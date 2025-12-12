import os

# 定义要处理的文件路径
file_path = 'e:\\Data\\Flora\\events\\command_tower\\dag_dispatcher_coordinator.py'

# 读取文件内容
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 替换所有中文逗号为英文逗号
new_content = content.replace('，', ',')

# 写入修改后的内容
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"Replaced all Chinese commas with English commas in {file_path}")
