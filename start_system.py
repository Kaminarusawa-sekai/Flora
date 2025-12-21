#!/usr/bin/env python3
"""
系统启动脚本（带实时日志）
用于同时启动系统的四个主要服务，并实时显示各服务的日志输出：
1. events/main.py
2. interaction/main.py
3. tasks/main.py
4. trigger/main.py
"""
import os
import sys
import time
import subprocess
import threading
from typing import Dict

# 系统服务配置
SERVICES = [
    {
        "name": "Events Service",
        "script": "events/main.py",
        "cwd": "e:\\Data\\Flora",
        "process": None
    },
    {
        "name": "Interaction Service",
        "script": "interaction/main.py",
        "cwd": "e:\\Data\\Flora",
        "process": None
    },
    {
        "name": "Tasks Service",
        "script": "tasks/main.py",
        "cwd": "e:\\Data\\Flora",
        "process": None
    },
    {
        "name": "Trigger Service",
        "script": "trigger/main.py",
        "cwd": "e:\\Data\\Flora",
        "process": None
    }
]

def _log_reader(name: str, pipe):
    """从子进程管道读取日志并打印，带服务前缀"""
    try:
        for line in iter(pipe.readline, ''):
            if line:
                print(f"[{name}] {line.rstrip()}")
    except Exception as e:
        print(f"[{name}] 日志读取异常: {e}", file=sys.stderr)
    finally:
        pipe.close()

def start_service(service: Dict) -> None:
    """启动单个服务，并开启日志监听线程"""
    print(f"\n=== 启动 {service['name']} ===")
    print(f"脚本路径: {service['script']}")
    print(f"工作目录: {service['cwd']}")
    
    command = [sys.executable, service['script']]
    
    # 启动子进程，捕获 stdout/stderr
    process = subprocess.Popen(
        command,
        cwd=service['cwd'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,               # 行缓冲
        universal_newlines=True  # 文本模式
    )
    
    service['process'] = process
    
    # 启动日志读取线程（daemon 线程，主程序退出时自动结束）
    log_thread = threading.Thread(
        target=_log_reader,
        args=(service['name'], process.stdout),
        daemon=True
    )
    log_thread.start()
    
    print(f"服务已启动，PID: {process.pid}")

def stop_service(service: Dict) -> None:
    """停止单个服务"""
    if service['process'] is None:
        print(f"{service['name']} 未运行")
        return
    
    print(f"\n=== 停止 {service['name']} ===")
    print(f"PID: {service['process'].pid}")
    
    try:
        service['process'].terminate()
        try:
            service['process'].wait(timeout=5)
            print(f"服务已成功停止")
        except subprocess.TimeoutExpired:
            print(f"服务停止超时，强制终止")
            service['process'].kill()
            service['process'].wait()
    except Exception as e:
        print(f"停止服务时发生错误: {str(e)}")
    finally:
        service['process'] = None

def monitor_services() -> None:
    """监控服务状态"""
    print("\n=== 监控服务状态 ===")
    print("按 Ctrl+C 停止所有服务")
    
    try:
        while True:
            time.sleep(1)
            for service in SERVICES:
                if service['process'] is not None and service['process'].poll() is not None:
                    print(f"\n⚠️  {service['name']} 已意外退出，退出码: {service['process'].returncode}")
                    # 可选：自动重启（取消注释下一行）
                    # start_service(service)
    except KeyboardInterrupt:
        print("\n\n=== 收到终止信号 ===")

def main() -> None:
    """主函数"""
    print("=== 系统启动脚本（带日志）===")
    print("用于同时启动系统的四个主要服务，并实时显示日志")
    print(f"当前目录: {os.getcwd()}")
    
    try:
        for service in SERVICES:
            start_service(service)
        
        monitor_services()
    finally:
        print("\n=== 正在停止所有服务 ===")
        for service in SERVICES:
            stop_service(service)
        print("\n=== 所有服务已停止 ===")

if __name__ == "__main__":
    main()