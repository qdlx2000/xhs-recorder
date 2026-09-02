#!/usr/bin/env python3
"""小红书直播弹幕监控 / XHS livestream danmaku (bullet comment) monitor

用法 / Usage: python3 danmaku.py <room_id>
输出 / Output: 实时打印弹幕，同时保存到日志文件 / Prints danmaku in real-time and saves to log file
"""
import asyncio
import base64
import json
import signal
import sys
from datetime import datetime
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("请安装 playwright / Please install playwright: pip install playwright && playwright install chromium")
    sys.exit(1)


# 输出目录 / Output directory
OUTPUT_DIR = Path("./recordings")
# 当前会话ID（基于启动时间） / Session ID based on startup time
SESSION_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
# 弹幕日志文件路径 / Danmaku log file path
DANMAKU_LOG = OUTPUT_DIR / f"xhs_danmaku_{SESSION_ID}.log"


def log_danmaku(msg_type, nickname, content):
    """将弹幕记录到日志文件并打印到终端 / Log danmaku to file and print to terminal"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{msg_type}] {nickname}: {content}\n"
    with open(DANMAKU_LOG, "a", encoding="utf-8") as f:
        f.write(log_line)
    print(log_line.strip(), flush=True)


def parse_ws_message(raw):
    """解析WebSocket消息，提取弹幕/礼物/关注等事件 / Parse WebSocket message to extract danmaku/gift/follow events"""
    if not isinstance(raw, str):
        return
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return
    # t == 4 表示业务消息 / t == 4 indicates a business message
    if data.get("t") != 4:
        return
    # 消息嵌套结构: data.b.d.b[] 包含各条事件 / Nested message structure: data.b.d.b[] contains individual events
    items = (((data.get("b") or {}).get("d") or {}).get("b") or [])
    for item in items:
        # d 字段是base64编码的自定义数据 / Field d is base64-encoded custom data
        encoded = item.get("d", "")
        if not encoded:
            continue
        try:
            decoded = base64.b64decode(encoded).decode("utf-8", errors="replace")
            wrapper = json.loads(decoded)
        except Exception:
            continue
        custom_data = wrapper.get("customData", "")
        if not custom_data:
            continue
        try:
            cd = json.loads(custom_data)
        except (json.JSONDecodeError, TypeError):
            continue
        cd_type = cd.get("type", "")
        profile = cd.get("profile", {})
        nickname = profile.get("nickname", "未知")  # 未知 / unknown
        if cd_type == "text":
            log_danmaku("弹幕", nickname, cd.get("desc", ""))
        elif cd_type in ("audience_join", "audience_join_v2"):
            log_danmaku("进入", nickname, "进入直播间")  # entered the live room
        elif cd_type == "follow_emcee":
            log_danmaku("关注", nickname, "关注了主播")  # followed the streamer
        elif cd_type == "like":
            log_danmaku("点赞", nickname, "点赞了")  # liked
        elif cd_type == "gift":
            log_danmaku("礼物", nickname, f"赠送 {cd.get('giftName', '礼物')} x{cd.get('count', 1)}")
            # gifted {gift_name} x{count}


async def run_session(room_id, cookies, attempt):
    """运行单次监控会话，断线后由调用方重试 / Run a single monitoring session; caller retries on disconnect"""
    url = f"https://www.xiaohongshu.com/livestream/dynpathBZhuJjtn/{room_id}"
    print(f"[Attempt {attempt}] 房间 {room_id} — 连接中... / Connecting to room {room_id}...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        await context.add_cookies(cookies)
        page = await context.new_page()

        def on_ws(ws):
            print(f"[WS] 已连接 / Connected: {ws.url[:100]}")
            ws.on("framereceived", lambda payload: parse_ws_message(payload))

        page.on("websocket", on_ws)

        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print(f"[WARN] 页面加载 / Page load: {e}")

        print("[INFO] 已连接，等待弹幕... / Connected, waiting for danmaku...")
        shutdown = False
        while not shutdown:
            await asyncio.sleep(5)

        await browser.close()


async def main():
    if len(sys.argv) < 2:
        print("用法 / Usage: python3 danmaku.py <room_id>")
        sys.exit(1)

    room_id = sys.argv[1]
    
    # 加载配置 / Load configuration
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        cookies = config.get("cookies", [])
    except FileNotFoundError:
        print("[ERROR] 未找到 config.json / config.json not found", file=sys.stderr)
        sys.exit(1)

    # 确保输出目录存在 / Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def handle_signal(sig, frame):
        print("\n[INFO] 收到停止信号 / Received stop signal")
        sys.exit(0)

    # 注册信号处理（优雅退出） / Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    print(f"=== 小红书弹幕监控 / XHS Danmaku Monitor ===")
    print(f"房间ID / Room ID: {room_id}")
    print(f"弹幕文件 / Danmaku file: {DANMAKU_LOG.name}")
    print()

    # 主循环：自动重连 / Main loop: auto-reconnect on failure
    attempt = 0
    while True:
        attempt += 1
        try:
            await run_session(room_id, cookies, attempt)
        except Exception as e:
            print(f"[ERROR] 会话异常 / Session error: {e}")
        print(f"[INFO] 10秒后重连... / Reconnecting in 10 seconds...")
        await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(main())
