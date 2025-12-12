# agent/repositories/mysql_metadata_repo.py

import logging
from pymysql.cursors import Cursor
from tasks.external.database.connection_pool import ConnectionPoolFactory, BaseConnectionPool
from typing import Dict, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)



class SQLMetadataRepository(ABC):
    """
    通用SQL数据库元数据仓库抽象基类
    """
    
    @abstractmethod
    def get_table_ddl(self, database: str, table: str) -> str:
        """
        获取指定表的 DDL（数据定义语言）语句
        """
        pass
    
    @abstractmethod
    def get_database_type(self) -> str:
        """
        返回数据库类型标识
        """
        pass


class MySQLMetadataRepository(SQLMetadataRepository):
    """
    负责从 MySQL 获取元数据信息（如 DDL）
    """

    def __init__(self, connection_pool:BaseConnectionPool=None):

        self.connection_pool = connection_pool or ConnectionPoolFactory.create_pool('mysql')

    def get_database_type(self) -> str:
        return "mysql"

    def get_table_ddl(self, database: str, table: str) -> str:
        """
        获取指定表的 CREATE TABLE 语句（DDL）
        """
        if not database or not table:
            raise ValueError("Database and table must be specified")

        # 使用连接池获取连接
        conn = self.connection_pool.get_connection()  # 注意：这里不需要指定 db，因为要跨库查
        try:
            cursor = conn.cursor(Cursor)
            cursor.execute(f"SHOW CREATE TABLE `{database}`.`{table}`")
            result = cursor.fetchone()
            if result is None:
                raise ValueError(f"Table `{database}.{table}` not found in MySQL")
            return result[1]  # 第二列是 DDL
        except Exception as e:
            logger.error(f"Failed to fetch DDL for {database}.{table}: {e}")
            raise
        finally:
            cursor.close()
            conn.close()


class PostgreSQLMetadataRepository(SQLMetadataRepository):
    """
    负责从 PostgreSQL 获取元数据信息（如 DDL）
    """

    def __init__(self, connection_pool:BaseConnectionPool=None):
        self.connection_pool = connection_pool or ConnectionPoolFactory.create_pool('postgresql')

    def get_database_type(self) -> str:
        return "postgresql"

    def get_table_ddl(self, database: str, table: str) -> str:
        """
        获取指定表的 CREATE TABLE 语句（DDL）
        """
        if not database or not table:
            raise ValueError("Database and table must be specified")

        # 使用连接池获取连接
        conn = self.connection_pool.get_connection()
        try:
            with conn.cursor() as cursor:
                # 查询表的 DDL
                cursor.execute("""
                    SELECT 
                        'CREATE TABLE "' || schemaname || '"."' || tablename || '" (' ||
                        string_agg(
                            '"' || column_name || '" ' || 
                            data_type || 
                            CASE WHEN is_nullable = 'NO' THEN ' NOT NULL' ELSE '' END,
                            ', '
                        ) || ');' as ddl
                    FROM (
                        SELECT table_schema as schemaname, table_name as tablename, 
                               column_name, data_type, is_nullable
                        FROM information_schema.columns 
                        WHERE table_schema = %s AND table_name = %s
                        ORDER BY ordinal_position
                    ) t
                    GROUP BY schemaname, tablename;
                """, (database, table))
                
                result = cursor.fetchone()
                if result is None:
                    raise ValueError(f"Table {database}.{table} not found in PostgreSQL")
                return result[0]
        except Exception as e:
            logger.error(f"Failed to fetch DDL for {database}.{table}: {e}")
            raise
        finally:
            conn.close()


