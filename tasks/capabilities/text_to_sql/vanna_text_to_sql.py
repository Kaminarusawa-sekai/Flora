"""Vanna AI TextToSQL implementation"""
import asyncio
from typing import Optional, List, Dict, Any
import pandas as pd


from .text_to_sql import ITextToSQLCapability
import logging

logger = logging.getLogger(__name__)
from external.repositories.sql_metadata_repo import DatabaseMetadataRepositoryFactory
from .utils import is_safe_sql, should_learn

from .vanna.vanna_factory import VannaFactory
from config import VANNA_TYPE


# 修改后的 VannaTextToSQL 类，支持多种数据库类型
class VannaTextToSQL(ITextToSQLCapability):
    """
    负责 Text-to-SQL 的核心逻辑，使用 Repository 模式解耦数据库访问
    """

    def __init__(self, metadata_repo=None, connection_pool=None, db_type="mysql"):
        self.vn = None
        self.business_id = None
        self.database = None
        self.table_name = None
        self.db_type = db_type
        self._initialized = False
        # 支持依赖注入，便于测试
        self.connection_pool = connection_pool
        self.metadata_repo = metadata_repo or DatabaseMetadataRepositoryFactory.create_repository(
            db_type, connection_pool=connection_pool
        )

    def get_capability_type(self) -> str:
        return "text_to_sql"

    def initialize(self, config: Dict[str, Any]) -> None:
        """
        初始化方法，符合 ITextToSQL 接口要求
        
        Expected config format:
        {
            "agent_id": "xxx",
            "agent_meta": {
                "database": "db_name.table_name",
                "database_type": "mysql"  # 可选，默认为 mysql
            }
        }
        """
        agent_id = config.get("agent_id")
        agent_meta = config.get("agent_meta", {})
        db_type = agent_meta.get("database_type", "mysql")
        self.db_type = db_type

        if not agent_id:
            logger.info("[VannaTextToSQL] Deferred init: missing agent_id in config.")
            self._initialized = False
            return

        data_source = agent_meta.get("database")

        if not data_source or "." not in data_source:
            logger.info(f"[VannaTextToSQL] Deferred init for agent {agent_id}: missing database metadata.")
            self._initialized = False
            return

        self.business_id = agent_id
        self.database = data_source.split(".")[0]
        self.table_name = data_source.split(".")[1]

        # 如果数据库类型发生变化，重新创建仓库
        if hasattr(self.metadata_repo, 'get_database_type') and \
           self.metadata_repo.get_database_type() != db_type:
            self.metadata_repo = DatabaseMetadataRepositoryFactory.create_repository(
                db_type, connection_pool=self.connection_pool
            )

        # 1. 通过 Repository 获取 DDL
        ddl = self.metadata_repo.get_table_ddl(self.database, self.table_name)

        # 2. 修正 DDL 中的表名以包含库名（兼容性处理）
        target_table = f"`{self.database}`.`{self.table_name}`"
        if target_table not in ddl and f'"{self.database}"."{self.table_name}"' not in ddl:
            # 根据数据库类型使用不同的表名格式
            if db_type == "mysql":
                ddl = ddl.replace(f"`{self.table_name}`", target_table)
            elif db_type in ["postgresql", "oracle"]:
                ddl = ddl.replace(f'"{self.table_name}"', f'"{self.database}"."{self.table_name}"')
            # 可以根据需要添加其他数据库类型的处理

        # 3. 初始化 Vanna
        try:
            self.vn  = VannaFactory.create(
                vanna_type=VANNA_TYPE,
                business_id=self.business_id,
            )
        except Exception as e:
            logger.error(f"[VannaTextToSQL] Failed to create Vanna: {e}, fallback to qwen-chroma")
            self.vn  = VannaFactory.create(
                    vanna_type="qwen-chroma",
                    business_id=self.business_id,
                )
        self.vn.train(ddl=ddl)
        self._initialized = True
        logger.info(f"[VannaTextToSQL] Initialized for {self.business_id} with {db_type} database")

    def shutdown(self) -> None:
        """释放资源，重置状态"""
        self.vn = None
        self.business_id = None
        self.database = None
        self.table_name = None
        self._initialized = False
        logger.info("[VannaTextToSQL] Shutdown completed")

    def execute_query(self, user_query: str, context: dict = None) -> dict:
        if not self._initialized:
            raise RuntimeError("VannaTextToSQL not initialized")

        enhanced_question = self._enrich_query(user_query, context)
        sql = self.vn.generate_sql(enhanced_question)

        if not is_safe_sql(sql):
            logger.warning(f"[SQL] Unsafe SQL blocked: {sql}")
            raise ValueError("Generated SQL is deemed unsafe")

        # 执行 SQL（这部分仍需直接查业务库，不属于元数据，可保留）
        conn = self._get_database_connection()
        try:
            df = pd.read_sql(sql, conn)
            logger.info(f"[SQL] Executed: {sql} | Rows: {len(df)}")
        finally:
            conn.close()

        if should_learn(df, sql):
            self.vn.train(question=enhanced_question, sql=sql)
            logger.info(f"[LEARN] Auto-trained on query")

        return {
            "result": df.to_dict(orient="records"),
            "sql": sql,
            "rows": len(df)
        }

    def _get_database_connection(self):
        """
        根据数据库类型获取连接
        """
        if self.connection_pool:
            return self.connection_pool.get_connection()
        # 回退：动态创建连接池并获取连接
        from external.database.connection_pool import ConnectionPoolFactory
        pool = ConnectionPoolFactory.create_pool(self.db_type)
        return pool.get_connection()

    def _enrich_query(self, query: str, context: dict) -> str:
        if not context:
            return query
        return query