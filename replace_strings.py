import os

# 目标目录
target_dir = "e:\Data\Flora\events\external"

# 要替换的字符串映射
replacements = {
    "TaskDefinition": "EventDefinition",
    "TaskInstance": "EventInstance",
    "TaskInstanceStatus": "EventInstanceStatus",
    "TaskDefinitionRepository": "EventDefinitionRepository",
    "TaskInstanceRepository": "EventInstanceRepository",
    "TaskDefinitionDB": "EventDefinitionDB",
    "TaskInstanceDB": "EventInstanceDB"
}

# 遍历目录下的所有 .py 文件
for root, dirs, files in os.walk(target_dir):
    for file in files:
        if file.endswith(".py"):
            file_path = os.path.join(root, file)
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查是否需要替换
            original_content = content
            for old_str, new_str in replacements.items():
                content = content.replace(old_str, new_str)
            
            # 如果内容有变化，写入文件
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Updated: {file_path}")

print("All replacements completed successfully!")