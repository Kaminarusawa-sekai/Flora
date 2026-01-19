from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class MessageQueueListener(ABC):
    """
    消息队列监听器抽象基类
    定义了消息队列监听器的通用接口，支持不同消息队列系统的实现
    """
    
    def __init__(self, actor_system: Any, agent_actor_ref: Any, config: dict = None):
        """
        初始化消息队列监听器
        
        Args:
            actor_system: Actor系统实例
            agent_actor_ref: AgentActor的引用
            config: 配置参数字典
        """
        self.actor_system = actor_system
        self.agent_actor_ref = agent_actor_ref
        self.config = config or {}
        self.running = False
    
    @abstractmethod
    def start(self):
        """
        启动消息队列监听
        """
        pass
    
    @abstractmethod
    def start_in_thread(self):
        """
        在独立线程中启动消息队列监听
        """
        pass
    
    @abstractmethod
    def stop(self):
        """
        停止消息队列监听
        """
        pass


class MessageQueuePublisher(ABC):
    """
    消息队列发布者抽象基类
    定义了消息队列发布的通用接口，支持不同消息队列系统的实现
    """
    
    def __init__(self, config: dict = None):
        """
        初始化消息队列发布者
        
        Args:
            config: 配置参数字典
        """
        self.config = config or {}
    
    @abstractmethod
    def connect(self):
        """
        建立消息队列连接
        """
        pass
    
    @abstractmethod
    def publish(self, message: Dict[str, Any], **kwargs):
        """
        发布消息到消息队列
        
        Args:
            message: 要发布的消息数据
            **kwargs: 额外的发布参数，如队列名、交换机、路由键等
        """
        pass
    
    @abstractmethod
    def close(self):
        """
        关闭消息队列连接
        """
        pass