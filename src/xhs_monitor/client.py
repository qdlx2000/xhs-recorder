"""XHS API客户端 / XHS (Xiaohongshu) API client"""
import json
import time
from typing import Optional

import requests


class XHSClient:
    """小红书API客户端 / Xiaohongshu API client"""
    
    BASE_URL = "https://edith.xiaohongshu.com"
    
    def __init__(self, cookies: list):
        # 初始化HTTP会话并注入cookies / Initialize HTTP session and inject cookies
        self.session = requests.Session()
        for cookie in cookies:
            self.session.cookies.set(cookie["name"], cookie["value"])
        # 设置请求头以模拟浏览器 / Set request headers to mimic a browser
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://www.xiaohongshu.com/",
        })
    
    def get_user_info(self, user_id: str) -> Optional[dict]:
        """获取用户信息 / Get user information"""
        url = f"{self.BASE_URL}/api/sns/web/v1/user/otherinfo?target_user_id={user_id}"
        try:
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"获取用户信息失败: {e}")
        return None
    
    def check_live_status(self, user_id: str) -> Optional[str]:
        """检查直播状态，返回room_id或None / Check live status, return room_id or None"""
        user_info = self.get_user_info(user_id)
        if user_info:
            data = user_info.get("data", {})
            # 判断是否正在直播 / Determine whether the user is currently live
            if data.get("live_status") == "live":
                return data.get("room_id")
        return None
