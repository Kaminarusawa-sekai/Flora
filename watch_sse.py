#!/usr/bin/env python3
"""
SSE 客户端：连接到 SSE 服务并进行交互式对话
"""
import sys
import http.client
import json
import time
import threading
from sseclient import SSEClient

# API 配置
API_HOST = "localhost"
API_PORT = 8000
SESSION_ID = "1"  # 会话ID，可根据需要修改
X_USER_ID = "test_user"  # 用户ID，根据API要求提供

# API 端点
SEND_MESSAGE_URL = f"/v1/conversations/{SESSION_ID}/messages"
SSE_STREAM_URL = f"/v1/conversations/{SESSION_ID}/stream"

def send_user_message(utterance):
    """发送用户消息到API"""
    try:
        # 创建 HTTP 连接
        conn = http.client.HTTPConnection(API_HOST, API_PORT)
        
        # 准备请求数据
        payload = {
            "utterance": utterance,
            "timestamp": int(time.time() * 1000),  # 毫秒时间戳
            "metadata": {}
        }
        
        # 设置请求头
        headers = {
            "Content-Type": "application/json",
            "X-User-ID": X_USER_ID
        }
        
        # 发送 POST 请求
        conn.request("POST", SEND_MESSAGE_URL, body=json.dumps(payload, ensure_ascii=False), headers=headers)
        
        # 获取响应
        response = conn.getresponse()
        response_data = response.read().decode("utf-8")
        
        if response.status == 202:
            print(f"✅ 消息已发送: {utterance}")
        else:
            print(f"❌ 发送消息失败，状态码: {response.status}")
            print(f"   响应: {response_data}")
        
        conn.close()
    except Exception as e:
        print(f"❌ 发送消息时发生错误: {e}", file=sys.stderr)

def listen_to_sse():
    """监听SSE流并打印事件"""
    try:
        # 创建完整的SSE URL
        sse_url = f"http://{API_HOST}:{API_PORT}{SSE_STREAM_URL}"
        print(f"🔌 连接到 SSE 流: {sse_url}")
        
        # 创建 HTTP 连接
        conn = http.client.HTTPConnection(API_HOST, API_PORT)
        
        # 设置请求头
        headers = {
            "X-User-ID": X_USER_ID
        }
        
        # 发送 GET 请求，获取 SSE 流
        conn.request("GET", SSE_STREAM_URL, headers=headers)
        
        # 获取响应
        response = conn.getresponse()
        
        # 检查响应状态码
        if response.status != 200:
            print(f"❌ SSE 连接失败，状态码: {response.status}")
            print(f"   响应头: {response.getheaders()}")
            print(f"   响应体: {response.read().decode('utf-8')}")
            return
        
        # 使用 SSEClient 处理响应流
        client = SSEClient(response)
        
        # 处理 SSE 事件
        for event in client.events():
            if event.data.strip():
                try:
                    # 尝试解析 JSON 数据
                    data = json.loads(event.data)
                    print(f"🤖 {event.event or 'data'}: {json.dumps(data, ensure_ascii=False, indent=2)}")
                except json.JSONDecodeError:
                    # 如果不是 JSON，直接打印
                    print(f"🤖 {event.event or 'data'}: {event.data}")
        
        conn.close()
    except Exception as e:
        print(f"❌ SSE 监听时发生错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()

def main():
    print("💬 SSE 对话客户端")
    print("按 Ctrl+C 退出，输入 'quit' 或 'exit' 结束对话\n")
    
    # 启动 SSE 监听线程
    sse_thread = threading.Thread(target=listen_to_sse, daemon=True)
    sse_thread.start()
    
    # 等待 SSE 连接建立
    time.sleep(1)
    
    try:
        while True:
            # 获取用户输入
            user_input = input("👤 你: ").strip()
            
            if not user_input:
                continue
            
            # 检查是否退出
            if user_input.lower() in ["quit", "exit"]:
                print("👋 对话结束")
                break
            
            # 发送用户消息
            send_user_message(user_input)
    
    except KeyboardInterrupt:
        print("\n👋 已断开连接")
    except Exception as e:
        print(f"❌ 程序发生错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()