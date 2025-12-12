"""Actor引用Repository - 负责Actor引用的持久化管理"""
import logging
import json
from typing import Optional, List
from datetime import datetime, timedelta

from tasks.common.types.actor_reference import ActorReferenceDTO
from tasks.external.database.redis_client import RedisClient


class ActorReferenceRepo:
    """
    Actor引用Repository

    负责Actor引用信息的存储、查询和管理
    使用Redis作为存储后端
    """

    def __init__(self, redis_client: Optional[RedisClient] = None):
        """
        初始化Repository

        Args:
            redis_client: Redis客户端实例，如果为None则创建新实例
        """
        self.logger = logging.getLogger("ActorReferenceRepo")
        self.redis_client = redis_client or RedisClient()
        self._use_redis = True

        # 测试连接
        try:
            self.redis_client.client.ping()
            self.logger.info("✓ ActorReferenceRepo Redis连接成功")
        except Exception as e:
            self.logger.warning(f"✗ ActorReferenceRepo Redis连接失败: {e}，将使用内存模式")
            self._use_redis = False
            self._memory_store = {}  # 内存备份

    def is_redis_available(self) -> bool:
        """检查Redis是否可用"""
        return self._use_redis

    def create_key(self, tenant_id: str, node_id: str) -> str:
        """
        创建Redis键

        Args:
            tenant_id: 租户ID
            node_id: 节点ID

        Returns:
            str: 完整的Redis键
        """
        return f"actor_ref:{tenant_id}:{node_id}"

    def save(self, dto: ActorReferenceDTO, ttl: int = 3600) -> bool:
        """
        保存Actor引用

        Args:
            dto: Actor引用DTO
            ttl: 过期时间（秒），默认3600秒（1小时）

        Returns:
            bool: 是否保存成功
        """
        key = self.create_key(dto.tenant_id, dto.node_id)

        try:
            # 序列化为JSON
            value = json.dumps(dto.to_dict())

            if self._use_redis:
                # 使用Redis保存
                success = self.redis_client.set(key, value, ttl=ttl)
                if success:
                    self.logger.debug(f"保存Actor引用到Redis: {key}")
                    return True
                else:
                    self.logger.error(f"保存Actor引用到Redis失败: {key}")
                    # 降级到内存
                    self._memory_store[key] = {
                        "value": value,
                        "expires_at": datetime.now() + timedelta(seconds=ttl)
                    }
                    return True
            else:
                # 使用内存保存
                self._memory_store[key] = {
                    "value": value,
                    "expires_at": datetime.now() + timedelta(seconds=ttl)
                }
                self.logger.debug(f"保存Actor引用到内存: {key}")
                return True

        except Exception as e:
            self.logger.error(f"保存Actor引用失败: {e}")
            return False

    def get(self, tenant_id: str, node_id: str) -> Optional[ActorReferenceDTO]:
        """
        获取Actor引用

        Args:
            tenant_id: 租户ID
            node_id: 节点ID

        Returns:
            ActorReferenceDTO: Actor引用DTO，如果不存在返回None
        """
        key = self.create_key(tenant_id, node_id)

        try:
            value = None

            if self._use_redis:
                # 从Redis获取
                value = self.redis_client.get(key)

            # 如果Redis获取失败或不可用，从内存获取
            if not value and key in self._memory_store:
                entry = self._memory_store[key]
                # 检查是否过期
                if datetime.now() < entry["expires_at"]:
                    value = entry["value"]
                else:
                    # 已过期，删除
                    del self._memory_store[key]

            if value:
                # 反序列化
                data = json.loads(value)
                return ActorReferenceDTO.from_dict(data)

            return None

        except Exception as e:
            self.logger.error(f"获取Actor引用失败: {e}")
            return None

    def delete(self, tenant_id: str, node_id: str) -> bool:
        """
        删除Actor引用

        Args:
            tenant_id: 租户ID
            node_id: 节点ID

        Returns:
            bool: 是否删除成功
        """
        key = self.create_key(tenant_id, node_id)

        try:
            success = False

            if self._use_redis:
                # 从Redis删除
                success = self.redis_client.delete(key)

            # 同时从内存删除
            if key in self._memory_store:
                del self._memory_store[key]
                success = True

            if success:
                self.logger.debug(f"删除Actor引用: {key}")

            return success

        except Exception as e:
            self.logger.error(f"删除Actor引用失败: {e}")
            return False

    def refresh_ttl(self, tenant_id: str, node_id: str, ttl: int = 3600) -> bool:
        """
        刷新Actor引用的TTL

        Args:
            tenant_id: 租户ID
            node_id: 节点ID
            ttl: 过期时间（秒），默认3600秒（1小时）

        Returns:
            bool: 是否刷新成功
        """
        key = self.create_key(tenant_id, node_id)

        try:
            success = False

            if self._use_redis:
                # 刷新Redis TTL
                success = self.redis_client.expire(key, ttl)

            # 同时刷新内存TTL
            if key in self._memory_store:
                self._memory_store[key]["expires_at"] = datetime.now() + timedelta(seconds=ttl)
                success = True

            if success:
                self.logger.debug(f"刷新Actor引用TTL: {key}")

            return success

        except Exception as e:
            self.logger.error(f"刷新Actor引用TTL失败: {e}")
            return False

    def update_heartbeat(self, tenant_id: str, node_id: str) -> bool:
        """
        更新Actor引用的心跳时间

        Args:
            tenant_id: 租户ID
            node_id: 节点ID

        Returns:
            bool: 是否更新成功
        """
        # 获取现有引用
        dto = self.get(tenant_id, node_id)
        if not dto:
            return False

        # 更新心跳时间
        dto.last_heartbeat = datetime.now()

        # 保存
        return self.save(dto)

    def exists(self, tenant_id: str, node_id: str) -> bool:
        """
        检查Actor引用是否存在

        Args:
            tenant_id: 租户ID
            node_id: 节点ID

        Returns:
            bool: 是否存在
        """
        return self.get(tenant_id, node_id) is not None
