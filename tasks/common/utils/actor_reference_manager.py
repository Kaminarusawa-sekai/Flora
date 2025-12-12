"""Actor引用管理工具类，提供序列化/反序列化和引用管理功能"""
import logging
import pickle
import json
import base64
from typing import Optional
from datetime import datetime, timedelta
from thespian.actors import ActorAddress

from tasks.common.types.actor_reference import ActorReferenceDTO
from tasks.external.repositories.actor_reference_repo import ActorReferenceRepo
from tasks.external.database.redis_client import RedisClient


class ActorReferenceManager:
    """Actor引用管理工具类"""

    def __init__(self):
        self.logger = logging.getLogger("ActorReferenceManager")

        # 初始化Repository
        try:
            redis_client = RedisClient()
            self.repo = ActorReferenceRepo(redis_client)
            self.logger.info("✓ ActorReferenceManager 初始化成功")
        except Exception as e:
            self.logger.error(f"✗ ActorReferenceManager 初始化失败: {e}")
            # 使用内存模式的repo
            self.repo = ActorReferenceRepo(redis_client=None)

    def serialize_address(self, addr: ActorAddress) -> Optional[str]:
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

    def create_redis_key(self, prefix: str, tenant_id: str, node_id: str) -> str:
        """
        创建Redis键（为了兼容性保留）

        Args:
            prefix: 键前缀
            tenant_id: 租户ID
            node_id: 节点ID

        Returns:
            str: 完整的Redis键
        """
        return f"{prefix}:{tenant_id}:{node_id}"

    # ============= Repository操作方法 =============

    def is_redis_available(self) -> bool:
        """
        检查Redis是否可用

        Returns:
            bool: Redis是否可用
        """
        return self.repo.is_redis_available()

    def save_actor_reference(self, tenant_id: str, node_id: str,
                           actor_address: ActorAddress, ttl: int = 3600) -> bool:
        """
        保存Actor引用

        Args:
            tenant_id: 租户ID
            node_id: 节点ID
            actor_address: Actor地址
            ttl: 过期时间（秒），默认3600秒（1小时）

        Returns:
            bool: 是否保存成功
        """
        # 序列化地址
        serialized_addr = self.serialize_address(actor_address)
        if not serialized_addr:
            return False

        # 创建DTO
        now = datetime.now()
        dto = ActorReferenceDTO(
            tenant_id=tenant_id,
            node_id=node_id,
            actor_address=serialized_addr,
            created_at=now,
            expires_at=now + timedelta(seconds=ttl),
            last_heartbeat=now
        )

        # 保存
        return self.repo.save(dto, ttl=ttl)

    def get_actor_reference(self, tenant_id: str, node_id: str) -> Optional[ActorAddress]:
        """
        获取Actor引用

        Args:
            tenant_id: 租户ID
            node_id: 节点ID

        Returns:
            ActorAddress: Actor地址，如果不存在返回None
        """
        # 从repo获取DTO
        dto = self.repo.get(tenant_id, node_id)
        if not dto:
            return None

        # 反序列化地址
        return self.deserialize_address(dto.actor_address)

    def delete_actor_reference(self, tenant_id: str, node_id: str) -> bool:
        """
        删除Actor引用

        Args:
            tenant_id: 租户ID
            node_id: 节点ID

        Returns:
            bool: 是否删除成功
        """
        return self.repo.delete(tenant_id, node_id)

    def refresh_actor_ttl(self, tenant_id: str, node_id: str, ttl: int = 3600) -> bool:
        """
        刷新Actor引用的TTL

        Args:
            tenant_id: 租户ID
            node_id: 节点ID
            ttl: 过期时间（秒），默认3600秒（1小时）

        Returns:
            bool: 是否刷新成功
        """
        return self.repo.refresh_ttl(tenant_id, node_id, ttl)

    def update_heartbeat(self, tenant_id: str, node_id: str) -> bool:
        """
        更新Actor引用的心跳时间

        Args:
            tenant_id: 租户ID
            node_id: 节点ID

        Returns:
            bool: 是否更新成功
        """
        # 刷新TTL并更新心跳
        success = self.repo.refresh_ttl(tenant_id, node_id)
        if success:
            self.repo.update_heartbeat(tenant_id, node_id)
        return success

    def exists(self, tenant_id: str, node_id: str) -> bool:
        """
        检查Actor引用是否存在

        Args:
            tenant_id: 租户ID
            node_id: 节点ID

        Returns:
            bool: 是否存在
        """
        return self.repo.exists(tenant_id, node_id)

    # ============= 兼容性方法（为了保持与旧代码的兼容） =============

    def get_redis_client(self) -> Optional[RedisClient]:
        """
        获取Redis客户端实例（兼容性方法）

        Returns:
            RedisClient: Redis客户端实例，如果不可用返回None
        """
        return self.repo.redis_client if self.repo.is_redis_available() else None

    def set_with_ttl(self, key: str, value: str, ttl: int = 3600) -> bool:
        """
        设置带TTL的Redis键值对（兼容性方法）

        Args:
            key: Redis键
            value: Redis值
            ttl: 过期时间（秒），默认3600秒（1小时）

        Returns:
            bool: 是否设置成功
        """
        if self.repo.is_redis_available():
            return self.repo.redis_client.set(key, value, ttl=ttl)
        return False

    def get(self, key: str) -> Optional[str]:
        """
        获取Redis键的值（兼容性方法）

        Args:
            key: Redis键

        Returns:
            str: Redis值，如果不存在或失败返回None
        """
        if self.repo.is_redis_available():
            return self.repo.redis_client.get(key)
        return None

    def delete(self, key: str) -> bool:
        """
        删除Redis键（兼容性方法）

        Args:
            key: Redis键

        Returns:
            bool: 是否删除成功
        """
        if self.repo.is_redis_available():
            return self.repo.redis_client.delete(key)
        return False

    def expire(self, key: str, ttl: int = 3600) -> bool:
        """
        设置Redis键的过期时间（兼容性方法）

        Args:
            key: Redis键
            ttl: 过期时间（秒），默认3600秒（1小时）

        Returns:
            bool: 是否设置成功
        """
        if self.repo.is_redis_available():
            return self.repo.redis_client.expire(key, ttl)
        return False


# 创建全局实例
actor_reference_manager = ActorReferenceManager()
