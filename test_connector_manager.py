"""
测试调整后的 Connector Manager
"""
from capabilities.connectors.connector_manager import UniversalConnectorManager


def test_connector_manager():
    """
    测试 Connector Manager 的基本功能
    """
    print("=== 测试 Connector Manager ===")
    
    # 创建 Connector Manager 实例
    connector_manager = UniversalConnectorManager()
    
    # 1. 测试 HTTP 连接器
    print("\n1. 测试 HTTP 连接器...")
    
    http_params = {
        "url": "https://jsonplaceholder.typicode.com/posts/1",
        "method": "GET"
    }
    
    try:
        http_result = connector_manager.execute("http", "execute", {}, http_params)
        print(f"HTTP 连接器测试结果: {http_result}")
        print("✅ HTTP 连接器测试通过")
    except Exception as e:
        print(f"❌ HTTP 连接器测试失败: {str(e)}")
    
    # 2. 测试健康检查功能
    print("\n2. 测试健康检查功能...")
    
    # 测试 HTTP 健康检查
    http_health = connector_manager.health_check("http", http_params)
    print(f"HTTP 健康检查结果: {'✅ 健康' if http_health else '❌ 不健康'}")
    
    # 测试 Dify 健康检查（预期会失败，因为没有提供有效的 API key）
    dify_params = {
        "api_key": "invalid_key",
        "base_url": "https://api.dify.ai/v1"
    }
    
    dify_health = connector_manager.health_check("dify", dify_params)
    print(f"Dify 健康检查结果: {'✅ 健康' if dify_health else '❌ 不健康'}")
    
    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    test_connector_manager()