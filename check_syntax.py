import os
import sys
import ast


def check_syntax(directory):
    """检查指定目录下所有Python文件的语法"""
    errors = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        ast.parse(content)
                except SyntaxError as e:
                    errors.append(f"{file_path}: {e}")
                except Exception as e:
                    errors.append(f"{file_path}: {type(e).__name__}: {e}")
    
    return errors


if __name__ == "__main__":
    directory = sys.argv[1] if len(sys.argv) > 1 else "."
    errors = check_syntax(directory)
    
    if errors:
        print(f"发现 {len(errors)} 个语法错误:")
        for error in errors:
            print(error)
        sys.exit(1)
    else:
        print("没有发现语法错误")
        sys.exit(0)
