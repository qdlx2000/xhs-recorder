#!/usr/bin/env python3
"""检查小红书主播是否在直播，返回房间ID。 / Check if an XHS streamer is live and return the room ID.

用法 / Usage: python3 check_live.py <host_id> [username]
输出 / Output: LIVE|<room_id> 或 / or NOT_LIVE

原理 / How it works:
1. 用Playwright搜索主播用户名 / Use Playwright to search for the streamer's username
2. 搜索API (onebox) 会返回 live_info 包含 room_id / Search API (onebox) returns live_info containing room_id
3. 如果主播在直播，直接拿到 room_id / If the streamer is live, we get the room_id directly
"""
import asyncio
import json
import re
import sys

from playwright.async_api import async_playwright


async def check_live(host_id: str, username: str = None, cookies: list = None) -> str:
    """检查主播是否在直播，返回 LIVE|room_id 或 NOT_LIVE / Check if streamer is live, returns LIVE|room_id or NOT_LIVE

    核心原理：搜索API (onebox) 在主播开播时会返回 live_info 字段，/ Core principle: Search API (onebox) returns live_info field when streamer is live,
    其中包含 room_id。这比解析主页更可靠。/ which contains room_id. This is more reliable than parsing the profile page.
    """
    if not username:
        print("[ERROR] 需要提供 username 参数 / username parameter is required", file=sys.stderr)
        return "NOT_LIVE"
    
    if not cookies:
        print("[ERROR] 需要提供 cookies 配置 / cookies configuration is required", file=sys.stderr)
        return "NOT_LIVE"

    room_id_found = None

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
        )
        await context.add_cookies(cookies)
        page = await context.new_page()

        # 拦截搜索API响应，寻找直播数据 / Intercept search API responses to find live stream data
        async def on_response(response):
            nonlocal room_id_found
            url = response.url
            try:
                if "onebox" in url or "search" in url:
                    body = await response.text()
                    # 搜索 onebox API 会返回 live_info 包含 room_id / Search onebox API returns live_info containing room_id
                    if "live_info" in body and host_id in body:
                        try:
                            data = json.loads(body)
                            onebox_list = data.get("data", {}).get("onebox_list", [])
                            for item in onebox_list:
                                user_data = item.get("user_one_box", {})
                                live_info = user_data.get("live_info", {})
                                if live_info.get("room_id"):
                                    room_id_found = str(live_info["room_id"])
                                    print(f"[INFO] 搜索API找到直播间: {room_id_found} / Search API found live room: {room_id_found}", file=sys.stderr)
                        except json.JSONDecodeError:
                            pass
                    # 也检查搜索结果中的 room_id / Also check for room_id in search results
                    if "room_id" in body and host_id in body:
                        room_match = re.search(r'"room_id"\s*:\s*"(\d{15,25})"', body)
                        if room_match and not room_id_found:
                            room_id_found = room_match.group(1)
            except Exception:
                pass

        page.on("response", on_response)

        # 核心方法: 用搜索API查找主播 / Core method: search for streamer via the search API
        search_url = f"https://www.xiaohongshu.com/search_result?keyword={username}&source=web_search_result_notes"
        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
        except Exception as e:
            print(f"[WARN] 搜索页加载 / Search page load: {e}", file=sys.stderr)

        # 等待搜索API响应 / Wait for search API response
        await asyncio.sleep(5)

        if room_id_found:
            return f"LIVE|{room_id_found}"

        # 备用方法: 检查主页DOM / Fallback method: check profile page DOM
        try:
            await page.goto(
                f"https://www.xiaohongshu.com/user/profile/{host_id}",
                wait_until="domcontentloaded",
                timeout=15000
            )
            await asyncio.sleep(3)

            # 检查是否有 "直播中" 文本 / Check for "Live" indicator text
            has_live_text = await page.evaluate('''() => {
                const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                while (walker.nextNode()) {
                    if (walker.currentNode.textContent.includes('直播中')) return true;
                }
                return false;
            }''')

            if has_live_text and not room_id_found:
                # 有直播标识但搜索API没返回 room_id，可能正在切换 / Live indicator found but search API didn't return room_id, may be transitioning
                return "LIVE|unknown"

        except Exception:
            pass

        await browser.close()

    return "NOT_LIVE"


async def main():
    if len(sys.argv) < 2:
        print("用法 / Usage: python3 check_live.py <host_id> [username]", file=sys.stderr)
        print("需要从 config.json 读取 cookies / Reads cookies from config.json", file=sys.stderr)
        sys.exit(1)

    host_id = sys.argv[1]
    username = sys.argv[2] if len(sys.argv) > 2 else None
    
    # 尝试从 config.json 读取配置 / Try to load configuration from config.json
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        cookies = config.get("cookies", [])
        if not username:
            username = config.get("username")
    except FileNotFoundError:
        print("[ERROR] 未找到 config.json，请先复制 config.example.json / config.json not found, please copy config.example.json first", file=sys.stderr)
        sys.exit(1)
    
    if not cookies:
        print("[ERROR] config.json 中缺少 cookies 配置 / Missing cookies configuration in config.json", file=sys.stderr)
        sys.exit(1)
    
    result = await check_live(host_id, username, cookies)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
