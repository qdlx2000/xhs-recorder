"""检测器模块"""
import json
import re
from typing import Optional

from playwright.async_api import async_playwright


class SearchDetector:
    """基于搜索API的检测器"""
    
    def __init__(self, cookies: list):
        self.cookies = cookies
    
    async def detect(self, host_id: str, username: str) -> Optional[str]:
        """检测直播状态，返回room_id或None"""
        room_id_found = None
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            await context.add_cookies(self.cookies)
            page = await context.new_page()
            
            async def on_response(response):
                nonlocal room_id_found
                url = response.url
                try:
                    if "onebox" in url or "search" in url:
                        body = await response.text()
                        if "live_info" in body and host_id in body:
                            try:
                                data = json.loads(body)
                                onebox_list = data.get("data", {}).get("onebox_list", [])
                                for item in onebox_list:
                                    user_data = item.get("user_one_box", {})
                                    live_info = user_data.get("live_info", {})
                                    if live_info.get("room_id"):
                                        room_id_found = str(live_info["room_id"])
                            except json.JSONDecodeError:
                                pass
                except Exception:
                    pass
            
            page.on("response", on_response)
            
            search_url = f"https://www.xiaohongshu.com/search_result?keyword={username}&source=web_search_result_notes"
            try:
                await page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
            except Exception:
                pass
            
            await asyncio.sleep(5)
            await browser.close()
        
        return room_id_found
