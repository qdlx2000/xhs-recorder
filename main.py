#!/usr/bin/env python3
"""XHS Monitor - 主入口"""
import sys
import argparse

from src.xhs_monitor import Config, Monitor


def main():
    parser = argparse.ArgumentParser(description="小红书直播监控")
    parser.add_argument("--config", default="config.json", help="配置文件路径")
    parser.add_argument("--check", action="store_true", help="仅检查一次直播状态")
    args = parser.parse_args()
    
    try:
        config = Config.from_file(args.config)
    except FileNotFoundError:
        print(f"[ERROR] 未找到配置文件: {args.config}")
        print("请先复制 config.example.json 并填入你的配置")
        sys.exit(1)
    
    monitor = Monitor(config)
    
    if args.check:
        import asyncio
        room_id = asyncio.run(monitor.check_once())
        if room_id:
            print(f"LIVE|{room_id}")
        else:
            print("NOT_LIVE")
    else:
        import signal
        def signal_handler(sig, frame):
            monitor.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        asyncio.run(monitor.run())


if __name__ == "__main__":
    main()
