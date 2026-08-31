"""配置模块"""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    """监控配置"""
    host_id: str
    username: str
    cookies: list = field(default_factory=list)
    check_interval: int = 3600
    check_live_interval: int = 600
    whisper_model: str = "medium"
    output_dir: str = "./recordings"
    
    @classmethod
    def from_file(cls, path: str = "config.json") -> "Config":
        """从配置文件加载"""
        with open(path, "r") as f:
            data = json.load(f)
        
        return cls(
            host_id=data["host_id"],
            username=data.get("username", ""),
            cookies=data.get("cookies", []),
            check_interval=data.get("check_interval", 3600),
            check_live_interval=data.get("check_live_interval", 600),
            whisper_model=data.get("whisper_model", "medium"),
            output_dir=data.get("output_dir", "./recordings"),
        )
    
    def save(self, path: str = "config.json"):
        """保存配置到文件"""
        data = {
            "host_id": self.host_id,
            "username": self.username,
            "cookies": self.cookies,
            "check_interval": self.check_interval,
            "check_live_interval": self.check_live_interval,
            "whisper_model": self.whisper_model,
            "output_dir": self.output_dir,
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
