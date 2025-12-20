#!/usr/bin/env python3
"""
系统启动脚本
用于同时启动系统的四个主要服务：
1. events/main.py
2. interaction/main.py
3. tasks/main.py
4. trigger/main.py
"""
import os
import sys
import time
import subprocess
import signal
from typing import List, Dict

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

def start_service(service: Dict) -> None:
    """启动单个服务"""
    print(f"\n=== 启动 {service['name']} ===")
    print(f"脚本路径: {service['script']}")
    print(f"工作目录: {service['cwd']}")
    
    # 构建启动命令
    command = [sys.executable, service['script']]
    
    # 启动服务
    process = subprocess.Popen(
        command,
        cwd=service['cwd'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # 存储进程对象
    service['process'] = process
    
    print(f"服务已启动，PID: {process.pid}")

def stop_service(service: Dict) -> None:
    """停止单个服务"""
    if service['process'] is None:
        print(f"{service['name']} 未运行")
        return
    
    print(f"\n=== 停止 {service['name']} ===")
    print(f"PID: {service['process'].pid}")
    
    try:
        # 发送 SIGTERM 信号
        service['process'].terminate()
        
        # 等待 5 秒
        try:
            service['process'].wait(timeout=5)
            print(f"服务已成功停止")
        except subprocess.TimeoutExpired:
            # 如果超时，发送 SIGKILL 信号
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
            # 检查每个服务的状态
            for service in SERVICES:
                if service['process'] is not None:
                    # 检查进程是否仍在运行
                    if service['process'].poll() is not None:
                        print(f"\n⚠️  {service['name']} 已退出，退出码: {service['process'].returncode}")
                        # 可以选择重启服务
                        # start_service(service)
    except KeyboardInterrupt:
        print("\n\n=== 收到终止信号 ===")

def main() -> None:
    """主函数"""
    print("=== 系统启动脚本 ===")
    print("用于同时启动系统的四个主要服务")
    print(f"当前目录: {os.getcwd()}")
    
    try:
        # 启动所有服务
        for service in SERVICES:
            start_service(service)
        
        # 监控服务
        monitor_services()
    finally:
        # 停止所有服务
        print("\n=== 停止所有服务 ===")
        for service in SERVICES:
            stop_service(service)
        
        print("\n=== 所有服务已停止 ===")

if __name__ == "__main__":
    main()