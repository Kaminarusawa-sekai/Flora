"""Actor引用管理工具类，提供序列化/反序列化和Redis配置功能"""
import logging
import pickle
import json
from typing import Optional, Any
from thespian.actors import ActorAddress

# 导入配置管理器
from common.config.config_manager import config_manager

# 尝试导入Redis
REDIS_AVAILABLE = False
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    logging.warning("Redis未安装，某些功能将不可用")


class ActorReferenceUtils:
    """Actor引用管理工具类"""
    
    def __init__(self):
        self.logger = logging.getLogger("ActorReferenceUtils")
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
    
    def serialize_address(self, addr: ActorAddress) -> str:
        """
        序列化ActorAddress为字符串
        
        Args:
            addr: Thespian ActorAddress对象
            
        Returns:
            str: 序列化后的字符串
        """
        try:
            # 尝试使用pickle序列化
            serialized = pickle.dumps(addr)
            # 使用base64编码确保安全存储
            import base64
            return base64.b64encode(serialized).decode('ascii')
        except Exception as e:
            self.logger.error(f"使用pickle序列化ActorAddress失败: {e}")
            
            # 备选方案1: 使用str()
            try:
                addr_str = str(addr)
                # 将字符串转换为JSON对象以便于存储
                return json.dumps({"type": "str", "value": addr_str})
            except Exception as e2:
                self.logger.error(f"使用str()序列化ActorAddress失败: {e2}")
                
                # 备选方案2: 使用__str__属性
                try:
                    if hasattr(addr, '__str__'):
                        str_repr = addr.__str__()
                        return json.dumps({"type": "__str__", "value": str_repr})
                except Exception as e3:
                    self.logger.error(f"使用__str__序列化ActorAddress失败: {e3}")
            
            # 最后的备选方案: 返回None
            self.logger.critical("无法序列化ActorAddress")
            return None
    
    def deserialize_address(self, addr_str: str) -> Optional[ActorAddress]:
        """
        从字符串反序列化为ActorAddress
        
        Args:
            addr_str: 序列化后的字符串
            
        Returns:
            ActorAddress: 反序列化后的ActorAddress对象，如果失败返回None
        """
        if not addr_str:
            return None
        
        try:
            # 尝试使用pickle反序列化
            import base64
            decoded = base64.b64decode(addr_str.encode('ascii'))
            return pickle.loads(decoded)
        except Exception as e:
            self.logger.error(f"使用pickle反序列化ActorAddress失败: {e}")
            
            # 尝试解析JSON格式
            try:
                data = json.loads(addr_str)
                if isinstance(data, dict) and "type" in data and "value" in data:
                    # 根据类型处理
                    if data["type"] == "str" or data["type"] == "__str__":
                        # 对于某些Thespian transport，可以使用ActorAddress.from_hash()
                        # 但这取决于具体的transport实现
                        try:
                            # 尝试直接使用字符串值
                            # 在某些情况下，Thespian可以接受字符串形式的地址
                            return data["value"]
                        except Exception as e2:
                            self.logger.error(f"处理字符串类型地址失败: {e2}")
            except Exception as e2:
                self.logger.error(f"解析JSON格式地址失败: {e2}")
        
        # 所有尝试都失败
        self.logger.critical(f"无法反序列化ActorAddress: {addr_str}")
        return None
    
    def get_redis_client(self) -> Optional[Any]:
        """
        获取Redis客户端实例
        
        Returns:
            redis.Redis: Redis客户端实例，如果不可用返回None
        """
        return self.redis_client
    
    def is_redis_available(self) -> bool:
        """
        检查Redis是否可用
        
        Returns:
            bool: Redis是否可用
        """
        return self.redis_client is not None
    
    def create_redis_key(self, prefix: str, tenant_id: str, node_id: str) -> str:
        """
        创建Redis键
        
        Args:
            prefix: 键前缀
            tenant_id: 租户ID
            node_id: 节点ID
            
        Returns:
            str: 完整的Redis键
        """
        return f"{prefix}:{tenant_id}:{node_id}"
    
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
actor_reference_utils = ActorReferenceUtils()
