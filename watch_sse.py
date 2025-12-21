#!/usr/bin/env python3
"""
SSE 客户端：连接到 SSE 服务并打印实时事件
"""
import sys
import http.client
from sseclient import SSEClient

# SSE 配置
SSE_URL = "http://localhost:8000/events" # ← 改成你实际的 SSE 地址

def main():
    print(f"🔌 连接到 SSE 流: {SSE_URL}")
    print("按 Ctrl+C 退出\n")
    
    try:
        # 解析 URL 获取主机和端口
        host = SSE_URL.replace("http://", "").split(":")[0]
        port = int(SSE_URL.replace("http://", "").split(":")[1].split("/")[0]) if ":" in SSE_URL else 80
        path = "/" + "/".join(SSE_URL.replace("http://", "").split(":")[1].split("/")[1:]) if ":" in SSE_URL else SSE_URL.replace("http://", "")
        
        # 创建 HTTP 连接
        conn = http.client.HTTPConnection(host, port)
        
        # 发送 GET 请求，获取 SSE 流
        conn.request("GET", path)
        
        # 获取响应
        response = conn.getresponse()
        
        # 检查响应状态码
        if response.status != 200:
            print(f"❌ 连接失败，状态码: {response.status}")
            print(f"   响应头: {response.getheaders()}")
            print(f"   响应体: {response.read().decode('utf-8')}")
            return
        
        # 使用 SSEClient 处理响应流
        client = SSEClient(response)
        
        # 处理 SSE 事件
        for event in client.events():
            if event.data.strip():
                print(f"📡 {event.event or 'data'}: {event.data}")
                
    except KeyboardInterrupt:
        print("\n👋 已断开 SSE 连接")
    except Exception as e:
        print(f"❌ 连接失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()