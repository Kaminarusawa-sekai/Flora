"""Redis客户端封装"""
import redis
from typing import Any, Optional
from config import REDIS_HOST, REDIS_PORT, REDIS_DATABASE, REDIS_PASSWORD


class RedisClient:
    """
    Redis客户端封装，提供基础的Redis操作方法
    """
    
    def __init__(self, host: str=REDIS_HOST, port: int=REDIS_PORT, db: int=REDIS_DATABASE, password: Optional[str] = REDIS_PASSWORD):
        """
        初始化Redis客户端
        
        Args:
            config: Redis配置
                - host: Redis主机地址
                - port: Redis端口
                - db: 数据库索引
                - password: 密码（可选）
        """
        self.client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True
        )
    
    def get(self, key: str) -> Optional[str]:
        """
        获取键值
        
        Args:
            key: Redis键
            
        Returns:
            str: 键对应的值，如果不存在返回None
        """
        return self.client.get(key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        设置键值
        
        Args:
            key: Redis键
            value: 要设置的值
            ttl: 过期时间（秒），可选
            
        Returns:
            bool: 设置是否成功
        """
        if ttl:
            return self.client.setex(key, ttl, value)
        return self.client.set(key, value)
    
    def delete(self, key: str) -> bool:
        """
        删除键
        
        Args:
            key: Redis键
            
        Returns:
            bool: 删除是否成功
        """
        return self.client.delete(key) > 0
    
    def expire(self, key: str, ttl: int) -> bool:
        """
        设置键的过期时间
        
        Args:
            key: Redis键
            ttl: 过期时间（秒）
            
        Returns:
            bool: 设置是否成功
        """
        return self.client.expire(key, ttl)
    
    def exists(self, key: str) -> bool:
        """
        检查键是否存在
        
        Args:
            key: Redis键
            
        Returns:
            bool: 键是否存在
        """
        return self.client.exists(key) > 0
    
    def hget(self, key: str, field: str) -> Optional[str]:
        """
        获取哈希表字段值
        
        Args:
            key: Redis键
            field: 哈希表字段
            
        Returns:
            str: 字段对应的值，如果不存在返回None
        """
        return self.client.hget(key, field)
    
    def hset(self, key: str, field: str, value: Any) -> bool:
        """
        设置哈希表字段值
        
        Args:
            key: Redis键
            field: 哈希表字段
            value: 要设置的值
            
        Returns:
            bool: 设置是否成功
        """
        return self.client.hset(key, field, value) > 0
    
    def lpush(self, key: str, *values: Any) -> int:
        """
        向左推入列表元素
        
        Args:
            key: Redis键
            values: 要推入的值
            
        Returns:
            int: 列表长度
        """
        return self.client.lpush(key, *values)
    
    def rpop(self, key: str) -> Optional[str]:
        """
        向右弹出列表元素
        
        Args:
            key: Redis键
            
        Returns:
            str: 弹出的元素，如果列表为空返回None
        """
        return self.client.rpop(key)
