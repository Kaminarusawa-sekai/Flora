"""
数据访问能力模块
提供统一的数据源访问接口和实现
"""

from .data_source import (
    DataSource,
    DataSourceType,
    DataSourceFactory,
    MemoryDataSource,
    SQLiteDataSource,
    CSVDataSource,
    JSONDataSource,
    RESTAPIDataSource
)

# 暂时注释掉这些导入，因为这些模块还不存在
# from .data_accessor import DataAccessor
# from .query_builder import QueryBuilder
# from .data_mapper import DataMapper

__all__ = [
    'DataSource', 
    'DataSourceType',
    # 'DataAccessor',
    # 'QueryBuilder',
    # 'DataMapper',
    'DataSourceFactory',
    'MemoryDataSource',
    'SQLiteDataSource',
    'CSVDataSource',
    'JSONDataSource',
    'RESTAPIDataSource'
]

__version__ = '1.0.0'
__description__ = '统一数据访问能力模块'
