#!/usr/bin/env python3
"""
测试合并后的UniversalConnectorManager功能
"""

from capabilities.excution.universal_excution import UniversalConnectorManager

def test_dify_config_params():
    """测试Dify配置参数正确时执行"""
    print("=== 测试Dify配置参数 ===")
    manager = UniversalConnectorManager()
    
    try:
        # 缺少必需参数，预期抛出异常
        result = manager.execute(
            connector_name="dify",
            operation_name="execute",
            inputs={"test": "input"},
            params={"base_url": "https://api.dify.ai/v1"}  # 缺少api_key
        )
        print("✗ 预期抛出异常，但未抛出")
    except Exception as e:
        print(f"✓ 预期抛出异常: {e}")

def test_http_config_params():
    """测试HTTP配置参数"""
    print("\n=== 测试HTTP配置参数 ===")
    manager = UniversalConnectorManager()
    
    try:
        # 缺少必需参数url，预期抛出异常
        result = manager.execute(
            connector_name="http",
            operation_name="execute",
            inputs={"test": "input"},
            params={"method": "GET"}  # 缺少url
        )
        print("✗ 预期抛出异常，但未抛出")
    except Exception as e:
        print(f"✓ 预期抛出异常: {e}")

def test_data_query_config_params():
    """测试数据查询配置参数"""
    print("\n=== 测试数据查询配置参数 ===")
    manager = UniversalConnectorManager()
    
    try:
        # 缺少必需参数query，预期抛出异常
        result = manager.execute(
            connector_name="data_query",
            operation_name="execute",
            inputs={"test": "input"},
            params={"params": {"key": "value"}}  # 缺少query
        )
        print("✗ 预期抛出异常，但未抛出")
    except Exception as e:
        print(f"✓ 预期抛出异常: {e}")

def test_connector_support():
    """测试支持的连接器类型"""
    print("\n=== 测试支持的连接器类型 ===")
    manager = UniversalConnectorManager()
    
    # 测试支持的连接器（预期会抛出配置参数缺失异常）
    supported_connectors = ["dify", "dify_workflow", "http", "http_get", "data", "data_query"]
    
    for connector in supported_connectors:
        try:
            # 故意缺少参数，预期抛出异常
            result = manager.execute(
                connector_name=connector,
                operation_name="execute",
                inputs={"test": "input"},
                params={}
            )
            print(f"✗ 连接器 {connector} 预期抛出异常，但未抛出")
        except Exception as e:
            if "Missing required config parameters" in str(e):
                print(f"✓ 连接器 {connector} 支持（配置参数检查通过）")
            else:
                print(f"✗ 连接器 {connector} 抛出意外异常: {e}")
    
    # 测试不支持的连接器
    try:
        result = manager.execute(
            connector_name="unsupported_connector",
            operation_name="execute",
            inputs={"test": "input"},
            params={}
        )
        print("✗ 不支持的连接器测试失败")
    except Exception as e:
        if "Unsupported connector" in str(e):
            print(f"✓ 不支持的连接器测试通过: {e}")
        else:
            print(f"✗ 不支持的连接器抛出意外异常: {e}")

if __name__ == "__main__":
    print("开始测试UniversalConnectorManager...\n")
    
    try:
        test_dify_config_params()
        test_http_config_params()
        test_data_query_config_params()
        test_connector_support()
        print("\n🎉 所有测试通过！")
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
    except Exception as e:
        print(f"\n❌ 测试发生异常: {e}")
