import os
import sys

def check_syntax(file_path):
    """检查单个文件的语法"""
    try:
        with open(file_path, 'rb') as f:
            code = compile(f.read(), file_path, 'exec')
        return True, None
    except SyntaxError as e:
        return False, f"{file_path}:{e.lineno}:{e.offset}: SyntaxError: {e.text.strip()}"
    except Exception as e:
        return False, f"{file_path}: Error: {str(e)}"

def main():
    """递归检查目录下所有 Python 文件的语法"""
    capabilities_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'interaction', 'capabilities')
    error_count = 0
    
    print(f"Checking syntax in {capabilities_dir}...")
    
    for root, dirs, files in os.walk(capabilities_dir):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                is_valid, error_msg = check_syntax(file_path)
                if not is_valid:
                    print(f"❌ {error_msg}")
                    error_count += 1
                else:
                    print(f"✅ {file_path}")
    
    print(f"\nSyntax check completed. Found {error_count} errors.")
    sys.exit(error_count)

if __name__ == "__main__":
    main()
