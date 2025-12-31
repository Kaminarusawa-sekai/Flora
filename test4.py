import requests

# 定义请求URL
url = 'http://localhost:8000/v1/user/1/sessions'

try:
    # 发送GET请求
    response = requests.get(url)
    
    # 打印响应状态码
    print(f"Status Code: {response.status_code}")
    
    # 打印响应头
    print("Response Headers:")
    for key, value in response.headers.items():
        print(f"{key}: {value}")
    
    # 打印响应内容
    print("\nResponse Body:")
    print(response.text)
    
    # 如果响应是JSON格式，也可以解析为JSON
    if response.headers.get('Content-Type') == 'application/json':
        print("\nResponse JSON:")
        print(response.json())
        
except requests.exceptions.RequestException as e:
    # 处理请求异常
    print(f"Request Error: {e}")
