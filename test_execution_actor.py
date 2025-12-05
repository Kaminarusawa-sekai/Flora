#!/usr/bin/env python3
"""
测试修改后的ExecutionActor功能
"""

import sys
import os
from thespian.actors import ActorSystem

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_execution_actor_init():
    """测试ExecutionActor初始化"""
    print("=== 测试ExecutionActor初始化 ===")
    
    # 创建Actor系统
    asys = ActorSystem('simpleSystemBase')
    
    try:
        # 导入ExecutionActor
        from capability_actors.execution_actor import ExecutionActor
        
        # 创建ExecutionActor实例
        exec_actor = asys.createActor(ExecutionActor)
        print("✓ ExecutionActor创建成功")
        
        # 测试执行dify命令，预期返回NEED_INPUT
        test_msg = {
            "type": "execute",
            "task_id": "test-123",
            "capability": "dify",
            "parameters": {
                "base_url": "https://api.dify.ai/v1"  # 缺少api_key和workflow_id
            }
        }
        
        # 发送消息并等待响应
        response = asys.ask(exec_actor, test_msg, timeout=5)
        print(f"✓ 收到响应: {response}")
        
    finally:
        # 关闭Actor系统
        asys.shutdown()

def test_connector_manager_integration():
    """测试connector_manager集成"""
    print("\n=== 测试connector_manager集成 ===")
    
    # 直接测试connector_manager的返回值处理
    from capabilities.excution.universal_excution import UniversalConnectorManager
    
    # 创建connector_manager实例
    manager = UniversalConnectorManager()
    
    # 测试dify缺失参数
    result = manager.execute(
        connector_name="dify",
        operation_name="execute",
        inputs={"test": "input"},
        params={"base_url": "https://api.dify.ai/v1"}
    )
    
    print(f"✓ ConnectorManager返回: {result}")
    assert result["result"]["status"] == "NEED_INPUT", f"预期NEED_INPUT，实际得到{result['result']['status']}"
    assert "api_key" in result["result"]["missing"], "预期缺少api_key"
    assert "workflow_id" in result["result"]["missing"], "预期缺少workflow_id"
    
    print("✓ ConnectorManager集成测试通过")

if __name__ == "__main__":
    print("开始测试ExecutionActor...\n")
    
    try:
        test_connector_manager_integration()
        # test_execution_actor_init()  # 注释掉，因为需要完整的Actor系统环境
        print("\n🎉 测试通过！")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
