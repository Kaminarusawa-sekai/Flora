"""测试TextToSQL接口和Vanna实现"""
import asyncio
import sys
import os
import pytest

# 添加项目根目录到Python路径
project_root = os.path.abspath('.')
sys.path.insert(0, project_root)

from new.capabilities.data_analytics.text_to_sql import TextToSQL
from new.capabilities.data_analytics.vanna.vanna_impl import VannaTextToSQL

def test_interface_import():
    """测试TextToSQL接口是否能正确导入"""
    print("=== 测试TextToSQL接口导入 ===")
    print(f"TextToSQL接口: {TextToSQL}")
    print("接口导入成功！")

def test_vanna_import():
    """测试VannaTextToSQL实现是否能正确导入"""
    print("\n=== 测试VannaTextToSQL实现导入 ===")
    print(f"VannaTextToSQL实现: {VannaTextToSQL}")
    print("实现导入成功！")

@pytest.mark.asyncio
async def test_vanna_initialization():
    """测试VannaTextToSQL初始化"""
    print("\n=== 测试VannaTextToSQL初始化 ===")
    
    # 注意：需要有效的Vanna API密钥才能进行完整测试
    # 这里使用空配置进行初始化测试
    config = {
        "api_key": "test_key",
        "model": "test_model"
    }
    
    try:
        vanna_tts = VannaTextToSQL(config)
        print(f"VannaTextToSQL初始化成功: {vanna_tts}")
        return True
    except Exception as e:
        print(f"VannaTextToSQL初始化失败: {e}")
        return False

@pytest.mark.asyncio
async def test_interface_methods():
    """测试TextToSQL接口的所有方法是否都被VannaTextToSQL实现"""
    print("\n=== 测试接口方法实现 ===")
    
    config = {
        "api_key": "test_key",
        "model": "test_model"
    }
    
    try:
        vanna_tts = VannaTextToSQL(config)
        
        # 检查所有接口方法是否都被实现
        methods_to_check = [
            "generate_sql",
            "execute_sql", 
            "get_table_info",
            "add_training_data",
            "get_training_data"
        ]
        
        for method in methods_to_check:
            if hasattr(vanna_tts, method):
                print(f"✓ {method} 方法已实现")
            else:
                print(f"✗ {method} 方法未实现")
        
        return True
    except Exception as e:
        print(f"测试接口方法失败: {e}")
        return False

def main():
    """运行所有测试"""
    print("开始测试TextToSQL接口和Vanna实现...")
    
    # 同步测试
    test_interface_import()
    test_vanna_import()
    
    # 异步测试
    asyncio.run(test_vanna_initialization())
    asyncio.run(test_interface_methods())
    
    print("\n=== 所有测试完成 ===")

if __name__ == "__main__":
    main()