import requests

# 测试创建对话接口
def test_create_conversation():
    url = "http://localhost:8000/conversations"
    headers = {
        "X-User-ID": "test_user_1"
    }
    
    try:
        response = requests.post(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    test_create_conversation()