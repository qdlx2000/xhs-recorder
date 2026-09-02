"""主监控模块 / Main monitoring module"""
import asyncio
import subprocess
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import Config
from .detector import SearchDetector


class Monitor:
    """直播监控器 / Livestream monitor"""
    
    def __init__(self, config: Config):
        self.config = config
        self.detector = SearchDetector(config.cookies)
        self.current_room: Optional[str] = None
        self.running = False
        self.is_recording = False
        # 日志文件路径 / Log file path
        self.log_file = Path(config.output_dir) / "monitor.log"
    
    def log(self, msg: str):
        # 记录带时间戳的日志到控制台和文件 / Log with timestamp to console and file
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {msg}"
        print(line)
        with open(self.log_file, "a") as f:
            f.write(line + "\n")
    
    def start_recording(self, room_id: str):
        self.log(f"启动录制: 房间 {room_id}")
        self.is_recording = True
        
        # 启动录制脚本 / Start the recording script
        subprocess.Popen(
            ["bash", "scripts/record.sh", room_id],
            cwd=str(Path(__file__).parent.parent.parent),
            stdout=open(Path(self.config.output_dir) / "record.log", "a"),
            stderr=subprocess.STDOUT,
        )
        
        # 启动弹幕采集脚本 / Start the danmaku (bullet comment) capture script
        subprocess.Popen(
            ["python3", "scripts/danmaku.py", room_id],
            cwd=str(Path(__file__).parent.parent.parent),
            stdout=open(Path(self.config.output_dir) / "danmaku.log", "a"),
            stderr=subprocess.STDOUT,
        )
        
        self.log("录制已启动")
    
    def stop_recording(self):
        self.log("停止录制")
        self.is_recording = False
        # 终止录制和弹幕进程 / Terminate recording and danmaku processes
        subprocess.run(["pkill", "-f", "record.sh"], capture_output=True)
        subprocess.run(["pkill", "-f", "danmaku.py"], capture_output=True)
    
    async def check_once(self) -> Optional[str]:
        # 执行一次直播状态检测 / Perform a single live status check
        return await self.detector.detect(self.config.host_id, self.config.username)
    
    async def run(self):
        self.running = True
        self.log("=" * 50)
        self.log("XHS直播监控启动")
        self.log(f"主播ID: {self.config.host_id}")
        self.log(f"检查间隔: {self.config.check_interval}秒")
        self.log("=" * 50)
        
        while self.running:
            try:
                room_id = await self.check_once()
                
                # 检测到开播且房间变化 / Live detected and room changed
                if room_id and room_id != self.current_room:
                    self.log(f"发现开播! 房间: {room_id}")
                    self.current_room = room_id
                    self.start_recording(room_id)
                    
                # 直播结束 / Livestream ended
                elif not room_id and self.current_room:
                    self.log("直播结束")
                    self.current_room = None
                    self.stop_recording()
                    
                # 仍在直播中 / Still live
                elif room_id:
                    self.log(f"继续直播中，房间: {room_id}")
                # 未开播 / Not live
                else:
                    self.log("未开播")
                
            except Exception as e:
                self.log(f"检查出错: {e}")
            
            # 直播中缩短检查间隔，否则用默认间隔 / Shorter interval while live, otherwise default
            interval = self.config.check_live_interval if self.current_room else self.config.check_interval
            await asyncio.sleep(interval)
    
    def stop(self):
        self.running = False
        self.stop_recording()
        self.log("监控已停止")


def main():
    config = Config.from_file()
    monitor = Monitor(config)
    
    def signal_handler(sig, frame):
        # 收到信号时优雅退出 / Gracefully exit on signal
        monitor.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    asyncio.run(monitor.run())


if __name__ == "__main__":
    main()
