"""业务数据管理模块"""

from .data_interface import BusinessDataInterface
from .mysql_business import MySQLBusinessData

__all__ = ['BusinessDataInterface', 'MySQLBusinessData']
