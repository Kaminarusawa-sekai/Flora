"""Redis连接适配器，负责管理与Redis的连接和基本操作"""
import logging
from typing import Optional, Any

# 导入配置管理器
from ...common.config.config_manager import config_manager

# 尝试导入Redis
REDIS_AVAILABLE = False
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    logging.warning("Redis未安装，某些功能将不可用")


class RedisAdapter:
    """Redis连接适配器类"""
    
    def __init__(self):
        self.logger = logging.getLogger("RedisAdapter")
        self.redis_client = None
        self._init_redis()
    
    def _init_redis(self):
        """初始化Redis连接"""
        if not REDIS_AVAILABLE:
            self.logger.warning("Redis未安装，无法初始化Redis连接")
            return
        
        try:
            # 从配置获取Redis连接信息
            redis_config = config_manager.get("redis", {})
            
            # 构建Redis连接参数
            redis_params = {
                "host": redis_config.get("host", "localhost"),
                "port": redis_config.get("port", 6379),
                "db": redis_config.get("db", 0),
            }
            
            # 添加可选的密码
            password = redis_config.get("password")
            if password:
                redis_params["password"] = password
            
            # 添加可选的超时设置
            timeout = redis_config.get("timeout", 30)
            redis_params["socket_connect_timeout"] = timeout
            
            # 创建Redis客户端
            self.redis_client = redis.Redis(**redis_params)
            
            # 测试连接
            self.redis_client.ping()
            self.logger.info(f"成功连接到Redis: {redis_params['host']}:{redis_params['port']}")
            
        except Exception as e:
            self.logger.error(f"Redis连接失败: {e}")
            self.redis_client = None
    
    def get_client(self) -> Optional[Any]:
        """
        获取Redis客户端实例
        
        Returns:
            redis.Redis: Redis客户端实例，如果不可用返回None
        """
        return self.redis_client
    
    def is_available(self) -> bool:
        """
        检查Redis是否可用
        
        Returns:
            bool: Redis是否可用
        """
        return self.redis_client is not None
    
    def set_with_ttl(self, key: str, value: str, ttl: int = 3600) -> bool:
        """
        设置带TTL的Redis键值对
        
        Args:
            key: Redis键
            value: Redis值
            ttl: 过期时间（秒），默认3600秒（1小时）
            
        Returns:
            bool: 是否设置成功
        """
        if not self.redis_client:
            self.logger.error("Redis客户端不可用")
            return False
        
        try:
            self.redis_client.setex(key, ttl, value)
            return True
        except Exception as e:
            self.logger.error(f"设置Redis键值对失败: {e}")
            return False
    
    def get(self, key: str) -> Optional[str]:
        """
        获取Redis键的值
        
        Args:
            key: Redis键
            
        Returns:
            str: Redis值，如果不存在或失败返回None
        """
        if not self.redis_client:
            self.logger.error("Redis客户端不可用")
            return None
        
        try:
            return self.redis_client.get(key)
        except Exception as e:
            self.logger.error(f"获取Redis键值失败: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """
        删除Redis键
        
        Args:
            key: Redis键
            
        Returns:
            bool: 是否删除成功
        """
        if not self.redis_client:
            self.logger.error("Redis客户端不可用")
            return False
        
        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            self.logger.error(f"删除Redis键失败: {e}")
            return False
    
    def expire(self, key: str, ttl: int = 3600) -> bool:
        """
        设置Redis键的过期时间
        
        Args:
            key: Redis键
            ttl: 过期时间（秒），默认3600秒（1小时）
            
        Returns:
            bool: 是否设置成功
        """
        if not self.redis_client:
            self.logger.error("Redis客户端不可用")
            return False
        
        try:
            self.redis_client.expire(key, ttl)
            return True
        except Exception as e:
            self.logger.error(f"设置Redis键过期时间失败: {e}")
            return False


# 创建全局实例
redis_adapter = RedisAdapter()