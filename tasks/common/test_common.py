"""
公共配置与工具模块测试
"""

import os
import sys
import tempfile
import json
import yaml
from datetime import datetime

# 从当前目录导入模块
from .config import config_manager, plugin_config_manager, PluginConfig
from .messages import (
    BaseMessage, SimpleMessage, TaskCreatedMessage, 
    TaskCompletedMessage, OptimizationStartedMessage
)
from .utils import (to_json, from_json, to_yaml, from_yaml, 
                          serialize, deserialize, serializer)

def test_config_manager():
    """测试配置管理器"""
    print("=== 测试配置管理器 ===")
    
    # 创建临时配置文件
    config_data = {
        "database": {
            "host": "localhost",
            "port": 3306,
            "name": "flora_db"
        },
        "api": {
            "host": "0.0.0.0",
            "port": 8080
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        temp_config_file = f.name
    
    try:
        # 加载配置
        config_manager.load_config(temp_config_file)
        
        # 获取配置
        assert config_manager.get("database.host") == "localhost"
        assert config_manager.get("database.port") == 3306
        assert config_manager.get("api.port") == 8080
        assert config_manager.get("api.missing", "default") == "default"
        
        # 设置配置
        config_manager.set("api.debug", True)
        assert config_manager.get("api.debug") is True
        
        print("✅ 配置管理器测试通过")
    finally:
        os.unlink(temp_config_file)

def test_plugin_config():
    """测试插件配置"""
    print("=== 测试插件配置 ===")
    
    # 创建临时插件配置文件
    plugin_config_data = {
        "plugin_name": "test_plugin",
        "api_key": "test_key",
        "endpoint": "https://api.example.com"
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(plugin_config_data, f)
        temp_plugin_file = f.name
    
    try:
        # 创建插件配置
        plugin_config = PluginConfig("test_plugin", temp_plugin_file)
        
        # 获取配置
        assert plugin_config.get("plugin_name") == "test_plugin"
        assert plugin_config.get("api_key") == "test_key"
        
        # 设置配置
        plugin_config.set("timeout", 30)
        assert plugin_config.get("timeout") == 30
        
        # 注册到插件配置管理器
        plugin_config_manager.register_plugin_config(plugin_config)
        assert plugin_config_manager.get_plugin_config("test_plugin") is plugin_config
        
        print("✅ 插件配置测试通过")
    finally:
        os.unlink(temp_plugin_file)

def test_messages():
    """测试消息模块"""
    print("=== 测试消息模块 ===")
    
    # 测试BaseMessage
    base_msg = BaseMessage.__subclasses__()[0]("source", "destination", "content")
    assert base_msg.source == "source"
    assert base_msg.destination == "destination"
    assert hasattr(base_msg, "timestamp")
    
    # 测试SimpleMessage
    simple_msg = SimpleMessage("user", "agent", "Hello, Flora!")
    simple_msg_dict = simple_msg.to_dict()
    assert simple_msg_dict["content"] == "Hello, Flora!"
    
    # 测试TaskCreatedMessage
    task_msg = TaskCreatedMessage(
        source="coordinator",
        destination="executor",
        task_id="task_123",
        task_type="analysis",
        parameters={"data": "test_data"}, 
        priority=1
    )
    task_msg_dict = task_msg.to_dict()
    assert task_msg_dict["task_id"] == "task_123"
    assert task_msg_dict["task_type"] == "analysis"
    
    # 测试OptimizationStartedMessage
    opt_msg = OptimizationStartedMessage(
        source="optimizer",
        destination="worker",
        task_id="task_456",
        optimization_id="opt_789",
        optimization_type="gradient_descent",
        initial_params={"lr": 0.01}
    )
    opt_msg_dict = opt_msg.to_dict()
    assert opt_msg_dict["optimization_type"] == "gradient_descent"
    
    print("✅ 消息模块测试通过")

def test_serializer():
    """测试序列化工具"""
    print("=== 测试序列化工具 ===")
    
    test_obj = {
        "string": "test",
        "number": 123,
        "float": 3.14,
        "bool": True,
        "list": [1, 2, 3],
        "dict": {"key": "value"},
        "datetime": datetime.now()
    }
    
    # 测试JSON序列化
    json_str = to_json(test_obj, indent=2)
    assert json_str is not None
    loaded_obj = from_json(json_str)
    assert loaded_obj["string"] == test_obj["string"]
    assert loaded_obj["number"] == test_obj["number"]
    
    # 测试YAML序列化
    yaml_str = to_yaml(test_obj)
    assert yaml_str is not None
    loaded_obj_yaml = from_yaml(yaml_str)
    assert loaded_obj_yaml["string"] == test_obj["string"]
    
    # 测试统一序列化接口
    json_str2 = serialize(test_obj, "json")
    assert json_str2 is not None
    loaded_obj2 = deserialize(json_str2, "json")
    assert loaded_obj2["string"] == test_obj["string"]
    
    # 测试消息对象序列化
    msg = SimpleMessage("source", "destination", "content")
    msg_json = to_json(msg)
    loaded_msg = from_json(msg_json)
    assert loaded_msg["source"] == msg.source
    assert loaded_msg["destination"] == msg.destination
    assert loaded_msg["content"] == msg.content
    
    print("✅ 序列化工具测试通过")

def test_message_serialization():
    """测试消息对象的序列化与反序列化"""
    print("=== 测试消息序列化 ===")
    
    # 创建测试消息
    task_msg = TaskCreatedMessage(
        source="coordinator",
        destination="executor",
        task_id="task_123",
        task_type="data_analysis",
        parameters={"dataset": "sales_data.csv", "model": "linear_regression"}, 
        priority=1
    )
    
    # 转换为JSON
    json_str = task_msg.to_json()
    assert json_str is not None
    
    # 转换回对象
    msg_dict = from_json(json_str)
    assert msg_dict["source"] == "coordinator"
    assert msg_dict["task_id"] == "task_123"
    assert msg_dict["task_type"] == "data_analysis"
    
    # 测试任务完成消息
    completed_msg = TaskCompletedMessage(
        source="executor",
        destination="coordinator",
        task_id="task_123",
        result={"accuracy": 0.95, "precision": 0.92}
    )
    
    completed_json = completed_msg.to_json()
    assert completed_json is not None
    
    print("✅ 消息序列化测试通过")

if __name__ == "__main__":
    """运行所有测试"""
    try:
        test_config_manager()
        test_plugin_config()
        test_messages()
        test_serializer()
        test_message_serialization()
        print("\n🎉 所有测试通过")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
