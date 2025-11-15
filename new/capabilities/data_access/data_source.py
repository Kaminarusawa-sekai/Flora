"""数据源接口和实现"""
from typing import Dict, Any, List, Optional, Tuple, Union
from ..capability_base import CapabilityBase
from enum import Enum
import logging
import threading
import json
import requests
from requests.auth import HTTPBasicAuth, HTTPDigestAuth
import time
import hashlib


class DataSourceType(Enum):
    """
    数据源类型枚举
    """
    MYSQL = "mysql"
    POSTGRES = "postgres"
    SQLITE = "sqlite"
    REDIS = "redis"
    MONGODB = "mongodb"
    CSV = "csv"
    JSON = "json"
    REST_API = "rest_api"
    ELASTICSEARCH = "elasticsearch"
    FILE = "file"
    API = "api"
    MEMORY = "memory"
    CUSTOM = "custom"


class DataSource(CapabilityBase):
    """
    数据源基类
    提供统一的数据源接口
    """
    
    def __init__(self, source_type: Union[DataSourceType, str], config: Dict[str, Any]):
        """
        初始化数据源
        
        Args:
            source_type: 数据源类型（枚举或字符串）
            config: 数据源配置
        """
        if isinstance(source_type, str):
            source_type = DataSourceType(source_type.lower())
            
        super().__init__()
        self.source_type = source_type
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{source_type.value}")
        self.connection = None
        self.is_connected = False
        self.lock = threading.RLock()  # 可重入锁，用于并发控制
    
    def get_capability_type(self) -> str:
        """
        获取能力类型
        """
        return 'data_source'
    
    def initialize(self) -> bool:
        """
        初始化数据源
        
        Returns:
            bool: 是否初始化成功
        """
        if not super().initialize():
            return False
        
        try:
            # 建立连接
            self.connection = self._connect()
            self.is_connected = True
            self.logger.info(f"Connected to {self.source_type.value} data source")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.source_type.value} data source: {str(e)}", exc_info=True)
            self.is_connected = False
            return False
    
    def close(self) -> bool:
        """
        关闭数据源连接
        
        Returns:
            bool: 是否关闭成功
        """
        try:
            if self.connection:
                self._disconnect()
                self.is_connected = False
                self.logger.info(f"Disconnected from {self.source_type.value} data source")
            return True
        except Exception as e:
            self.logger.error(f"Error closing {self.source_type.value} data source: {str(e)}", exc_info=True)
            return False
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        执行查询
        
        Args:
            query: 查询语句
            params: 查询参数
            
        Returns:
            Union[List[Dict[str, Any]], Dict[str, Any]]: 查询结果
        """
        if not self.is_connected:
            raise RuntimeError("Data source not connected")
        
        try:
            return self._execute_query(query, params)
        except Exception as e:
            self.logger.error(f"Error executing query: {str(e)}", exc_info=True)
            raise
    
    def execute_command(self, command: str, params: Optional[Dict[str, Any]] = None) -> int:
        """
        执行命令（如插入、更新、删除等）
        
        Args:
            command: 命令语句
            params: 命令参数
            
        Returns:
            int: 受影响的行数
        """
        if not self.is_connected:
            raise RuntimeError("Data source not connected")
        
        try:
            return self._execute_command(command, params)
        except Exception as e:
            self.logger.error(f"Error executing command: {str(e)}", exc_info=True)
            raise
    
    def begin_transaction(self) -> bool:
        """
        开始事务
        
        Returns:
            bool: 是否成功
        """
        try:
            if self.is_connected:
                return self._begin_transaction()
            return False
        except Exception as e:
            self.logger.error(f"Error beginning transaction: {str(e)}", exc_info=True)
            return False
    
    def commit_transaction(self) -> bool:
        """
        提交事务
        
        Returns:
            bool: 是否成功
        """
        try:
            if self.is_connected:
                return self._commit_transaction()
            return False
        except Exception as e:
            self.logger.error(f"Error committing transaction: {str(e)}", exc_info=True)
            return False
    
    def rollback_transaction(self) -> bool:
        """
        回滚事务
        
        Returns:
            bool: 是否成功
        """
        try:
            if self.is_connected:
                return self._rollback_transaction()
            return False
        except Exception as e:
            self.logger.error(f"Error rolling back transaction: {str(e)}", exc_info=True)
            return False
    
    def get_schema(self, entity: Optional[str] = None) -> Dict[str, Any]:
        """
        获取数据源模式信息
        
        Args:
            entity: 实体名称（如表名），如果为None则获取所有实体
            
        Returns:
            Dict[str, Any]: 模式信息
        """
        if not self.is_connected:
            raise RuntimeError("Data source not connected")
        
        try:
            return self._get_schema(entity)
        except Exception as e:
            self.logger.error(f"Error getting schema: {str(e)}", exc_info=True)
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取数据源状态
        
        Returns:
            Dict[str, Any]: 状态信息
        """
        status = super().get_status()
        status.update({
            'source_type': self.source_type.value,
            'is_connected': self.is_connected,
            'config_summary': self._get_config_summary()
        })
        return status
    
    def _get_config_summary(self) -> Dict[str, Any]:
        """
        获取配置摘要（不包含敏感信息）
        
        Returns:
            Dict[str, Any]: 配置摘要
        """
        # 创建配置的副本，移除敏感信息
        summary = {}
        sensitive_keys = ['password', 'key', 'secret', 'token', 'credential']
        
        for key, value in self.config.items():
            if not any(sensitive in key.lower() for sensitive in sensitive_keys):
                summary[key] = value
            else:
                summary[key] = '********'
        
        return summary
    
    # 以下是需要子类实现的抽象方法
    def _connect(self):
        """
        连接到数据源
        
        Returns:
            连接对象
        """
        raise NotImplementedError("Subclass must implement _connect method")
    
    def _disconnect(self):
        """
        断开连接
        """
        raise NotImplementedError("Subclass must implement _disconnect method")
    
    def _execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        执行查询的具体实现
        """
        raise NotImplementedError("Subclass must implement _execute_query method")
    
    def _execute_command(self, command: str, params: Optional[Dict[str, Any]] = None) -> int:
        """
        执行命令的具体实现
        """
        raise NotImplementedError("Subclass must implement _execute_command method")
    
    def _begin_transaction(self) -> bool:
        """
        开始事务的具体实现
        """
        # 默认不支持事务
        return False
    
    def _commit_transaction(self) -> bool:
        """
        提交事务的具体实现
        """
        # 默认不支持事务
        return False
    
    def _rollback_transaction(self) -> bool:
        """
        回滚事务的具体实现
        """
        # 默认不支持事务
        return False
    
    def test_connection(self) -> bool:
        """
        测试数据源连接
        
        Returns:
            bool: 连接是否成功
        """
        try:
            # 尝试一个简单的操作来测试连接
            self.execute_query(self._get_test_query())
            return True
        except Exception as e:
            self.logger.warning(f"Connection test failed: {str(e)}")
            return False
    
    def _get_test_query(self) -> str:
        """
        获取用于测试连接的查询语句
        
        Returns:
            str: 测试查询语句
        """
        # 默认返回一个简单的查询，子类可以重写
        return "SELECT 1"
    
    def _clean_cache(self):
        """
        清理过期的缓存条目
        """
        current_time = time.time()
        # 使用列表推导式创建新的缓存字典，只保留未过期的条目
        self.cache = {k: v for k, (data, timestamp) in self.cache.items() 
                     if current_time - timestamp < self.cache_ttl}
    
    def _clean_cache(self):
        """
        清理过期的缓存条目
        """
        if not self.cache_enabled:
            return
        
        current_time = time.time()
        # 使用列表推导式创建新的缓存字典，只保留未过期的条目
        self.cache = {k: v for k, (data, timestamp) in self.cache.items() 
                     if current_time - timestamp < self.cache_ttl}
    
    def _get_schema(self, entity: Optional[str] = None) -> Dict[str, Any]:
        """
        获取模式信息的具体实现
        """
        raise NotImplementedError("Subclass must implement _get_schema method")


class MemoryDataSource(DataSource):
    """
    增强的内存数据源实现
    支持更复杂的查询和事务操作
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化内存数据源
        
        Args:
            config: 配置信息，包含tables定义和初始数据
        """
        if config is None:
            config = {}
        super().__init__(DataSourceType.MEMORY, config)
        self.data = {}
        self.schema = {}
        self.transaction_data = None  # 事务数据备份
    
    def _connect(self):
        """
        连接到内存数据源
        """
        # 初始化数据表和结构
        tables = self.config.get('tables', {})
        for table_name, table_schema in tables.items():
            self.schema[table_name] = table_schema
            self.data[table_name] = []
        
        # 加载初始数据
        initial_data = self.config.get('initial_data', {})
        for table_name, records in initial_data.items():
            if table_name in self.data:
                self.data[table_name].extend(records)
        
        return self.data
    
    def _disconnect(self):
        """
        断开内存数据源连接
        """
        # 可选：清空数据
        if self.config.get('clear_on_disconnect', False):
            self.data.clear()
    
    def _execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        执行内存查询
        
        支持的查询格式：
        - "select * from table" - 获取表中所有数据
        - "select field1,field2 from table" - 获取表中指定字段的数据
        - "get table" - 获取整个表
        - "select * from table where condition" - 支持简单条件过滤
        """
        import re
        
        try:
            with self.lock:
                # 使用当前数据（事务中使用事务数据）
                current_data = self.transaction_data if self.transaction_data else self.data
                
                # 记录查询开始
                self.logger.debug(f"Executing query: {query}, params: {params}")
                
                # 简单的查询解析
                query = query.lower().strip()
                
                # 匹配 "get table" 格式
                get_match = re.match(r'get\s+([\w]+)', query)
                if get_match:
                    table = get_match.group(1)
                    result = current_data.get(table, []).copy()
                    self.logger.debug(f"Query executed successfully, returned {len(result)} records")
                    return result
                
                # 匹配 "select * from table" 或 "select fields from table" 格式
                select_pattern = r'select\s+([\w\*,\s]+)\s+from\s+([\w]+)(\s+where\s+(.+))?'
                select_match = re.match(select_pattern, query)
                if select_match:
                    fields_str = select_match.group(1)
                    table = select_match.group(2)
                    where_clause = select_match.group(4)  # 可能为None
                    
                    # 获取表数据
                    table_data = current_data.get(table, [])
                    if not table_data:
                        self.logger.debug(f"Table {table} not found or empty")
                        return []
                    
                    # 过滤数据（如果有WHERE条件）
                    filtered_data = self._filter_data(table_data, where_clause, params)
                    
                    # 处理字段选择
                    if fields_str == '*':
                        # 返回所有字段
                        result = [dict(item) for item in filtered_data]
                    else:
                        # 返回指定字段
                        fields = [f.strip() for f in fields_str.split(',')]
                        result = []
                        for item in filtered_data:
                            filtered_item = {}
                            for field in fields:
                                if field in item:
                                    filtered_item[field] = item[field]
                            result.append(filtered_item)
                    
                    self.logger.debug(f"Query executed successfully, returned {len(result)} records")
                    return result
                
                self.logger.warning(f"Unknown query format: {query}")
                # 默认返回空列表
                return []
        except Exception as e:
            self.logger.error(f"Error executing query: {str(e)}", exc_info=True)
            raise
    
    
    def _execute_command(self, command: str, params: Optional[Dict[str, Any]] = None) -> int:
        """
        执行内存命令
        
        支持的命令格式：
        - "insert into table values {...}" - 插入数据
        - "update table set field=value where condition" - 更新数据
        - "delete from table where condition" - 删除数据
        - "create table" - 创建表
        - "drop table" - 删除表
        - "truncate table" - 清空表
        """
        import re
        
        try:
            with self.lock:
                # 使用当前数据（事务中使用事务数据）
                current_data = self.transaction_data if self.transaction_data else self.data
                
                # 记录命令开始
                self.logger.debug(f"Executing command: {command}, params: {params}")
                
                command = command.lower().strip()
                
                # 匹配 "create table" 格式
                create_match = re.match(r'create\s+table\s+([\w]+)', command)
                if create_match:
                    table = create_match.group(1)
                    if table not in current_data:
                        current_data[table] = []
                        # 尝试解析表结构
                        self._parse_table_structure(command, table)
                        self.logger.info(f"Created table: {table}")
                    else:
                        self.logger.warning(f"Table {table} already exists, skipping creation")
                    return 1
                
                # 匹配 "drop table" 格式
                elif re.match(r'drop\s+table\s+([\w]+)', command):
                    table = re.match(r'drop\s+table\s+([\w]+)', command).group(1)
                    if table in current_data:
                        del current_data[table]
                        if table in self.schema:
                            del self.schema[table]
                        self.logger.info(f"Dropped table: {table}")
                        return 1
                    else:
                        self.logger.warning(f"Table {table} does not exist, cannot drop")
                        return 0
                
                # 匹配 "truncate table" 格式
                truncate_match = re.match(r'truncate\s+table\s+([\w]+)', command)
                if truncate_match:
                    table = truncate_match.group(1)
                    if table in current_data:
                        count = len(current_data[table])
                        current_data[table] = []
                        self.logger.info(f"Truncated table {table}, removed {count} records")
                        return count
                    else:
                        self.logger.warning(f"Table {table} does not exist, cannot truncate")
                        return 0
                
                # 匹配 "insert into table" 格式
                insert_match = re.match(r'insert\s+into\s+([\w]+)', command)
                if insert_match and params:
                    table = insert_match.group(1)
                    if table not in current_data:
                        current_data[table] = []
                        self.logger.info(f"Auto-created table {table} for insertion")
                
                    # 支持单条插入和批量插入
                    if isinstance(params, list):
                        current_data[table].extend(params)
                        self.logger.info(f"Inserted {len(params)} records into table {table}")
                        return len(params)
                    else:
                        current_data[table].append(params)
                        self.logger.info(f"Inserted 1 record into table {table}")
                        return 1
                
                # 匹配 "update table" 格式
                update_match = re.match(r'update\s+([\w]+)\s+set\s+(.+?)(\s+where\s+(.+))?', command)
                if update_match:
                    table = update_match.group(1)
                    set_clause = update_match.group(2)
                    where_clause = update_match.group(4)  # 可能为None
                
                    if table in current_data:
                        updated_count = self._update_data(current_data[table], set_clause, where_clause, params)
                        self.logger.info(f"Updated {updated_count} records in table {table}")
                        return updated_count
                    else:
                        self.logger.warning(f"Table {table} does not exist, cannot update")
                        return 0
                
                # 匹配 "delete from table" 格式
                delete_match = re.match(r'delete\s+from\s+([\w]+)(\s+where\s+(.+))?', command)
                if delete_match:
                    table = delete_match.group(1)
                    where_clause = delete_match.group(3)  # 可能为None
                
                    if table in current_data:
                        deleted_count = self._delete_data(current_data[table], where_clause, params)
                        self.logger.info(f"Deleted {deleted_count} records from table {table}")
                        return deleted_count
                    else:
                        self.logger.warning(f"Table {table} does not exist, cannot delete")
                        return 0
                
                self.logger.warning(f"Unknown command format: {command}")
                return 0
        except Exception as e:
            self.logger.error(f"Error executing command: {str(e)}", exc_info=True)
            raise
    
    def _filter_data(self, data: List[Dict[str, Any]], where_clause: Optional[str], 
                    params: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        根据条件过滤数据
        
        Args:
            data: 原始数据列表
            where_clause: WHERE子句条件
            params: 参数字典
            
        Returns:
            过滤后的数据列表
        """
        try:
            self.logger.debug(f"Filtering data with where clause: {where_clause}")
            
            if not where_clause:
                self.logger.debug("No where clause provided, returning copy of all data")
                return data.copy()
            
            # 简单的条件解析和过滤
            import re
            filtered_data = []
            
            try:
                # 支持 AND 连接的条件
                conditions = re.split(r'\s+and\s+', where_clause.lower())
                self.logger.debug(f"Parsed conditions: {conditions}")
            except Exception as e:
                self.logger.error(f"Failed to parse where clause '{where_clause}': {str(e)}")
                # 如果解析失败，返回空列表
                return []
            
            for item in data:
                match = True
                for condition in conditions:
                    try:
                        if not self._evaluate_condition(item, condition, params):
                            match = False
                            break
                    except Exception as e:
                        self.logger.error(f"Error evaluating condition '{condition}': {str(e)}")
                        match = False
                        break
                if match:
                    filtered_data.append(item)
            
            self.logger.debug(f"Filtered {len(filtered_data)} items out of {len(data)}")
            return filtered_data
        except Exception as e:
            self.logger.error(f"Unexpected error in _filter_data: {str(e)}", exc_info=True)
            # 发生异常时返回空列表
            return []
    
    def _evaluate_condition(self, item: Dict[str, Any], condition: str, 
                           params: Optional[Dict[str, Any]]) -> bool:
        """
        评估单个条件是否满足
        
        Args:
            item: 数据项
            condition: 单个条件
            params: 参数字典
            
        Returns:
            条件是否满足
        """
        import re
        
        # 匹配字段名和操作符
        # 支持 =, !=, >, <, >=, <=, like, in
        pattern = r'([\w]+)\s*([!=<>]+|like|in)\s*(.+)'
        match = re.match(pattern, condition)
        
        if not match:
            return False
        
        field = match.group(1)
        operator = match.group(2)
        value_str = match.group(3).strip()
        
        # 如果字段不在数据项中，条件不满足
        if field not in item:
            return False
        
        # 尝试从参数中获取值
        if params and value_str.startswith(':') and value_str[1:] in params:
            value = params[value_str[1:]]
        else:
            # 尝试解析字面量值
            # 处理字符串、数字、布尔值等
            if value_str.startswith('"') and value_str.endswith('"'):
                value = value_str[1:-1]
            elif value_str.startswith("'") and value_str.endswith("'"):
                value = value_str[1:-1]
            elif value_str.lower() == 'true':
                value = True
            elif value_str.lower() == 'false':
                value = False
            elif value_str.isdigit():
                value = int(value_str)
            elif '.' in value_str and value_str.replace('.', '').isdigit():
                value = float(value_str)
            else:
                value = value_str
        
        # 执行比较
        item_value = item[field]
        
        if operator == '=':
            return item_value == value
        elif operator == '!=':
            return item_value != value
        elif operator == '>':
            return item_value > value
        elif operator == '<':
            return item_value < value
        elif operator == '>=':
            return item_value >= value
        elif operator == '<=':
            return item_value <= value
        elif operator.lower() == 'like':
            # 简单的 like 实现，支持 % 通配符
            if isinstance(item_value, str) and isinstance(value, str):
                pattern = value.replace('%', '.*')
                return bool(re.match(f'^{pattern}$', item_value))
            return False
        elif operator.lower() == 'in':
            # 简单的 in 实现，期望值是逗号分隔的列表
            in_values = [v.strip() for v in value_str.strip('()').split(',')]
            return str(item_value) in in_values
        
        return False
    
    def _update_data(self, data: List[Dict[str, Any]], set_clause: str, 
                    where_clause: Optional[str], params: Optional[Dict[str, Any]]) -> int:
        """
        更新数据
        
        Args:
            data: 原始数据列表
            set_clause: SET子句
            where_clause: WHERE子句条件
            params: 参数字典
            
        Returns:
            更新的行数
        """
        import re
        updated_count = 0
        
        # 解析SET子句
        set_pattern = r'([\w]+)\s*=\s*(.+?)\s*(,|$)'
        set_matches = re.findall(set_pattern, set_clause)
        
        if not set_matches:
            return 0
        
        # 构建更新表达式
        updates = []
        for field, value_str, _ in set_matches:
            # 尝试从参数中获取值
            if params and value_str.strip().startswith(':') and value_str.strip()[1:] in params:
                value = params[value_str.strip()[1:]]
                updates.append((field, value))
            else:
                # 尝试解析字面量值
                value_str = value_str.strip()
                if value_str.startswith('"') and value_str.endswith('"'):
                    value = value_str[1:-1]
                elif value_str.startswith("'") and value_str.endswith("'"):
                    value = value_str[1:-1]
                elif value_str.lower() == 'true':
                    value = True
                elif value_str.lower() == 'false':
                    value = False
                elif value_str.isdigit():
                    value = int(value_str)
                elif '.' in value_str and value_str.replace('.', '').isdigit():
                    value = float(value_str)
                else:
                    # 如果是字段引用
                    if re.match(r'^[\w]+$', value_str):
                        # 字段引用，使用其他字段的值
                        updates.append((field, value_str, True))  # True 表示是字段引用
                    else:
                        value = value_str
                        updates.append((field, value))
        
        # 遍历数据并更新
        for item in data:
            # 如果没有WHERE条件或满足WHERE条件
            if not where_clause or self._evaluate_condition(item, where_clause, params):
                for update in updates:
                    if len(update) == 3 and update[2]:  # 字段引用
                        if update[1] in item:
                            item[update[0]] = item[update[1]]
                    else:
                        item[update[0]] = update[1]
                updated_count += 1
        
        return updated_count
    
    def _delete_data(self, data: List[Dict[str, Any]], where_clause: Optional[str], 
                    params: Optional[Dict[str, Any]]) -> int:
        """
        删除数据
        
        Args:
            data: 原始数据列表
            where_clause: WHERE子句条件
            params: 参数字典
            
        Returns:
            删除的行数
        """
        if not where_clause:
            # 如果没有WHERE条件，删除所有数据
            deleted_count = len(data)
            data.clear()
            return deleted_count
        
        # 过滤出需要保留的数据（不满足条件的数据）
        remaining_data = []
        deleted_count = 0
        
        for item in data:
            if not self._evaluate_condition(item, where_clause, params):
                remaining_data.append(item)
            else:
                deleted_count += 1
        
        # 更新数据列表
        data.clear()
        data.extend(remaining_data)
        
        return deleted_count
    
    def _begin_transaction(self) -> bool:
        """
        开始事务
        
        Returns:
            是否成功开始事务
        """
        try:
            # 创建数据的深拷贝作为事务数据
            self.transaction_data = {}
            for table_name, table_data in self.data.items():
                # 深拷贝每个表的数据
                self.transaction_data[table_name] = [dict(record) for record in table_data]
            return True
        except Exception as e:
            self.logger.error(f"Failed to begin transaction: {str(e)}")
            self.transaction_data = None
            return False
    
    def _commit_transaction(self) -> bool:
        """
        提交事务
        
        Returns:
            是否成功提交事务
        """
        try:
            if self.transaction_data is not None:
                # 将事务数据复制回主数据
                self.data = {}
                for table_name, table_data in self.transaction_data.items():
                    self.data[table_name] = [dict(record) for record in table_data]
                # 清除事务数据
                self.transaction_data = None
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to commit transaction: {str(e)}")
            return False
    
    def _rollback_transaction(self) -> bool:
        """
        回滚事务
        
        Returns:
            是否成功回滚事务
        """
        try:
            # 直接清除事务数据，放弃所有修改
            self.transaction_data = None
            return True
        except Exception as e:
            self.logger.error(f"Failed to rollback transaction: {str(e)}")
            return False
    
    def _get_schema(self, entity: Optional[str] = None) -> Dict[str, Any]:
        """
        获取内存数据源模式
        """
        with self.lock:
            schema = {'tables': []}
            
            if entity:
                # 获取特定表的模式
                if entity in self.data:
                    table_data = self.data[entity]
                    fields = []
                    field_types = {}
                    
                    # 如果有显式模式，使用它
                    if entity in self.schema:
                        fields = list(self.schema[entity].keys())
                        field_types = self.schema[entity]
                    # 否则从数据推断
                    elif table_data:
                        fields = list(table_data[0].keys())
                        for field in fields:
                            # 推断字段类型
                            field_types[field] = self._infer_field_type(field, table_data)
                    
                    schema['tables'].append({
                        'name': entity,
                        'count': len(table_data),
                        'fields': fields,
                        'field_types': field_types
                    })
            else:
                # 获取所有表的模式
                for table_name, table_data in self.data.items():
                    fields = []
                    field_types = {}
                    
                    # 如果有显式模式，使用它
                    if table_name in self.schema:
                        fields = list(self.schema[table_name].keys())
                        field_types = self.schema[table_name]
                    # 否则从数据推断
                    elif table_data:
                        fields = list(table_data[0].keys())
                        for field in fields:
                            field_types[field] = self._infer_field_type(field, table_data)
                    
                    schema['tables'].append({
                        'name': table_name,
                        'count': len(table_data),
                        'fields': fields,
                        'field_types': field_types
                    })
            
            return schema


class SQLiteDataSource(DataSource):
    """
    SQLite数据源实现
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化SQLite数据源
        
        Args:
            config: 配置信息，包含数据库文件路径等
        """
        super().__init__(DataSourceType.SQLITE, config)
        self.conn = None
        self.cursor = None
    
    def _connect(self):
        """
        连接到SQLite数据库
        """
        import sqlite3
        
        db_path = self.config.get('db_path', ':memory:')
        self.logger.info(f"Connecting to SQLite database: {db_path}")
        
        # 创建连接
        self.conn = sqlite3.connect(
            db_path,
            check_same_thread=False,  # 允许在不同线程中使用
            timeout=self.config.get('timeout', 5)
        )
        
        # 设置为返回字典类型的结果
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        
        return self.conn
    
    def _disconnect(self):
        """
        断开SQLite连接
        """
        if self.cursor:
            self.cursor.close()
            self.cursor = None
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def _execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        执行SQLite查询
        """
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            
            # 将结果转换为字典列表
            results = []
            for row in self.cursor.fetchall():
                results.append(dict(row))
            
            return results
        except Exception as e:
            self.logger.error(f"SQLite query error: {str(e)}")
            raise
    
    def _execute_command(self, command: str, params: Optional[Dict[str, Any]] = None) -> int:
        """
        执行SQLite命令
        """
        try:
            if params:
                self.cursor.execute(command, params)
            else:
                self.cursor.execute(command)
            
            # 提交更改
            self.conn.commit()
            
            return self.cursor.rowcount
        except Exception as e:
            self.logger.error(f"SQLite command error: {str(e)}")
            self.conn.rollback()
            raise
    
    def _begin_transaction(self) -> bool:
        """
        开始事务
        """
        try:
            self.cursor.execute("BEGIN TRANSACTION")
            return True
        except Exception as e:
            self.logger.error(f"Failed to begin transaction: {str(e)}")
            return False
    
    def _commit_transaction(self) -> bool:
        """
        提交事务
        """
        try:
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to commit transaction: {str(e)}")
            return False
    
    def _rollback_transaction(self) -> bool:
        """
        回滚事务
        """
        try:
            self.conn.rollback()
            return True
        except Exception as e:
            self.logger.error(f"Failed to rollback transaction: {str(e)}")
            return False
    
    def _get_schema(self, entity: Optional[str] = None) -> Dict[str, Any]:
        """
        获取SQLite数据库模式
        """
        schema = {'tables': []}
        
        try:
            # 获取表列表
            if entity:
                tables = [entity]
            else:
                self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in self.cursor.fetchall()]
            
            # 获取每个表的结构
            for table in tables:
                # 获取表信息
                self.cursor.execute(f"PRAGMA table_info({table})")
                columns = []
                field_types = {}
                
                for col_info in self.cursor.fetchall():
                    column_name = col_info['name']
                    column_type = col_info['type']
                    columns.append(column_name)
                    field_types[column_name] = column_type
                
                # 获取记录数
                self.cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = self.cursor.fetchone()[0]
                
                schema['tables'].append({
                    'name': table,
                    'count': count,
                    'fields': columns,
                    'field_types': field_types
                })
            
            return schema
        except Exception as e:
            self.logger.error(f"Error getting schema: {str(e)}")
            raise
    
    def _get_test_query(self) -> str:
        """
        获取测试查询
        """
        return "SELECT 1 AS test"
    
    def _begin_transaction(self) -> bool:
        """
        开始事务
        """
        with self.lock:
            # 创建数据的深拷贝作为事务数据
            try:
                self.transaction_data = {}
                for table_name, records in self.data.items():
                    # 深拷贝每条记录
                    self.transaction_data[table_name] = [dict(record) for record in records]
                return True
            except Exception as e:
                self.logger.error(f"Failed to begin transaction: {str(e)}")
                self.transaction_data = None
                return False
    
    def _commit_transaction(self) -> bool:
        """
        提交事务
        """
        with self.lock:
            if self.transaction_data:
                # 将事务数据复制回主数据
                self.data = {}
                for table_name, records in self.transaction_data.items():
                    self.data[table_name] = [dict(record) for record in records]
                self.transaction_data = None
                return True
            return False
    
    def _rollback_transaction(self) -> bool:
        """
        回滚事务
        """
        with self.lock:
            self.transaction_data = None
            return True
    
    def _filter_data(self, data: List[Dict[str, Any]], where_clause: Optional[str], 
                    params: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        根据WHERE子句过滤数据
        """
        if not where_clause:
            return data
        
        filtered = []
        for item in data:
            if self._evaluate_condition(item, where_clause, params):
                filtered.append(item)
        
        return filtered
    
    def _evaluate_condition(self, item: Dict[str, Any], condition: str, 
                           params: Optional[Dict[str, Any]]) -> bool:
        """
        评估条件是否满足
        """
        # 替换参数
        if params:
            for key, value in params.items():
                placeholder = f":{key}"
                if placeholder in condition:
                    if isinstance(value, str):
                        condition = condition.replace(placeholder, f"'{value}'")
                    else:
                        condition = condition.replace(placeholder, str(value))
        
        # 替换字段值
        for field, value in item.items():
            # 安全替换，避免部分匹配
            pattern = r'\b' + re.escape(field) + r'\b'
            if re.search(pattern, condition):
                if isinstance(value, str):
                    condition = re.sub(pattern, f"'{value}'", condition)
                else:
                    condition = re.sub(pattern, str(value), condition)
        
        # 简单的条件评估
        # 注意：这是一个简化实现，存在安全风险
        try:
            # 定义安全的全局变量
            safe_globals = {'__builtins__': {}}
            return bool(eval(condition, safe_globals))
        except:
            return False
    
    def _update_data(self, data: List[Dict[str, Any]], set_clause: str, 
                    where_clause: Optional[str], params: Optional[Dict[str, Any]]) -> int:
        """
        更新数据
        """
        updated_count = 0
        
        # 解析SET子句
        updates = {}
        for assignment in set_clause.split(','):
            if '=' in assignment:
                field, value = assignment.split('=', 1)
                field = field.strip()
                value = value.strip()
                updates[field] = value
        
        # 应用更新
        for item in data:
            if not where_clause or self._evaluate_condition(item, where_clause, params):
                # 替换更新值中的参数和字段引用
                for field, value_expr in updates.items():
                    # 创建表达式的副本进行替换
                    expr_copy = value_expr
                    
                    # 替换参数
                    if params:
                        for key, param_value in params.items():
                            placeholder = f":{key}"
                            if placeholder in expr_copy:
                                if isinstance(param_value, str):
                                    expr_copy = expr_copy.replace(placeholder, f"'{param_value}'")
                                else:
                                    expr_copy = expr_copy.replace(placeholder, str(param_value))
                    
                    # 替换字段引用（当前记录的值）
                    for item_field, item_value in item.items():
                        pattern = r'\b' + re.escape(item_field) + r'\b'
                        if re.search(pattern, expr_copy):
                            if isinstance(item_value, str):
                                expr_copy = re.sub(pattern, f"'{item_value}'", expr_copy)
                            else:
                                expr_copy = re.sub(pattern, str(item_value), expr_copy)
                    
                    # 尝试评估表达式
                    try:
                        # 简单处理：如果是纯字符串或数字，直接赋值
                        if (expr_copy.startswith("'") and expr_copy.endswith("'") or
                            expr_copy.startswith('"') and expr_copy.endswith('"')):
                            item[field] = expr_copy[1:-1]
                        elif expr_copy.isdigit():
                            item[field] = int(expr_copy)
                        elif '.' in expr_copy and all(part.isdigit() for part in expr_copy.split('.', 1)):
                            item[field] = float(expr_copy)
                        elif expr_copy.lower() in ('true', 'false'):
                            item[field] = expr_copy.lower() == 'true'
                        else:
                            # 尝试评估更复杂的表达式
                            safe_globals = {'__builtins__': {}}
                            item[field] = eval(expr_copy, safe_globals)
                    except:
                        # 如果评估失败，使用原始值
                        pass
                
                updated_count += 1
        
        return updated_count
    
    def _delete_data(self, data: List[Dict[str, Any]], where_clause: Optional[str], 
                    params: Optional[Dict[str, Any]]) -> int:
        """
        删除数据
        """
        original_count = len(data)
        
        if not where_clause:
            # 删除所有数据
            data.clear()
            return original_count
        
        # 按条件删除
        i = 0
        while i < len(data):
            if self._evaluate_condition(data[i], where_clause, params):
                del data[i]
            else:
                i += 1
        
        return original_count - len(data)
    
    def _parse_table_structure(self, create_command: str, table_name: str) -> None:
        """
        解析CREATE TABLE命令中的表结构
        """
        # 查找括号内的字段定义
        start = create_command.find('(')
        end = create_command.rfind(')')
        
        if start != -1 and end != -1 and start < end:
            fields_str = create_command[start+1:end].strip()
            field_defs = [f.strip() for f in fields_str.split(',')]
            
            # 解析字段定义
            table_schema = {}
            for field_def in field_defs:
                parts = field_def.split()
                if parts:
                    field_name = parts[0]
                    field_type = 'string'  # 默认类型
                    if len(parts) > 1:
                        # 提取类型信息
                        field_type = parts[1].lower()
                        # 简化类型映射
                        if field_type in ('int', 'integer', 'long', 'short'):
                            field_type = 'integer'
                        elif field_type in ('float', 'double', 'decimal', 'real'):
                            field_type = 'float'
                        elif field_type in ('bool', 'boolean'):
                            field_type = 'boolean'
                        elif field_type in ('date', 'time', 'datetime', 'timestamp'):
                            field_type = 'datetime'
                        else:
                            field_type = 'string'
                    
                    table_schema[field_name] = field_type
            
            self.schema[table_name] = table_schema
    
    def _infer_field_type(self, field: str, data: List[Dict[str, Any]]) -> str:
        """
        从数据推断字段类型
        """
        # 检查所有非空值来推断类型
        for record in data:
            if field in record and record[field] is not None:
                value = record[field]
                if isinstance(value, bool):
                    return 'boolean'
                elif isinstance(value, int):
                    return 'integer'
                elif isinstance(value, float):
                    return 'float'
                elif isinstance(value, str):
                    # 尝试解析为数字或布尔值
                    if value.lower() in ('true', 'false'):
                        return 'boolean'
                    try:
                        int(value)
                        return 'integer'
                    except ValueError:
                        try:
                            float(value)
                            return 'float'
                        except ValueError:
                            # 尝试解析日期
                            import re
                            date_patterns = [
                                r'^\d{4}-\d{2}-\d{2}$',  # YYYY-MM-DD
                                r'^\d{2}/\d{2}/\d{4}$',  # MM/DD/YYYY
                                r'^\d{4}/\d{2}/\d{2}$',  # YYYY/MM/DD
                                r'^\d{8}$',  # YYYYMMDD
                            ]
                            for pattern in date_patterns:
                                if re.match(pattern, value):
                                    return 'date'
                            # 尝试解析日期时间
                            datetime_patterns = [
                                r'^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}$',
                                r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$',
                            ]
                            for pattern in datetime_patterns:
                                if re.match(pattern, value):
                                    return 'datetime'
                    return 'string'
                elif hasattr(value, 'isoformat'):  # datetime对象
                    return 'datetime'
        
        # 默认返回字符串类型
        return 'string'
    
    def _get_test_query(self) -> str:
        """
        获取测试查询
        """
        return "SELECT 1"


class CSVDataSource(DataSource):
    """
    CSV文件数据源实现
    支持读取CSV文件作为数据源
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化CSV数据源
        
        Args:
            config: 配置信息，包含文件路径、编码等
        """
        super().__init__(DataSourceType.CSV, config)
        self.file_data = {}
        self.file_paths = {}
        self.delimiter = self.config.get('delimiter', ',')
        self.encoding = self.config.get('encoding', 'utf-8')
        self.header_row = self.config.get('header_row', 0)
        self.skip_rows = self.config.get('skip_rows', 0)
    
    def _connect(self):
        """
        连接到CSV数据源（加载文件）
        """
        import csv
        import os
        
        # 处理单个文件配置
        if 'file_path' in self.config:
            table_name = self.config.get('table_name', 'data')
            file_path = self.config['file_path']
            self.file_paths[table_name] = file_path
            self._load_csv_file(table_name, file_path)
        
        # 处理多个文件配置
        elif 'files' in self.config:
            for table_name, file_info in self.config['files'].items():
                if isinstance(file_info, str):
                    file_path = file_info
                else:
                    file_path = file_info.get('path')
                    
                if file_path:
                    self.file_paths[table_name] = file_path
                    self._load_csv_file(table_name, file_path)
        
        return self.file_data
    
    def _load_csv_file(self, table_name: str, file_path: str):
        """
        加载CSV文件数据
        """
        import csv
        import os
        
        if not os.path.exists(file_path):
            self.logger.warning(f"CSV file not found: {file_path}")
            self.file_data[table_name] = []
            return
        
        try:
            with open(file_path, 'r', encoding=self.encoding, newline='') as f:
                # 跳过指定行数
                for _ in range(self.skip_rows):
                    next(f, None)
                
                # 使用csv.reader读取文件
                reader = csv.reader(f, delimiter=self.delimiter)
                
                # 获取表头
                headers = None
                if self.header_row == 0:
                    headers = next(reader, None)
                else:
                    # 找到正确的表头行
                    for i, row in enumerate(reader):
                        if i == self.header_row - 1:
                            headers = row
                            break
                
                if not headers:
                    # 如果没有表头，使用数字索引
                    headers = [f'col_{i}' for i in range(len(next(reader, [])))]
                    f.seek(0)
                    for _ in range(self.skip_rows + (1 if self.header_row == 0 else self.header_row)):
                        next(f, None)
                    reader = csv.reader(f, delimiter=self.delimiter)
                
                # 读取数据
                data = []
                for row in reader:
                    # 确保行长度与表头一致
                    if len(row) < len(headers):
                        row.extend([''] * (len(headers) - len(row)))
                    elif len(row) > len(headers):
                        row = row[:len(headers)]
                    
                    # 创建字典
                    record = {headers[i]: value for i, value in enumerate(row)}
                    data.append(record)
                
                self.file_data[table_name] = data
                self.logger.info(f"Loaded CSV file {file_path} with {len(data)} records as table {table_name}")
        except Exception as e:
            self.logger.error(f"Error loading CSV file {file_path}: {str(e)}")
            self.file_data[table_name] = []
    
    def _disconnect(self):
        """
        断开CSV数据源连接（清理内存）
        """
        self.file_data.clear()
    
    def _execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        执行CSV数据查询
        支持简单的查询语法
        """
        import re
        
        query = query.lower().strip()
        
        # 匹配简单的查询格式
        select_pattern = r'select\s+([\w\*,\s]+)\s+from\s+([\w]+)(\s+where\s+(.+))?'
        select_match = re.match(select_pattern, query)
        
        if not select_match:
            self.logger.warning(f"Unsupported query format: {query}")
            return []
        
        fields_str = select_match.group(1)
        table_name = select_match.group(2)
        where_clause = select_match.group(4)  # 可能为None
        
        # 检查表是否存在
        if table_name not in self.file_data:
            self.logger.warning(f"Table not found: {table_name}")
            return []
        
        # 获取表数据
        table_data = self.file_data[table_name]
        
        # 过滤数据
        filtered_data = []
        if where_clause:
            # 简单的条件过滤
            for record in table_data:
                if self._evaluate_condition(record, where_clause, params):
                    filtered_data.append(record)
        else:
            filtered_data = table_data
        
        # 选择字段
        if fields_str == '*':
            return [dict(record) for record in filtered_data]
        else:
            fields = [f.strip() for f in fields_str.split(',')]
            result = []
            for record in filtered_data:
                filtered_record = {}
                for field in fields:
                    if field in record:
                        filtered_record[field] = record[field]
                result.append(filtered_record)
            return result
    
    def _execute_command(self, command: str, params: Optional[Dict[str, Any]] = None) -> int:
        """
        执行CSV命令
        注意：CSV数据源是只读的，只支持加载新文件
        """
        import re
        import os
        
        command = command.lower().strip()
        
        # 支持加载新的CSV文件
        load_match = re.match(r'load\s+csv\s+from\s+"([^"]+)"\s+as\s+([\w]+)', command)
        if load_match:
            file_path = load_match.group(1)
            table_name = load_match.group(2)
            
            self.file_paths[table_name] = file_path
            self._load_csv_file(table_name, file_path)
            return len(self.file_data.get(table_name, []))
        
        # 支持刷新已加载的文件
        refresh_match = re.match(r'refresh\s+table\s+([\w]+)', command)
        if refresh_match:
            table_name = refresh_match.group(1)
            
            if table_name in self.file_paths:
                self._load_csv_file(table_name, self.file_paths[table_name])
                return len(self.file_data.get(table_name, []))
        
        self.logger.warning(f"Unsupported command for CSV data source: {command}")
        return 0
    
    def _get_schema(self, entity: Optional[str] = None) -> Dict[str, Any]:
        """
        获取CSV数据源模式
        """
        schema = {'tables': []}
        
        tables_to_process = [entity] if entity else self.file_data.keys()
        
        for table_name in tables_to_process:
            if table_name in self.file_data:
                table_data = self.file_data[table_name]
                fields = []
                field_types = {}
                
                if table_data:
                    fields = list(table_data[0].keys())
                    # 推断字段类型
                    for field in fields:
                        field_types[field] = self._infer_field_type(field, table_data)
                
                schema['tables'].append({
                    'name': table_name,
                    'count': len(table_data),
                    'fields': fields,
                    'field_types': field_types,
                    'file_path': self.file_paths.get(table_name)
                })
        
        return schema
    
    def _evaluate_condition(self, record: Dict[str, Any], condition: str, 
                           params: Optional[Dict[str, Any]]) -> bool:
        """
        评估条件
        """
        # 简单的条件评估实现
        # 替换参数
        if params:
            for key, value in params.items():
                placeholder = f":{key}"
                if placeholder in condition:
                    if isinstance(value, str):
                        condition = condition.replace(placeholder, f"'{value}'")
                    else:
                        condition = condition.replace(placeholder, str(value))
        
        # 替换字段值
        for field, value in record.items():
            pattern = r'\b' + re.escape(field) + r'\b'
            if re.search(pattern, condition):
                if isinstance(value, str):
                    condition = re.sub(pattern, f"'{value}'", condition)
                else:
                    condition = re.sub(pattern, str(value), condition)
        
        try:
            # 简单的表达式求值
            safe_globals = {'__builtins__': {}}
            return bool(eval(condition, safe_globals))
        except:
            return False
    
    def _begin_transaction(self) -> bool:
        """
        开始事务
        CSV不支持事务，返回True表示成功
        """
        return True
    
    def _commit_transaction(self) -> bool:
        """
        提交事务
        CSV不支持事务，返回True表示成功
        """
        return True
    
    def _rollback_transaction(self) -> bool:
        """
        回滚事务
        CSV不支持事务，返回True表示成功
        """
        return True
    
    def _get_test_query(self) -> str:
        """
        获取测试查询
        """
        # 获取第一个表名
        if self.file_data:
            table_name = next(iter(self.file_data.keys()))
            return f"SELECT * FROM {table_name} LIMIT 1"
        return "SELECT 1"


class JSONDataSource(DataSource):
    """
    JSON文件数据源实现
    支持读取JSON文件作为数据源
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化JSON数据源
        
        Args:
            config: 配置信息，包含文件路径、编码等
        """
        super().__init__(DataSourceType.JSON, config)
        self.file_data = {}
        self.file_paths = {}
        self.encoding = self.config.get('encoding', 'utf-8')
        self.data_path = self.config.get('data_path', '')  # JSONPath表达式或点分隔路径
    
    def _connect(self):
        """
        连接到JSON数据源（加载文件）
        """
        import json
        import os
        
        # 处理单个文件配置
        if 'file_path' in self.config:
            table_name = self.config.get('table_name', 'data')
            file_path = self.config['file_path']
            self.file_paths[table_name] = file_path
            self._load_json_file(table_name, file_path)
        
        # 处理多个文件配置
        elif 'files' in self.config:
            for table_name, file_info in self.config['files'].items():
                if isinstance(file_info, str):
                    file_path = file_info
                else:
                    file_path = file_info.get('path')
                    
                if file_path:
                    self.file_paths[table_name] = file_path
                    self._load_json_file(table_name, file_path)
        
        return self.file_data
    
    def _load_json_file(self, table_name: str, file_path: str):
        """
        加载JSON文件数据
        """
        import json
        import os
        
        if not os.path.exists(file_path):
            self.logger.warning(f"JSON file not found: {file_path}")
            self.file_data[table_name] = []
            return
        
        try:
            with open(file_path, 'r', encoding=self.encoding) as f:
                data = json.load(f)
                
                # 根据数据路径提取数据
                if self.data_path:
                    data = self._extract_data_by_path(data, self.data_path)
                
                # 确保数据是列表格式
                if not isinstance(data, list):
                    if isinstance(data, dict):
                        # 如果是字典，尝试转换为列表
                        if all(isinstance(v, dict) for v in data.values()):
                            # 如果值都是字典，可以将键作为ID添加到每个字典中
                            data_list = []
                            for key, value in data.items():
                                value['_id'] = key
                                data_list.append(value)
                            data = data_list
                        else:
                            # 否则，将整个字典作为单个记录
                            data = [data]
                    else:
                        data = [{'value': data}]
                
                self.file_data[table_name] = data
                self.logger.info(f"Loaded JSON file {file_path} with {len(data)} records as table {table_name}")
        except Exception as e:
            self.logger.error(f"Error loading JSON file {file_path}: {str(e)}")
            self.file_data[table_name] = []
    
    def _extract_data_by_path(self, data: Any, path: str) -> Any:
        """
        根据路径提取数据
        支持简单的点分隔路径或JSONPath
        """
        current = data
        
        # 尝试使用点分隔路径
        try:
            for part in path.split('.'):
                if isinstance(current, dict):
                    current = current.get(part)
                elif isinstance(current, list) and part.isdigit():
                    index = int(part)
                    if 0 <= index < len(current):
                        current = current[index]
                    else:
                        return []
                else:
                    return []
            return current
        except:
            return data
    
    def _disconnect(self):
        """
        断开JSON数据源连接
        """
        self.file_data.clear()
    
    def _execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        执行JSON数据查询
        """
        import re
        
        query = query.lower().strip()
        
        # 匹配简单的查询格式
        select_pattern = r'select\s+([\w\*,\s]+)\s+from\s+([\w]+)(\s+where\s+(.+))?'
        select_match = re.match(select_pattern, query)
        
        if not select_match:
            self.logger.warning(f"Unsupported query format: {query}")
            return []
        
        fields_str = select_match.group(1)
        table_name = select_match.group(2)
        where_clause = select_match.group(4)  # 可能为None
        
        # 检查表是否存在
        if table_name not in self.file_data:
            self.logger.warning(f"Table not found: {table_name}")
            return []
        
        # 获取表数据
        table_data = self.file_data[table_name]
        
        # 过滤数据
        filtered_data = []
        if where_clause:
            for record in table_data:
                if isinstance(record, dict) and self._evaluate_condition(record, where_clause, params):
                    filtered_data.append(record)
        else:
            filtered_data = [r for r in table_data if isinstance(r, dict)]
        
        # 选择字段
        if fields_str == '*':
            return [dict(record) for record in filtered_data]
        else:
            fields = [f.strip() for f in fields_str.split(',')]
            result = []
            for record in filtered_data:
                filtered_record = {}
                for field in fields:
                    if field in record:
                        # 转换嵌套字段路径
                        if '.' in field:
                            value = self._get_nested_value(record, field)
                            if value is not None:
                                filtered_record[field] = value
                        else:
                            filtered_record[field] = record[field]
                result.append(filtered_record)
            return result
    
    def _get_nested_value(self, record: Dict[str, Any], nested_path: str) -> Any:
        """
        获取嵌套字段的值
        """
        parts = nested_path.split('.')
        current = record
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        
        return current
    
    def _execute_command(self, command: str, params: Optional[Dict[str, Any]] = None) -> int:
        """
        执行JSON命令
        """
        import re
        import os
        
        command = command.lower().strip()
        
        # 支持加载新的JSON文件
        load_match = re.match(r'load\s+json\s+from\s+"([^"]+)"\s+as\s+([\w]+)', command)
        if load_match:
            file_path = load_match.group(1)
            table_name = load_match.group(2)
            
            self.file_paths[table_name] = file_path
            self._load_json_file(table_name, file_path)
            return len(self.file_data.get(table_name, []))
        
        # 支持刷新已加载的文件
        refresh_match = re.match(r'refresh\s+table\s+([\w]+)', command)
        if refresh_match:
            table_name = refresh_match.group(1)
            
            if table_name in self.file_paths:
                self._load_json_file(table_name, self.file_paths[table_name])
                return len(self.file_data.get(table_name, []))
        
        self.logger.warning(f"Unsupported command for JSON data source: {command}")
        return 0
    
    def _get_schema(self, entity: Optional[str] = None) -> Dict[str, Any]:
        """
        获取JSON数据源模式
        """
        schema = {'tables': []}
        
        tables_to_process = [entity] if entity else self.file_data.keys()
        
        for table_name in tables_to_process:
            if table_name in self.file_data:
                table_data = [r for r in self.file_data[table_name] if isinstance(r, dict)]
                fields = set()
                field_types = {}
                
                # 收集所有可能的字段
                for record in table_data:
                    fields.update(record.keys())
                fields = list(fields)
                
                # 推断字段类型
                for field in fields:
                    field_types[field] = self._infer_field_type(field, table_data)
                
                schema['tables'].append({
                    'name': table_name,
                    'count': len(table_data),
                    'fields': fields,
                    'field_types': field_types,
                    'file_path': self.file_paths.get(table_name)
                })
        
        return schema
    
    def _evaluate_condition(self, record: Dict[str, Any], condition: str, 
                           params: Optional[Dict[str, Any]]) -> bool:
        """
        评估条件
        """
        import re
        
        # 替换参数
        if params:
            for key, value in params.items():
                placeholder = f":{key}"
                if placeholder in condition:
                    if isinstance(value, str):
                        condition = condition.replace(placeholder, f"'{value}'")
                    else:
                        condition = condition.replace(placeholder, str(value))
        
        # 替换字段值
        # 处理嵌套字段
        def replace_field(match):
            field_path = match.group(1)
            value = self._get_nested_value(record, field_path)
            if value is None:
                return 'None'
            elif isinstance(value, str):
                return f"'{value}'"
            else:
                return str(value)
        
        # 替换嵌套字段引用
        condition = re.sub(r'\b([\w.]+)\b', replace_field, condition)
        
        try:
            safe_globals = {'__builtins__': {}}
            return bool(eval(condition, safe_globals))
        except:
            return False
    
    def _begin_transaction(self) -> bool:
        """
        开始事务
        JSON不支持事务，返回True表示成功
        """
        return True
    
    def _commit_transaction(self) -> bool:
        """
        提交事务
        JSON不支持事务，返回True表示成功
        """
        return True
    
    def _rollback_transaction(self) -> bool:
        """
        回滚事务
        JSON不支持事务，返回True表示成功
        """
        return True
    
    def _get_test_query(self) -> str:
        """
        获取测试查询
        """
        if self.file_data:
            table_name = next(iter(self.file_data.keys()))
            return f"SELECT * FROM {table_name} LIMIT 1"
        return "SELECT 1"


class RESTAPIDataSource(DataSource):
    """
    REST API数据源实现
    支持通过HTTP请求访问REST API
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化REST API数据源
        
        Args:
            config: 配置信息，包含base_url、headers、认证信息等
        """
        super().__init__(DataSourceType.REST_API, config)
        self.base_url = self.config.get('base_url', '')
        self.headers = self.config.get('headers', {})
        self.auth = self.config.get('auth')
        self.timeout = self.config.get('timeout', 30)
        self.cache_enabled = self.config.get('cache_enabled', False)
        self.cache_ttl = self.config.get('cache_ttl', 300)  # 5分钟
        self.cache = {}
        self.endpoints = self.config.get('endpoints', {})  # 端点配置
        self.session = None  # requests会话对象
        self.endpoints = self.config.get('endpoints', {})
    
    def _connect(self):
        """
        连接到REST API（初始化）
        """
        # 检查必要的配置
        if not self.base_url:
            raise ValueError("base_url is required for REST API data source")
        
        # 添加默认User-Agent
        if 'User-Agent' not in self.headers:
            self.headers['User-Agent'] = 'Flora Data Access/1.0'
        
        # 初始化认证
        if self.auth:
            self._setup_auth()
        
        return True
    
    def _setup_auth(self):
        """
        设置认证信息
        """
        auth_type = self.auth.get('type', '').lower()
        
        if auth_type == 'bearer':
            token = self.auth.get('token')
            if token:
                self.headers['Authorization'] = f"Bearer {token}"
        elif auth_type == 'basic':
            import base64
            username = self.auth.get('username')
            password = self.auth.get('password')
            if username and password:
                auth_str = f"{username}:{password}"
                encoded = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')
                self.headers['Authorization'] = f"Basic {encoded}"
    
    def _disconnect(self):
        """
        断开连接（清理缓存）
        """
        self.cache.clear()
    
    def _execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        执行REST API查询
        
        支持的查询格式：
        - "select * from endpoint_name" - 调用指定端点
        - "get endpoint_name" - 调用指定端点
        - "get endpoint_name with {params}" - 带参数调用端点
        """
        import re
        import time
        
        query = query.lower().strip()
        
        # 解析端点名称
        endpoint_name = None
        query_params = params.copy() if params else {}
        
        # 匹配 "get endpoint_name with {params}" 格式
        with_params_match = re.match(r'get\s+([\w_]+)\s+with\s+\{([^\}]+)\}', query)
        if with_params_match:
            endpoint_name = with_params_match.group(1)
            # 解析参数
            param_str = with_params_match.group(2)
            for param in param_str.split(','):
                if '=' in param:
                    key, value = param.split('=', 1)
                    query_params[key.strip()] = value.strip()
        
        # 匹配 "get endpoint_name" 格式
        elif query.startswith('get '):
            endpoint_name = query[4:].strip()
        
        # 匹配 "select * from endpoint_name" 格式
        elif query.startswith('select '):
            match = re.match(r'select\s+.+\s+from\s+([\w_]+)', query)
            if match:
                endpoint_name = match.group(1)
        
        if not endpoint_name:
            self.logger.warning(f"Invalid query format: {query}")
            return []
        
        # 构建请求URL
        url = self._build_url(endpoint_name, query_params)
        cache_key = self._get_cache_key(url, query_params)
        
        # 检查缓存
        if self.cache_enabled and cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                self.logger.debug(f"Using cached data for {url}")
                return self._format_response(cached_data, endpoint_name)
        
        # 发送请求
        response_data = self._send_request(url, query_params)
        
        # 更新缓存
        if self.cache_enabled:
            self.cache[cache_key] = (response_data, time.time())
        
        return self._format_response(response_data, endpoint_name)
    
    def _execute_command(self, command: str, params: Optional[Dict[str, Any]] = None) -> int:
        """
        执行REST API命令
        支持POST、PUT、DELETE等操作
        """
        import re
        
        command = command.lower().strip()
        
        # 匹配 "post to endpoint_name" 格式
        post_match = re.match(r'post\s+to\s+([\w_]+)', command)
        if post_match:
            endpoint_name = post_match.group(1)
            url = self._build_url(endpoint_name)
            response = self._send_request(url, params, method='POST')
            return 1 if response else 0
        
        # 匹配 "put to endpoint_name" 格式
        put_match = re.match(r'put\s+to\s+([\w_]+)', command)
        if put_match:
            endpoint_name = put_match.group(1)
            url = self._build_url(endpoint_name)
            response = self._send_request(url, params, method='PUT')
            return 1 if response else 0
        
        # 匹配 "delete from endpoint_name" 格式
        delete_match = re.match(r'delete\s+from\s+([\w_]+)', command)
        if delete_match:
            endpoint_name = delete_match.group(1)
            url = self._build_url(endpoint_name, params)
            response = self._send_request(url, None, method='DELETE')
            return 1 if response else 0
        
        # 匹配 "clear cache" 格式
        if command == 'clear cache':
            self.cache.clear()
            return 1
        
        self.logger.warning(f"Unsupported command for REST API: {command}")
        return 0
    
    def _build_url(self, endpoint_name: str, params: Optional[Dict[str, Any]] = None) -> str:
        """
        构建请求URL
        """
        # 检查是否在endpoints配置中定义了此端点
        endpoint_config = self.endpoints.get(endpoint_name, {})
        path = endpoint_config.get('path', endpoint_name)
        
        # 构建URL
        url = self.base_url.rstrip('/') + '/' + path.lstrip('/')
        
        # 替换URL中的路径参数
        if params:
            for key, value in params.items():
                placeholder = f"{{{key}}}"
                if placeholder in url:
                    url = url.replace(placeholder, str(value))
                    # 从查询参数中移除已使用的路径参数
                    del params[key]
        
        return url
    
    def _send_request(self, url: str, params: Optional[Dict[str, Any]] = None,
                     method: str = 'GET') -> Dict[str, Any]:
        """
        发送HTTP请求
        """
        import requests
        
        # 对于GET请求，检查缓存
        if self.cache_enabled and method.upper() == 'GET':
            cache_key = self._get_cache_key(url, params)
            
            # 先清理过期缓存
            self._clean_cache()
            
            # 检查是否存在有效的缓存
            if cache_key in self.cache:
                cached_data, timestamp = self.cache[cache_key]
                if time.time() - timestamp < self.cache_ttl:
                    self.logger.debug(f"Using cached data for {url}")
                    return cached_data
        
        try:
            self.logger.debug(f"Sending {method} request to {url}")
            
            kwargs = {
                'headers': self.headers.copy(),
                'timeout': self.timeout
            }
            
            # 根据方法设置参数
            if method == 'GET':
                kwargs['params'] = params
            else:
                # 对于其他方法，使用JSON数据
                kwargs['json'] = params
                # 如果没有设置Content-Type，默认设置为application/json
                if 'Content-Type' not in kwargs['headers']:
                    kwargs['headers']['Content-Type'] = 'application/json'
            
            # 发送请求
            response = requests.request(method, url, **kwargs)
            
            # 检查响应状态
            response.raise_for_status()
            
            # 解析响应
            data = response.json()
            
            # 对于GET请求，更新缓存
            if self.cache_enabled and method.upper() == 'GET':
                cache_key = self._get_cache_key(url, params)
                self.cache[cache_key] = (data, time.time())
            
            return data
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {str(e)}")
            raise
    
    def _format_response(self, data: Any, endpoint_name: str) -> List[Dict[str, Any]]:
        """
        格式化API响应为统一格式
        """
        # 检查是否有自定义的响应格式化配置
        endpoint_config = self.endpoints.get(endpoint_name, {})
        data_path = endpoint_config.get('data_path')
        
        # 如果指定了数据路径，提取数据
        if data_path:
            # 使用简单的点分隔路径提取
            current = data
            for part in data_path.split('.'):
                if isinstance(current, dict) and part in current:
                    current = current[part]
                elif isinstance(current, list) and part.isdigit():
                    index = int(part)
                    if 0 <= index < len(current):
                        current = current[index]
                    else:
                        return []
                else:
                    return []
            data = current
        
        # 确保返回列表格式
        if isinstance(data, list):
            # 确保列表中的每个元素都是字典
            return [item if isinstance(item, dict) else {'value': item} for item in data]
        elif isinstance(data, dict):
            return [data]
        else:
            return [{'value': data}]
    
    def _get_cache_key(self, url: str, params: Optional[Dict[str, Any]] = None) -> str:
        """
        生成缓存键
        """
        key = url
        if params:
            # 排序参数以确保相同参数生成相同的键
            sorted_params = sorted(params.items())
            params_str = '&'.join([f"{k}={v}" for k, v in sorted_params])
            key += '?' + params_str
        return key
    
    def _get_schema(self, entity: Optional[str] = None) -> Dict[str, Any]:
        """
        获取REST API数据源模式
        """
        schema = {'endpoints': []}
        
        endpoints_to_process = [entity] if entity else self.endpoints.keys()
        
        for endpoint_name in endpoints_to_process:
            if endpoint_name in self.endpoints:
                endpoint_config = self.endpoints[endpoint_name]
                
                schema['endpoints'].append({
                    'name': endpoint_name,
                    'path': endpoint_config.get('path', endpoint_name),
                    'method': endpoint_config.get('method', 'GET'),
                    'description': endpoint_config.get('description', ''),
                    'data_path': endpoint_config.get('data_path', '')
                })
        
        # 如果没有配置endpoints，尝试获取一个示例响应来推断模式
        if not schema['endpoints'] and entity:
            try:
                # 尝试调用端点获取示例数据
                sample_data = self._execute_query(f"get {entity} limit 1")
                if sample_data:
                    fields = list(sample_data[0].keys())
                    schema['endpoints'].append({
                        'name': entity,
                        'path': entity,
                        'method': 'GET',
                        'fields': fields,
                        'sample_count': len(sample_data)
                    })
            except:
                pass
        
        return schema
    
    def _begin_transaction(self) -> bool:
        """
        开始事务
        REST API不支持事务，返回True表示成功
        """
        return True
    
    def _commit_transaction(self) -> bool:
        """
        提交事务
        REST API不支持事务，返回True表示成功
        """
        return True
    
    def _rollback_transaction(self) -> bool:
        """
        回滚事务
        REST API不支持事务，返回True表示成功
        """
        return True
    
    def _get_test_query(self) -> str:
        """
        获取测试查询
        """
        # 尝试测试第一个配置的端点
        if self.endpoints:
            endpoint_name = next(iter(self.endpoints.keys()))
            return f"get {endpoint_name} limit 1"
        # 或者测试基础URL的健康检查端点
        return "get health"


class DataSourceFactory:
    """
    数据源工厂类
    负责创建和管理不同类型的数据源实例
    """
    
    # 数据源类型映射表
    _data_source_types = {
        DataSourceType.MEMORY: MemoryDataSource,
        DataSourceType.SQLITE: SQLiteDataSource,
        DataSourceType.CSV: CSVDataSource,
        DataSourceType.JSON: JSONDataSource,
        DataSourceType.REST_API: RESTAPIDataSource
    }
    
    # 数据源实例缓存（私有属性）
    _instances = {}
    
    # 线程锁，用于保证线程安全（私有属性）
    _lock = threading.RLock()
    
    @classmethod
    def register_data_source(cls, source_type: Union[DataSourceType, str], data_source_class: type) -> None:
        """
        注册新的数据源类型
        
        Args:
            source_type: 数据源类型（枚举或字符串）
            data_source_class: 数据源实现类
        """
        if isinstance(source_type, str):
            source_type = DataSourceType(source_type.lower())
        
        with cls._lock:
            cls._data_source_types[source_type] = data_source_class
    
    @classmethod
    def create_data_source(cls, source_type: Union[DataSourceType, str], config: Dict[str, Any], 
                          instance_id: Optional[str] = None) -> DataSource:
        """
        创建数据源实例
        
        Args:
            source_type: 数据源类型（枚举或字符串）
            config: 数据源配置
            instance_id: 实例ID，如果提供则使用单例模式
        
        Returns:
            DataSource: 创建的数据源实例
        
        Raises:
            ValueError: 如果数据源类型不支持
        """
        if isinstance(source_type, str):
            source_type = DataSourceType(source_type.lower())
        
        # 如果指定了实例ID，检查缓存
        if instance_id:
            with cls._lock:
                if instance_id in cls._instances:
                    return cls._instances[instance_id]
        
        # 检查是否支持该数据源类型
        if source_type not in cls._data_source_types:
            raise ValueError(f"Unsupported data source type: {source_type.value}")
        
        try:
            # 创建数据源实例
            data_source_class = cls._data_source_types[source_type]
            data_source = data_source_class(config)
            
            # 初始化数据源
            if not data_source.initialize():
                raise RuntimeError(f"Failed to initialize {source_type.value} data source")
            
            # 缓存实例（如果指定了实例ID）
            if instance_id:
                with cls._lock:
                    cls._instances[instance_id] = data_source
            
            return data_source
        except Exception as e:
            # 捕获所有异常，确保方法返回一个有效的数据源对象
            # 如果初始化失败，返回一个失败的数据源对象（标记为未连接）
            # 注意：这里我们不直接抛出异常，而是通过数据源的is_connected标志来表示失败状态
            try:
                data_source = data_source_class(config)
                data_source.is_connected = False
                data_source.logger.error(f"Failed to create data source: {str(e)}", exc_info=True)
                return data_source
            except:
                # 如果连创建失败对象都不行，就返回基类的实例
                base_data_source = DataSource(source_type, config)
                base_data_source.is_connected = False
                base_data_source.logger.error(f"Failed to create data source: {str(e)}", exc_info=True)
                return base_data_source
    
    @classmethod
    def get_data_source(cls, instance_id: str) -> Optional[DataSource]:
        """
        获取已缓存的数据源实例
        
        Args:
            instance_id: 实例ID
        
        Returns:
            Optional[DataSource]: 数据源实例，如果不存在则返回None
        """
        with cls._lock:
            return cls._instances.get(instance_id)
    
    @classmethod
    def release_data_source(cls, instance_id: str) -> bool:
        """
        释放数据源实例
        
        Args:
            instance_id: 实例ID
        
        Returns:
            bool: 是否成功释放
        """
        with cls._lock:
            if instance_id in cls._instances:
                data_source = cls._instances.pop(instance_id)
                data_source.close()
                return True
            return False
    
    @classmethod
    def release_all_data_sources(cls) -> None:
        """
        释放所有数据源实例
        """
        with cls._lock:
            for instance_id in list(cls._instances.keys()):
                cls.release_data_source(instance_id)
    
    @classmethod
    def get_available_types(cls) -> List[str]:
        """
        获取所有可用的数据源类型
        
        Returns:
            List[str]: 可用的数据源类型列表
        """
        return [source_type.value for source_type in cls._data_source_types.keys()]
    
    @classmethod
    def test_data_source(cls, source_type: Union[DataSourceType, str], config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        测试数据源连接
        
        Args:
            source_type: 数据源类型（枚举或字符串）
            config: 数据源配置
        
        Returns:
            Tuple[bool, str]: (是否连接成功, 错误信息或成功消息)
        """
        try:
            data_source = cls.create_data_source(source_type, config)
            if data_source.test_connection():
                return True, "Connection successful"
            else:
                return False, "Connection test failed"
        except Exception as e:
            return False, str(e)
        finally:
            # 清理测试实例
            data_source.close()