import requests
import json

# 测试数据
url = "http://localhost:8000/api/v1/task/with-comment"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMTIzIiwidGVuYW50X2lkIjoiZGVmYXVsdCIsInVzZXJuYW1lIjoidGVzdHVzZXIiLCJyb2xlcyI6WyJhZG1pbiIsInVzZXIiXSwiZXhwIjoxNzYzMDQ2MzMyLCJpYXQiOjE3NjMwNDQ1MzIsImp0aSI6ImFjODJiNzg3Y2VkMDY0MmQ5NDFiZmIxMWE5MTIxZmY1In0.ALfFPw5YPtDqj1hye1_Irvsf8H2T0y6TXphi0zih0Ow"
}
data = {
    "task": {
        "title": "Test Task",
        "description": "This is a test task"
    },
    "comment": {
        "content": "First comment",
        "user_id": "user123"
    }
}

# 发送请求
try:
    response = requests.post(url, headers=headers, data=json.dumps(data))
    print(f"Response Status Code: {response.status_code}")
    print(f"Response Content: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {str(e)}")
