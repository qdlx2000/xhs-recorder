#!/usr/bin/env python3
"""小红书直播弹幕监控

用法: python3 danmaku.py <room_id>
输出: 实时打印弹幕，同时保存到日志文件
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
    print("请安装 playwright: pip install playwright && playwright install chromium")
    sys.exit(1)


OUTPUT_DIR = Path("./recordings")
SESSION_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
DANMAKU_LOG = OUTPUT_DIR / f"xhs_danmaku_{SESSION_ID}.log"


def log_danmaku(msg_type, nickname, content):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{msg_type}] {nickname}: {content}\n"
    with open(DANMAKU_LOG, "a", encoding="utf-8") as f:
        f.write(log_line)
    print(log_line.strip(), flush=True)


def parse_ws_message(raw):
    if not isinstance(raw, str):
        return
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return
    if data.get("t") != 4:
        return
    items = (((data.get("b") or {}).get("d") or {}).get("b") or [])
    for item in items:
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
        nickname = profile.get("nickname", "未知")
        if cd_type == "text":
            log_danmaku("弹幕", nickname, cd.get("desc", ""))
        elif cd_type in ("audience_join", "audience_join_v2"):
            log_danmaku("进入", nickname, "进入直播间")
        elif cd_type == "follow_emcee":
            log_danmaku("关注", nickname, "关注了主播")
        elif cd_type == "like":
            log_danmaku("点赞", nickname, "点赞了")
        elif cd_type == "gift":
            log_danmaku("礼物", nickname, f"赠送 {cd.get('giftName', '礼物')} x{cd.get('count', 1)}")


async def run_session(room_id, cookies, attempt):
    url = f"https://www.xiaohongshu.com/livestream/dynpathBZhuJjtn/{room_id}"
    print(f"[Attempt {attempt}] 房间 {room_id} — 连接中...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        await context.add_cookies(cookies)
        page = await context.new_page()

        def on_ws(ws):
            print(f"[WS] 已连接: {ws.url[:100]}")
            ws.on("framereceived", lambda payload: parse_ws_message(payload))

        page.on("websocket", on_ws)

        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print(f"[WARN] 页面加载: {e}")

        print("[INFO] 已连接，等待弹幕...")
        shutdown = False
        while not shutdown:
            await asyncio.sleep(5)

        await browser.close()


async def main():
    if len(sys.argv) < 2:
        print("用法: python3 danmaku.py <room_id>")
        sys.exit(1)

    room_id = sys.argv[1]
    
    # 加载配置
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        cookies = config.get("cookies", [])
    except FileNotFoundError:
        print("[ERROR] 未找到 config.json", file=sys.stderr)
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def handle_signal(sig, frame):
        print("\n[INFO] 收到停止信号")
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    print(f"=== 小红书弹幕监控 ===")
    print(f"房间ID: {room_id}")
    print(f"弹幕文件: {DANMAKU_LOG.name}")
    print()

    attempt = 0
    while True:
        attempt += 1
        try:
            await run_session(room_id, cookies, attempt)
        except Exception as e:
            print(f"[ERROR] 会话异常: {e}")
        print(f"[INFO] 10秒后重连...")
        await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(main())