class SQLServerMetadataRepository(SQLMetadataRepository):
    """
    负责从 SQL Server 获取元数据信息（如 DDL）
    """

    def __init__(self, connection_pool:BaseConnectionPool=None):
        self.connection_pool = connection_pool or ConnectionPoolFactory.create_pool('sqlserver')

    def get_database_type(self) -> str:
        return "sqlserver"

    def get_table_ddl(self, database: str, table: str) -> str:
        """
        获取指定表的 CREATE TABLE 语句（DDL）
        """
        if not database or not table:
            raise ValueError("Database and table must be specified")

        # 使用连接池获取连接
        conn = self.connection_pool.get_connection()
        try:
            with conn.cursor() as cursor:
                # 查询表的 DDL
                cursor.execute("""
                    SELECT 
                        'CREATE TABLE [' + s.name + '].[' + t.name + '] (' +
                        STUFF((
                            SELECT ', [' + c.name + '] ' + 
                                   UPPER(tp.name) +
                                   CASE 
                                       WHEN tp.name IN ('varchar', 'nvarchar', 'char', 'nchar') 
                                       THEN '(' + CASE WHEN c.max_length = -1 THEN 'MAX' 
                                                      ELSE CAST(c.max_length AS VARCHAR(10)) END + ')'
                                       WHEN tp.name IN ('decimal', 'numeric') 
                                       THEN '(' + CAST(c.precision AS VARCHAR(10)) + ',' + 
                                            CAST(c.scale AS VARCHAR(10)) + ')'
                                       ELSE ''
                                   END +
                                   CASE WHEN c.is_nullable = 1 THEN '' ELSE ' NOT NULL' END
                            FROM sys.columns c
                            JOIN sys.types tp ON c.user_type_id = tp.user_type_id
                            WHERE c.object_id = t.object_id
                            ORDER BY c.column_id
                            FOR XML PATH('')
                        ), 1, 2, '') + ');' AS ddl
                    FROM sys.tables t
                    JOIN sys.schemas s ON t.schema_id = s.schema_id
                    WHERE s.name = ? AND t.name = ?
                """, (database, table))
                
                result = cursor.fetchone()
                if result is None:
                    raise ValueError(f"Table {database}.{table} not found in SQL Server")
                return result[0]
        except Exception as e:
            logger.error(f"Failed to fetch DDL for {database}.{table}: {e}")
            raise
        finally:
            conn.close()


class OracleMetadataRepository(SQLMetadataRepository):
    """
    负责从 Oracle 获取元数据信息（如 DDL）
    """

    def __init__(self, connection_pool:BaseConnectionPool=None):
        self.connection_pool = connection_pool or ConnectionPoolFactory.create_pool('oracle')

    def get_database_type(self) -> str:
        return "oracle"

    def get_table_ddl(self, database: str, table: str) -> str:
        """
        获取指定表的 CREATE TABLE 语句（DDL）
        """
        if not database or not table:
            raise ValueError("Database and table must be specified")

        # 使用连接池获取连接
        conn = self.connection_pool.get_connection()
        try:
            with conn.cursor() as cursor:
                # 查询表的 DDL
                cursor.execute("""
                    SELECT 'CREATE TABLE "' || owner || '"."' || table_name || '" (' ||
                           LISTAGG(
                               '"' || column_name || '" ' || 
                               data_type ||
                               CASE 
                                   WHEN data_type IN ('VARCHAR2', 'NVARCHAR2', 'CHAR', 'NCHAR') 
                                   THEN '(' || data_length || ')'
                                   WHEN data_type IN ('NUMBER') 
                                   THEN CASE 
                                           WHEN data_precision IS NOT NULL AND data_scale IS NOT NULL 
                                           THEN '(' || data_precision || ',' || data_scale || ')'
                                           WHEN data_precision IS NOT NULL 
                                           THEN '(' || data_precision || ')'
                                           ELSE ''
                                       END
                                   ELSE ''
                               END ||
                               CASE WHEN nullable = 'N' THEN ' NOT NULL' ELSE '' END,
                               ', '
                           ) WITHIN GROUP (ORDER BY column_id) || ');' as ddl
                    FROM all_tab_columns
                    WHERE owner = UPPER(:1) AND table_name = UPPER(:2)
                    GROUP BY owner, table_name
                """, (database, table))
                
                result = cursor.fetchone()
                if result is None:
                    raise ValueError(f"Table {database}.{table} not found in Oracle")
                return result[0]
        except Exception as e:
            logger.error(f"Failed to fetch DDL for {database}.{table}: {e}")
            raise
        finally:
            conn.close()


class DatabaseMetadataRepositoryFactory:
    """
    数据库元数据仓库工厂类，根据数据库类型创建相应的仓库实例
    """
    
    @staticmethod
    def create_repository(db_type: str, connection_pool=None, **kwargs) -> SQLMetadataRepository:
        """
        根据数据库类型创建相应的元数据仓库实例
        
        Args:
            db_type: 数据库类型 ('mysql', 'postgresql', 'sqlserver', 'oracle' 等)
            connection_pool: 连接池实例
            **kwargs: 传递给仓库构造函数的额外参数
            
        Returns:
            SQLMetadataRepository 实例
        """
        db_type = db_type.lower()
        
        if db_type == 'mysql':
            return MySQLMetadataRepository(connection_pool=connection_pool, **kwargs)
        elif db_type == 'postgresql':
            return PostgreSQLMetadataRepository(connection_pool=connection_pool, **kwargs)
        elif db_type == 'sqlserver':
            return SQLServerMetadataRepository(connection_pool=connection_pool, **kwargs)
        elif db_type == 'oracle':
            return OracleMetadataRepository(connection_pool=connection_pool, **kwargs)
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
