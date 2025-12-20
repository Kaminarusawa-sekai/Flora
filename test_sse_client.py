#!/usr/bin/env python3
"""
SSE 客户端测试脚本
功能：
1. 启动系统的四个主要服务
2. 测试 send_message API 的 SSE 流式响应功能
"""
import sys
import json
import time
import subprocess
import requests
from typing import List, Dict

# API 配置
BASE_URL = "http://localhost:8000"
SESSION_ID = "test_session_123"
USER_ID = "test_user_456"

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
        # 发送终止信号
        service['process'].terminate()
        
        # 等待 5 秒
        try:
            service['process'].wait(timeout=5)
            print(f"服务已成功停止")
        except subprocess.TimeoutExpired:
            # 如果超时，强制终止
            print(f"服务停止超时，强制终止")
            service['process'].kill()
            service['process'].wait()
    except Exception as e:
        print(f"停止服务时发生错误: {str(e)}")
    finally:
        service['process'] = None

def start_all_services() -> None:
    """启动所有服务"""
    print("=== 启动系统服务 ===")
    for service in SERVICES:
        start_service(service)
    print("\n=== 所有服务已启动 ===")

def stop_all_services() -> None:
    """停止所有服务"""
    print("=== 停止系统服务 ===")
    for service in SERVICES:
        stop_service(service)
    print("\n=== 所有服务已停止 ===")

def send_message(message: str):
    """发送消息到 SSE API 并处理流式响应"""
    # 构建请求 URL
    url = f"{BASE_URL}/conversations/{SESSION_ID}/messages"
    
    # 构建请求数据
    data = {
        "utterance": message,
        "timestamp": int(time.time() * 1000),
        "metadata": {}
    }
    
    # 构建请求头
    headers = {
        "X-User-ID": USER_ID,
        "Content-Type": "application/json"
    }
    
    print(f"\n=== 发送消息: {message} ===")
    print("\n服务器响应:")
    
    # 发送请求并获取 SSE 客户端
    response = requests.post(url, json=data, headers=headers, stream=True)
    client = SSEClient(response)
    
    # 存储最终回复
    final_reply = ""
    
    # 处理 SSE 事件
    for event in client.events():
        if event.event == "thought":
            # 处理思考过程
            data = json.loads(event.data)
            print(f"💭 {data['message']}")
            if "intent" in data:
                print(f"   意图: {data['intent']}")
        elif event.event == "message":
            # 处理消息内容
            data = json.loads(event.data)
            content = data["content"]
            final_reply += content
            print(content, end="", flush=True)
        elif event.event == "meta":
            # 处理元数据
            data = json.loads(event.data)
            print(f"\n\n📋 元数据: {json.dumps(data, ensure_ascii=False)}")
        elif event.event == "error":
            # 处理错误
            data = json.loads(event.data)
            print(f"\n❌ 错误: {data['message']}")
        else:
            # 处理其他事件类型
            print(f"\n📌 其他事件 {event.event}: {event.data}")
    
    print(f"\n=== 对话结束 ===")
    return final_reply

def main():
    """主函数"""
    print("=== SSE 客户端测试 ===")
    print(f"服务器地址: {BASE_URL}")
    print(f"会话 ID: {SESSION_ID}")
    print(f"用户 ID: {USER_ID}")
    print("\n输入 'exit' 或 'quit' 退出程序")
    print("输入 'start' 启动所有系统服务")
    print("输入 'stop' 停止所有系统服务\n")
    
    try:
        while True:
            # 获取用户输入
            message = input("你: ")
            
            # 检查退出条件
            if message.lower() in ["exit", "quit"]:
                print("\n=== 退出程序 ===")
                break
            
            # 启动所有服务
            elif message.lower() == "start":
                start_all_services()
            
            # 停止所有服务
            elif message.lower() == "stop":
                stop_all_services()
            
            # 发送消息
            else:
                try:
                    # 尝试导入 SSEClient
                    from sseclient import SSEClient
                    
                    # 发送消息并处理响应
                    send_message(message)
                except ImportError:
                    print("\n❌ 未安装 sseclient 库，请先安装: pip install sseclient-py")
                except Exception as e:
                    print(f"\n❌ 发送消息失败: {str(e)}")
                    import traceback
                    traceback.print_exc()
    except KeyboardInterrupt:
        print("\n\n=== 程序中断 ===")
    except Exception as e:
        print(f"\n\n❌ 程序错误: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # 退出前停止所有服务
        print("\n=== 清理资源 ===")
        stop_all_services()

if __name__ == "__main__":
    main()