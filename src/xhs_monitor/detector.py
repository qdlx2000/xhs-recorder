"""检测器模块 / Detector module"""
import json
import re
from typing import Optional

from playwright.async_api import async_playwright


class SearchDetector:
    """基于搜索API的检测器 / Detector based on the search API"""
    
    def __init__(self, cookies: list):
        # 保存cookies供Playwright使用 / Store cookies for Playwright to use
        self.cookies = cookies
    
    async def detect(self, host_id: str, username: str) -> Optional[str]:
        """检测直播状态，返回room_id或None / Detect live status, return room_id or None"""
        room_id_found = None
        
        async with async_playwright() as p:
            # 启动无头浏览器 / Launch a headless browser
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            # 注入cookies以保持登录状态 / Inject cookies to maintain login state
            await context.add_cookies(self.cookies)
            page = await context.new_page()
            
            async def on_response(response):
                # 拦截搜索API响应 / Intercept search API responses
                nonlocal room_id_found
                url = response.url
                try:
                    # 仅处理onebox或search接口 / Only handle onebox or search endpoints
                    if "onebox" in url or "search" in url:
                        body = await response.text()
                        # 响应中包含直播信息且属于目标主播 / Response contains live info and belongs to the target host
                        if "live_info" in body and host_id in body:
                            try:
                                data = json.loads(body)
                                onebox_list = data.get("data", {}).get("onebox_list", [])
                                for item in onebox_list:
                                    user_data = item.get("user_one_box", {})
                                    live_info = user_data.get("live_info", {})
                                    # 提取房间ID / Extract the room ID
                                    if live_info.get("room_id"):
                                        room_id_found = str(live_info["room_id"])
                            except json.JSONDecodeError:
                                pass
                except Exception:
                    pass
            
            page.on("response", on_response)
            
            # 构造搜索URL / Build the search URL
            search_url = f"https://www.xiaohongshu.com/search_result?keyword={username}&source=web_search_result_notes"
            try:
                await page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
            except Exception:
                pass
            
            # 等待页面加载完成 / Wait for the page to finish loading
            await asyncio.sleep(5)
            await browser.close()
        
        return room_id_found
