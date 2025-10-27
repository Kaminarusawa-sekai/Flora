# actor.py
import thespian.actors as actors
from agent.io.vanna_qwen_chroma import QwenVanna
from agent.io.utils import should_learn
from agent.io.mysql_pool import mysql_pool
import pandas as pd
from agent.message import DataQueryRequest, DataQueryResponse, MemoryResponse,InitDataQueryActor
from agent.agent_registry import AgentRegistry
from agent.memory.memory_interface import LoadMemoryForAgent
from agent.memory.memory_actor import MemoryActor

from pymysql.cursors import Cursor  # 普通元组游标

import logging

logger = logging.getLogger(__name__)

def get_mysql_ddl(database: str, table: str) -> str:
    conn = mysql_pool.get_connection()
    try:
        # ✅ 显式指定使用普通 Cursor（返回元组）
        cursor = conn.cursor(Cursor)
        cursor.execute(f"SHOW CREATE TABLE `{database}`.`{table}`")
        result = cursor.fetchone()
        if result is None:
            raise ValueError(f"Table `{database}.{table}` not found")
        ddl = result[1]  # ✅ 现在 result 是元组 (table_name, create_ddl)
        return ddl
    finally:
        cursor.close()
        conn.close()

class DataActor(actors.Actor):
    def __init__(self):
        super().__init__()
        self.vn = None
        self.agent_id = None
        self.data_scope = None
        self._initialized = False
        self._memory = None

        self.business_id = None
        self.database = None
        self.table_name = None
        logger.info("[DataActor] Created (not yet initialized)")

    def receiveMessage(self, msg, sender):
        if isinstance(msg, DataQueryRequest):
            self._handle_query_request(msg, sender)
        elif isinstance(msg, MemoryResponse):
            self._memory = msg.value if msg.value else {}
            self._process_queued_requests()
        elif isinstance(msg, InitDataQueryActor):
            # ✅ 触发完整初始化
            try:
                self._do_full_initialization(msg.agent_id)
                # 初始化成功后再加载 memory
                self._memory_actor = self.createActor(MemoryActor)
                self.send(self._memory_actor, LoadMemoryForAgent(msg.agent_id))
                # 可选：通知 sender 初始化成功
                # self.send(sender, {"status": "initialized", "agent_id": msg.agent_id})
            except Exception as e:
                logger.exception(f"Failed to initialize DataActor for agent_id={msg.agent_id}")
                self.send(sender, {"error": f"Initialization failed: {str(e)}"})
        else:
            logger.warning(f"DataActor received unknown message: {type(msg)}")

    def _do_full_initialization(self, agent_id: str):
        """执行完整的业务初始化：加载元数据、设置上下文、初始化 Vanna"""
        registry = AgentRegistry.get_instance()
        meta = registry.get_agent_meta(agent_id)
        if not meta:
            raise ValueError(f"Agent {agent_id} not found in registry")

        if "data_query" not in meta.get("capabilities", []):
            logger.warning(f"Agent {agent_id} is not a data actor (missing 'data_query' capability)")

        self.agent_id = agent_id
        self.data_scope = meta.get("datascope", {})

        self.business_id = agent_id
        self.data_source =  meta.get("database")
        self.database = self.data_source.split(".")[0]
        self.table_name = self.data_source.split(".")[1]

        if not all([self.business_id, self.database, self.table_name]):
            raise ValueError(f"Incomplete data_scope: {self.data_scope}")

        # 初始化 Vanna
        ddl = get_mysql_ddl(self.database, self.table_name)
        if f"`{self.database}`.`{self.table_name}`" not in ddl:
            ddl = ddl.replace(f"`{self.table_name}`", f"`{self.database}`.`{self.table_name}`")
        
        self.vn = QwenVanna(business_id=self.business_id)
        self.vn.train(ddl=ddl)
        self._initialized = True
        logger.info(f"[DataActor] Fully initialized for agent_id={agent_id}, biz={self.business_id}")

    def _handle_query_request(self, req: DataQueryRequest, sender):
        if not self._initialized:
            error_msg = "DataActor not initialized. Send InitDataQueryActor first."
            logger.error(error_msg)
            self.send(sender, DataQueryResponse(
                request_id=req.request_id,
                error=error_msg
            ))
            return

        try:
            # 使用记忆增强原始查询（如果 memory 存在）
            enhanced_question = (
                self._build_query_with_memory(req.query, self._memory)
                if self._memory is not None
                else req.query
            )

            # 生成 SQL
            sql = self.vn.generate_sql(enhanced_question)

            # 安全审核
            if not self._is_safe_sql(sql):
                logger.warning("[SQL] Unsafe SQL generated")
                raise ValueError("Generated SQL is not safe")

            # 执行 SQL
            conn = mysql_pool.get_connection(self.database)
            try:
                df = pd.read_sql(sql, conn)
                logger.info(f"[SQL] Executed: {sql} | Rows: {len(df)}")
            finally:
                conn.close()

            # ✅ 审核后自动学习（可选）
            if should_learn(df, sql):
                self.vn.train(question=enhanced_question, sql=sql)
                self.log_successful_query(enhanced_question, sql)

            # 发送成功响应
            self.send(sender, DataQueryResponse(
                request_id=req.request_id,
                result=df.to_dict(orient="records"),
                metadata={"sql": sql}
            ))

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            logger.exception("🔥 CRITICAL ERROR in DataActor query handling")
            self.send(sender, DataQueryResponse(
                request_id=req.request_id,
                error=str(e),
                metadata={"detail": error_detail}
            ))

    def _build_query_with_memory(self, query: str, memory: dict) -> str:
        # TODO: 根据 memory 增强 query，例如拼接上下文
        # 示例：return f"Context: {memory.get('last_query', '')}. Current: {query}"
        return query

    def _is_safe_sql(self, sql: str) -> bool:
        return is_safe_sql(sql)

    def log_successful_query(self, question: str, sql: str):
        logger.info(f"[LEARN] biz={self.business_id} | Q: {question} | SQL: {sql}")

    def _process_queued_requests(self):
        # TODO: 如果有排队的查询请求，可以在这里处理
        pass