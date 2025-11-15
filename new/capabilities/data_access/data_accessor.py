"""数据访问器实现"""
from typing import Dict, Any, List, Optional, Tuple, Union
from ..capability_base import CapabilityBase
from .data_source import DataSource, DataSourceType
import logging


class DataAccessor(CapabilityBase):
    """
    数据访问器
    提供高级数据访问接口，支持多种数据源和查询优化
    从agent.io.data_actor和agent.io.data_query_actor迁移而来
    """
    
    def __init__(self):
        """
        初始化数据访问器
        """
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.data_sources: Dict[str, DataSource] = {}
        self.default_source = None
        self.query_cache = {}
        self.cache_size_limit = 1000  # 缓存条目数限制
    
    def get_capability_type(self) -> str:
        """
        获取能力类型
        """
        return 'data_access'
    
    def initialize(self) -> bool:
        """
        初始化数据访问器
        
        Returns:
            bool: 是否初始化成功
        """
        if not super().initialize():
            return False
        
        # 初始化所有注册的数据源
        success = True
        for name, source in self.data_sources.items():
            if not source.initialize():
                self.logger.error(f"Failed to initialize data source: {name}")
                success = False
        
        # 如果没有设置默认数据源，使用第一个可用的
        if not self.default_source and self.data_sources:
            self.default_source = next(iter(self.data_sources.keys()))
            self.logger.info(f"Set default data source to: {self.default_source}")
        
        return success
    
    def register_data_source(self, name: str, data_source: DataSource, set_as_default: bool = False) -> bool:
        """
        注册数据源
        
        Args:
            name: 数据源名称
            data_source: 数据源实例
            set_as_default: 是否设为默认数据源
            
        Returns:
            bool: 是否注册成功
        """
        if not isinstance(data_source, DataSource):
            self.logger.error(f"Invalid data source type for {name}")
            return False
        
        self.data_sources[name] = data_source
        self.logger.info(f"Registered data source: {name} ({data_source.source_type.value})")
        
        if set_as_default:
            self.default_source = name
            self.logger.info(f"Set {name} as default data source")
        
        # 如果是首次注册数据源且没有默认数据源，自动设为默认
        elif not self.default_source:
            self.default_source = name
            self.logger.info(f"Automatically set {name} as default data source")
        
        return True
    
    def create_data_source(self, name: str, source_type: Union[DataSourceType, str], config: Dict[str, Any], 
                          set_as_default: bool = False) -> bool:
        """
        创建并注册数据源
        
        Args:
            name: 数据源名称
            source_type: 数据源类型
            config: 数据源配置
            set_as_default: 是否设为默认数据源
            
        Returns:
            bool: 是否创建成功
        """
        try:
            # 转换类型字符串为枚举
            if isinstance(source_type, str):
                source_type = DataSourceType(source_type.lower())
            
            # 根据类型创建数据源实例
            data_source = self._create_source_instance(source_type, config)
            
            # 注册数据源
            return self.register_data_source(name, data_source, set_as_default)
            
        except Exception as e:
            self.logger.error(f"Failed to create data source {name}: {str(e)}", exc_info=True)
            return False
    
    def query(self, query: str, params: Optional[Dict[str, Any]] = None, 
              source_name: Optional[str] = None, use_cache: bool = True) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        执行查询
        
        Args:
            query: 查询语句
            params: 查询参数
            source_name: 数据源名称，None表示使用默认数据源
            use_cache: 是否使用缓存
            
        Returns:
            Union[List[Dict[str, Any]], Dict[str, Any]]: 查询结果
        """
        # 获取数据源
        data_source = self._get_data_source(source_name)
        if not data_source:
            raise ValueError(f"Data source not found: {source_name}")
        
        # 检查缓存
        cache_key = self._generate_cache_key(query, params, source_name)
        if use_cache and cache_key in self.query_cache:
            self.logger.debug(f"Cache hit for query: {query[:50]}...")
            return self.query_cache[cache_key]
        
        # 执行查询
        try:
            result = data_source.execute_query(query, params)
            
            # 缓存结果
            if use_cache:
                self._update_cache(cache_key, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Query execution failed: {str(e)}", exc_info=True)
            raise
    
    def execute(self, command: str, params: Optional[Dict[str, Any]] = None, 
                source_name: Optional[str] = None) -> int:
        """
        执行命令（如插入、更新、删除等）
        
        Args:
            command: 命令语句
            params: 命令参数
            source_name: 数据源名称，None表示使用默认数据源
            
        Returns:
            int: 受影响的行数
        """
        # 获取数据源
        data_source = self._get_data_source(source_name)
        if not data_source:
            raise ValueError(f"Data source not found: {source_name}")
        
        # 执行命令
        try:
            result = data_source.execute_command(command, params)
            
            # 命令执行会修改数据，清除相关缓存
            self._clear_related_cache(source_name)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Command execution failed: {str(e)}", exc_info=True)
            raise
    
    def transaction(self, operations: List[Dict[str, Any]], source_name: Optional[str] = None) -> bool:
        """
        执行事务操作
        
        Args:
            operations: 操作列表，每个操作包含type('query'/'command'), statement, params
            source_name: 数据源名称
            
        Returns:
            bool: 是否执行成功
        """
        # 获取数据源
        data_source = self._get_data_source(source_name)
        if not data_source:
            raise ValueError(f"Data source not found: {source_name}")
        
        # 开始事务
        if not data_source.begin_transaction():
            self.logger.error("Failed to begin transaction")
            return False
        
        try:
            # 执行所有操作
            for op in operations:
                op_type = op.get('type', 'query')
                statement = op.get('statement', '')
                params = op.get('params', {})
                
                if op_type == 'query':
                    data_source.execute_query(statement, params)
                elif op_type == 'command':
                    data_source.execute_command(statement, params)
                else:
                    raise ValueError(f"Unknown operation type: {op_type}")
            
            # 提交事务
            if not data_source.commit_transaction():
                self.logger.error("Failed to commit transaction")
                return False
            
            # 清除相关缓存
            self._clear_related_cache(source_name)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Transaction failed: {str(e)}", exc_info=True)
            # 回滚事务
            data_source.rollback_transaction()
            return False
    
    def get_schema(self, entity: Optional[str] = None, source_name: Optional[str] = None) -> Dict[str, Any]:
        """
        获取数据源模式
        
        Args:
            entity: 实体名称，None表示获取所有实体
            source_name: 数据源名称
            
        Returns:
            Dict[str, Any]: 模式信息
        """
        # 获取数据源
        data_source = self._get_data_source(source_name)
        if not data_source:
            raise ValueError(f"Data source not found: {source_name}")
        
        return data_source.get_schema(entity)
    
    def get_data_source_status(self, source_name: Optional[str] = None) -> Dict[str, Any]:
        """
        获取数据源状态
        
        Args:
            source_name: 数据源名称，None表示获取所有数据源状态
            
        Returns:
            Dict[str, Any]: 状态信息
        """
        if source_name is not None:
            # 获取特定数据源状态
            data_source = self._get_data_source(source_name)
            if not data_source:
                raise ValueError(f"Data source not found: {source_name}")
            return {
                source_name: data_source.get_status()
            }
        else:
            # 获取所有数据源状态
            status = {}
            for name, source in self.data_sources.items():
                status[name] = source.get_status()
            return status
    
    def set_default_source(self, source_name: str) -> bool:
        """
        设置默认数据源
        
        Args:
            source_name: 数据源名称
            
        Returns:
            bool: 是否设置成功
        """
        if source_name in self.data_sources:
            self.default_source = source_name
            self.logger.info(f"Set default data source to: {source_name}")
            return True
        else:
            self.logger.error(f"Data source not found: {source_name}")
            return False
    
    def clear_cache(self, source_name: Optional[str] = None) -> int:
        """
        清除缓存
        
        Args:
            source_name: 数据源名称，None表示清除所有缓存
            
        Returns:
            int: 清除的缓存条目数
        """
        if source_name:
            # 清除特定数据源的缓存
            cleared = 0
            keys_to_remove = []
            for key in self.query_cache:
                if f"source:{source_name}@" in key:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.query_cache[key]
                cleared += 1
            
            self.logger.info(f"Cleared {cleared} cache entries for data source: {source_name}")
            return cleared
        else:
            # 清除所有缓存
            count = len(self.query_cache)
            self.query_cache.clear()
            self.logger.info(f"Cleared all {count} cache entries")
            return count
    
    def close(self) -> bool:
        """
        关闭所有数据源连接
        
        Returns:
            bool: 是否关闭成功
        """
        success = True
        for name, source in self.data_sources.items():
            if not source.close():
                self.logger.error(f"Failed to close data source: {name}")
                success = False
        
        # 清空缓存
        self.query_cache.clear()
        
        return success
    
    def _get_data_source(self, source_name: Optional[str]) -> Optional[DataSource]:
        """
        获取数据源实例
        
        Args:
            source_name: 数据源名称，None表示使用默认数据源
            
        Returns:
            Optional[DataSource]: 数据源实例
        """
        name = source_name or self.default_source
        
        if not name:
            self.logger.error("No data source specified and no default data source set")
            return None
        
        data_source = self.data_sources.get(name)
        if not data_source:
            self.logger.error(f"Data source not found: {name}")
            return None
        
        return data_source
    
    def _create_source_instance(self, source_type: DataSourceType, config: Dict[str, Any]) -> DataSource:
        """
        创建数据源实例
        
        Args:
            source_type: 数据源类型
            config: 配置信息
            
        Returns:
            DataSource: 数据源实例
        """
        # 根据类型创建不同的数据源实例
        if source_type == DataSourceType.MEMORY:
            from .data_source import MemoryDataSource
            return MemoryDataSource(config)
        elif source_type == DataSourceType.MYSQL:
            # MySQL数据源（示例，需要实际实现）
            return self._create_mysql_source(config)
        elif source_type == DataSourceType.SQLITE:
            # SQLite数据源（示例，需要实际实现）
            return self._create_sqlite_source(config)
        else:
            # 创建默认的基类实例，实际应用中需要为每种类型实现具体的子类
            return DataSource(source_type, config)
    
    def _create_mysql_source(self, config: Dict[str, Any]) -> DataSource:
        """
        创建MySQL数据源（示例实现）
        """
        # 这里应该返回MySQL特定的DataSource实现
        # 由于是示例，返回基类实例
        return DataSource(DataSourceType.MYSQL, config)
    
    def _create_sqlite_source(self, config: Dict[str, Any]) -> DataSource:
        """
        创建SQLite数据源（示例实现）
        """
        # 这里应该返回SQLite特定的DataSource实现
        # 由于是示例，返回基类实例
        return DataSource(DataSourceType.SQLITE, config)
    
    def _generate_cache_key(self, query: str, params: Optional[Dict[str, Any]], 
                          source_name: Optional[str]) -> str:
        """
        生成缓存键
        
        Args:
            query: 查询语句
            params: 查询参数
            source_name: 数据源名称
            
        Returns:
            str: 缓存键
        """
        import hashlib
        import json
        
        source = source_name or self.default_source or 'default'
        params_str = json.dumps(params, sort_keys=True) if params else ''
        
        # 创建键的基础部分
        base_key = f"source:{source}@query:{query}@params:{params_str}"
        
        # 生成哈希值以避免键过长
        hash_obj = hashlib.md5(base_key.encode('utf-8'))
        return f"cache:{hash_obj.hexdigest()}"
    
    def _update_cache(self, key: str, result: Any) -> None:
        """
        更新缓存
        
        Args:
            key: 缓存键
            result: 要缓存的结果
        """
        # 限制缓存大小
        if len(self.query_cache) >= self.cache_size_limit:
            # 移除最旧的缓存项（简单的FIFO策略）
            oldest_key = next(iter(self.query_cache.keys()))
            del self.query_cache[oldest_key]
        
        # 添加到缓存
        self.query_cache[key] = result
    
    def _clear_related_cache(self, source_name: Optional[str]) -> None:
        """
        清除相关的缓存
        
        Args:
            source_name: 数据源名称
        """
        # 对于写操作，简单地清除整个数据源的缓存
        self.clear_cache(source_name)
