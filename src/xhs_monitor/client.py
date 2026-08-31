"""XHS API客户端"""
import json
import time
from typing import Optional

import requests


class XHSClient:
    """小红书API客户端"""
    
    BASE_URL = "https://edith.xiaohongshu.com"
    
    def __init__(self, cookies: list):
        self.session = requests.Session()
        for cookie in cookies:
            self.session.cookies.set(cookie["name"], cookie["value"])
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://www.xiaohongshu.com/",
        })
    
    def get_user_info(self, user_id: str) -> Optional[dict]:
        """获取用户信息"""
        url = f"{self.BASE_URL}/api/sns/web/v1/user/otherinfo?target_user_id={user_id}"
        try:
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"获取用户信息失败: {e}")
        return None
    
    def check_live_status(self, user_id: str) -> Optional[str]:
        """检查直播状态，返回room_id或None"""
        user_info = self.get_user_info(user_id)
        if user_info:
            data = user_info.get("data", {})
            if data.get("live_status") == "live":
                return data.get("room_id")
        return None
