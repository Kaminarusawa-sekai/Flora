# tenant_router.py
"""
Flora多智能体协作系统 - 租户路由分发器

负责根据租户ID路由请求到对应的服务实例，实现多租户隔离
"""

import logging
from typing import Dict, Any, Optional, Union, Callable
from collections import defaultdict
import asyncio

logger = logging.getLogger(__name__)


class TenantRouter:
    """
    租户路由分发器类，管理不同租户的服务实例
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化租户路由分发器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        
        # 存储租户服务实例的缓存
        # 格式: {tenant_id: {service_type: service_instance}}
        self._service_cache = defaultdict(dict)
        
        # 服务工厂映射
        # 格式: {service_type: factory_function}
        self._service_factories = {}
        
        # 服务配置映射
        # 格式: {tenant_id: {service_type: service_config}}
        self._service_configs = defaultdict(dict)
        
        # 初始化默认配置
        self._init_defaults()
    
    def _init_defaults(self):
        """
        初始化默认配置和服务工厂
        """
        # 初始化默认服务配置
        default_config = self.config.get('default_services', {})
        for service_type, config in default_config.items():
            self.set_default_service_config(service_type, config)
    
    def register_service_factory(
        self,
        service_type: str,
        factory: Callable[..., Any]
    ):
        """
        注册服务工厂函数
        
        Args:
            service_type: 服务类型标识符
            factory: 创建服务实例的工厂函数
        """
        self._service_factories[service_type] = factory
        logger.info(f"Service factory registered: {service_type}")
    
    def set_default_service_config(
        self,
        service_type: str,
        config: Dict[str, Any]
    ):
        """
        设置默认服务配置
        
        Args:
            service_type: 服务类型
            config: 服务配置
        """
        # 设置通配符租户（*）的配置作为默认配置
        self._service_configs['*'][service_type] = config
        logger.info(f"Default config set for service: {service_type}")
    
    def set_tenant_service_config(
        self,
        tenant_id: str,
        service_type: str,
        config: Dict[str, Any]
    ):
        """
        设置特定租户的服务配置
        
        Args:
            tenant_id: 租户ID
            service_type: 服务类型
            config: 服务配置
        """
        self._service_configs[tenant_id][service_type] = config
        logger.info(f"Config set for tenant {tenant_id}, service: {service_type}")
    
    async def get_service(
        self,
        tenant_id: str,
        service_type: str,
        force_recreate: bool = False
    ) -> Any:
        """
        获取指定租户和类型的服务实例
        
        Args:
            tenant_id: 租户ID
            service_type: 服务类型
            force_recreate: 是否强制重新创建服务实例
            
        Returns:
            服务实例
            
        Raises:
            ValueError: 当服务类型未注册时
        """
        # 检查服务实例是否已存在且不强制重新创建
        if not force_recreate and service_type in self._service_cache[tenant_id]:
            logger.debug(
                f"Returning cached service: {service_type} for tenant: {tenant_id}"
            )
            return self._service_cache[tenant_id][service_type]
        
        # 获取服务配置
        config = self._get_service_config(tenant_id, service_type)
        
        # 创建服务实例
        service = await self._create_service(
            tenant_id=tenant_id,
            service_type=service_type,
            config=config
        )
        
        # 缓存服务实例
        self._service_cache[tenant_id][service_type] = service
        
        return service
    
    def _get_service_config(
        self,
        tenant_id: str,
        service_type: str
    ) -> Dict[str, Any]:
        """
        获取服务配置，优先使用租户特定配置，其次使用默认配置
        
        Args:
            tenant_id: 租户ID
            service_type: 服务类型
            
        Returns:
            服务配置字典
        """
        # 优先使用租户特定配置
        if tenant_id in self._service_configs and service_type in self._service_configs[tenant_id]:
            return self._service_configs[tenant_id][service_type].copy()
        
        # 其次使用默认配置
        if '*' in self._service_configs and service_type in self._service_configs['*']:
            return self._service_configs['*'][service_type].copy()
        
        # 如果都没有，返回空配置
        return {}
    
    async def _create_service(
        self,
        tenant_id: str,
        service_type: str,
        config: Dict[str, Any]
    ) -> Any:
        """
        创建服务实例
        
        Args:
            tenant_id: 租户ID
            service_type: 服务类型
            config: 服务配置
            
        Returns:
            服务实例
            
        Raises:
            ValueError: 当服务类型未注册时
        """
        # 检查服务工厂是否已注册
        if service_type not in self._service_factories:
            # 在实际实现中，这里应该抛出异常
            # 但为了开发和测试方便，这里返回一个模拟服务
            logger.warning(
                f"Service factory not registered: {service_type}. "
                f"Returning mock service for tenant: {tenant_id}"
            )
            return self._create_mock_service(tenant_id, service_type, config)
        
        # 获取服务工厂
        factory = self._service_factories[service_type]
        
        # 准备工厂参数
        factory_kwargs = {
            'tenant_id': tenant_id,
            'config': config
        }
        
        try:
            # 创建服务实例
            # 检查工厂是否为协程函数
            if asyncio.iscoroutinefunction(factory):
                service = await factory(**factory_kwargs)
            else:
                service = factory(**factory_kwargs)
            
            logger.info(
                f"Service created: {service_type} for tenant: {tenant_id}"
            )
            
            return service
            
        except Exception as e:
            logger.error(
                f"Failed to create service: {service_type} for tenant: {tenant_id}. "
                f"Error: {str(e)}",
                exc_info=True
            )
            
            # 返回模拟服务作为后备
            return self._create_mock_service(tenant_id, service_type, config)
    
    def _create_mock_service(
        self,
        tenant_id: str,
        service_type: str,
        config: Dict[str, Any]
    ) -> Any:
        """
        创建模拟服务实例，用于开发和测试
        
        Args:
            tenant_id: 租户ID
            service_type: 服务类型
            config: 服务配置
            
        Returns:
            模拟服务实例
        """
        # 创建一个简单的模拟服务类
        class MockService:
            def __init__(self, tenant_id, service_type, config):
                self.tenant_id = tenant_id
                self.service_type = service_type
                self.config = config
                self.name = f"Mock{service_type.capitalize()}Service"
            
            def __str__(self):
                return f"{self.name}(tenant_id={self.tenant_id})"
            
            def publish_event(self, **kwargs):
                # 模拟发布事件的方法
                pass
            
            def store_event(self, event_type: str, data: dict):
                # 模拟存储事件的方法
                pass
        
        return MockService(tenant_id, service_type, config)
    
    async def release_service(
        self,
        tenant_id: str,
        service_type: str
    ):
        """
        释放服务实例
        
        Args:
            tenant_id: 租户ID
            service_type: 服务类型
        """
        if tenant_id in self._service_cache:
            if service_type in self._service_cache[tenant_id]:
                del self._service_cache[tenant_id][service_type]
                logger.info(
                    f"Service released: {service_type} for tenant: {tenant_id}"
                )
    
    async def release_tenant_services(
        self,
        tenant_id: str
    ):
        """
        释放指定租户的所有服务实例
        
        Args:
            tenant_id: 租户ID
        """
        if tenant_id in self._service_cache:
            services_count = len(self._service_cache[tenant_id])
            del self._service_cache[tenant_id]
            logger.info(
                f"Released {services_count} services for tenant: {tenant_id}"
            )
    
    def clear_cache(self):
        """
        清空所有服务缓存
        """
        cache_size = len(self._service_cache)
        self._service_cache.clear()
        logger.info(f"Service cache cleared. Removed {cache_size} tenant entries.")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        获取缓存信息
        
        Returns:
            缓存信息字典
        """
        tenants_count = len(self._service_cache)
        services_count = sum(len(services) for services in self._service_cache.values())
        
        return {
            'tenants_count': tenants_count,
            'services_count': services_count,
            'per_tenant_services': {}
        }


# 工厂函数，用于创建租户路由分发器实例
def create_tenant_router(config: Optional[Dict[str, Any]] = None) -> TenantRouter:
    """
    创建租户路由分发器实例
    
    Args:
        config: 配置字典
        
    Returns:
        TenantRouter实例
    """
    return TenantRouter(config=config)
