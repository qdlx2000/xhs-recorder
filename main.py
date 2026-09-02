#!/usr/bin/env python3
"""XHS Monitor - 主入口 / Main entry point"""
import sys
import argparse

from src.xhs_monitor import Config, Monitor


def main():
    # Set up command-line argument parser / 设置命令行参数解析器
    parser = argparse.ArgumentParser(description="小红书直播监控 / Xiaohongshu live stream monitor")
    # --config: path to JSON config file (default: config.json)
    # --config: 配置文件路径（默认：config.json）
    parser.add_argument("--config", default="config.json", help="配置文件路径 / Config file path")
    # --check: single check mode (exit after one status check)
    # --check: 单次检查模式（检查一次后退出）
    parser.add_argument("--check", action="store_true", help="仅检查一次直播状态 / Check live status once and exit")
    args = parser.parse_args()
    
    # Load configuration from file, exit with error if not found
    # 从文件加载配置，找不到则报错退出
    try:
        config = Config.from_file(args.config)
    except FileNotFoundError:
        print(f"[ERROR] 未找到配置文件: {args.config} / Config file not found: {args.config}")
        print("请先复制 config.example.json 并填入你的配置 / Copy config.example.json and fill in your config")
        sys.exit(1)
    
    # Create monitor instance with loaded config / 使用加载的配置创建 Monitor 实例
    monitor = Monitor(config)
    
    if args.check:
        # Single check mode: check once and print result / 单次检查模式：检查一次并输出结果
        import asyncio
        room_id = asyncio.run(monitor.check_once())
        if room_id:
            print(f"LIVE|{room_id}")
        else:
            print("NOT_LIVE")
    else:
        # Continuous monitoring mode: run until interrupted by signal
        # 持续监听模式：运行直到收到信号中断
        import signal
        def signal_handler(sig, frame):
            # Graceful shutdown on SIGINT/SIGTERM
            # 收到 SIGINT/SIGTERM 时优雅停止
            monitor.stop()
            sys.exit(0)
        
        # Register signal handlers for clean shutdown
        # 注册信号处理函数以实现干净退出
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start the monitoring loop / 启动监听循环
        asyncio.run(monitor.run())


if __name__ == "__main__":
    main()
