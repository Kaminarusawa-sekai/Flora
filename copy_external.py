import os
import shutil

# 源目录和目标目录
source_dir = "e:\Data\Flora\events copy 3\external"
target_dir = "e:\Data\Flora\events\external"

# 确保目标目录存在
os.makedirs(target_dir, exist_ok=True)

# 复制所有文件和子目录
for root, dirs, files in os.walk(source_dir):
    # 计算相对路径
    relative_path = os.path.relpath(root, source_dir)
    # 构建目标子目录路径
    target_subdir = os.path.join(target_dir, relative_path)
    # 创建目标子目录
    os.makedirs(target_subdir, exist_ok=True)
    # 复制文件
    for file in files:
        source_file = os.path.join(root, file)
        target_file = os.path.join(target_subdir, file)
        # 如果目标文件存在，先删除
        if os.path.exists(target_file):
            os.remove(target_file)
        # 复制文件
        shutil.copy2(source_file, target_file)
        print(f"Copied: {source_file} -> {target_file}")

print("All files copied successfully!")