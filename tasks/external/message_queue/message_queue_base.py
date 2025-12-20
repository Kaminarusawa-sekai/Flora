from abc import ABC, abstractmethod
from typing import Any


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