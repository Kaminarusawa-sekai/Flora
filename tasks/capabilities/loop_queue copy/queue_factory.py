"""循环队列工厂类"""
from typing import Dict, Any, Optional
from .queue_interface import LoopQueueInterface


def create_queue(queue_type: str = "thespian", **kwargs) -> LoopQueueInterface:
    """
    创建循环队列实例
    
    Args:
        queue_type: 队列类型，默认为"thespian"
        **kwargs: 额外的配置参数
        
    Returns:
        LoopQueueInterface: 循环队列实例
        
    Raises:
        ValueError: 当队列类型不支持时
    """
    if queue_type == "thespian":
        from .thespian_queue import ThespianLoopQueue
        queue = ThespianLoopQueue()
        queue.initialize()
        return queue
    else:
        raise ValueError(f"Unsupported queue type: {queue_type}")


def get_queue_types() -> Dict[str, Dict[str, Any]]:
    """
    获取所有支持的队列类型及其描述
    
    Returns:
        Dict[str, Dict[str, Any]]: 队列类型到描述的映射
    """
    return {
        "thespian": {
            "description": "基于Thespian框架的循环队列实现",
            "features": [
                "支持Thespian Actor系统集成",
                "任务状态管理",
                "动态添加/移除任务",
                "任务暂停/恢复功能"
            ],
            "requires": ["thespian"]
        }
    }


def is_queue_type_supported(queue_type: str) -> bool:
    """
    检查是否支持指定的队列类型
    
    Args:
        queue_type: 队列类型
        
    Returns:
        bool: 是否支持
    """
    supported_types = get_queue_types()
    return queue_type in supported_types


def create_queue_with_config(config: Dict[str, Any]) -> Optional[LoopQueueInterface]:
    """
    使用配置字典创建队列实例
    
    Args:
        config: 配置字典，必须包含"type"键
        
    Returns:
        LoopQueueInterface: 循环队列实例，如果配置无效返回None
    """
    if "type" not in config:
        return None
    
    queue_type = config["type"]
    if not is_queue_type_supported(queue_type):
        return None
    
    # 移除type键，其他作为kwargs传递
    queue_config = config.copy()
    queue_config.pop("type")
    
    try:
        return create_queue(queue_type=queue_type, **queue_config)
    except Exception:
        return None
