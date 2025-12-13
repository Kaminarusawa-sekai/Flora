import os
import shutil

# 获取当前目录
current_dir = os.path.dirname(os.path.abspath(__file__))
capabilities_dir = os.path.join(current_dir, 'interaction', 'capabilities')

# 遍历所有子目录
for root, dirs, files in os.walk(capabilities_dir):
    # 只处理直接子目录
    if os.path.dirname(root) == capabilities_dir:
        dir_name = os.path.basename(root)
        for file in files:
            if file == 'common_implementation.py':
                # 构建新文件名：common_+目录名.py
                new_file_name = f'common_{dir_name}.py'
                old_path = os.path.join(root, file)
                new_path = os.path.join(root, new_file_name)
                print(f'Renaming: {old_path} -> {new_path}')
                os.rename(old_path, new_path)

print('All files renamed successfully!')
