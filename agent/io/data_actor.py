# actor.py
import thespian.actors as actors
from vanna_qwen_chroma import QwenVanna
from utils import should_learn
from mysql_pool import mysql_pool
import pandas as pd
from agent.message import DataQueryRequest, DataQueryResponse, MemoryResponse

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

        self.database = None
        self.table_name = None
        print("[DataActor] Initialized")

    def receiveMessage(self, msg, sender):
        if isinstance(msg, DataQueryRequest):
            self._handle_query_request(msg, sender)
        elif isinstance(msg, MemoryResponse):
            self._memory = msg.value if msg.value else {}
            self._process_queued_requests()

        # 在 DataQueryActor.receiveMessage 中增加：
        elif isinstance(msg, InitDataQueryActor):
            self._agent_id = msg.agent_id
            self._memory_actor = self.createActor(MemoryActor)
            self.send(self._memory_actor, LoadMemoryForAgent(self._agent_id))
        else:
            # 可能是初始化消息（见下一步）
            pass
    def _handle_init(self, msg, sender):
        agent_id = msg["agent_id"]
        registry = AgentRegistry.get_instance()  # 单例

        meta = registry.get_agent_meta(agent_id)
        if not meta:
            logger.error(f"DataActor init failed: agent_id={agent_id} not found in registry")
            self.send(sender, {"error": "Agent metadata not found"})
            return

        # 验证这是一个 data actor
        if "data_query" not in meta.get("capabilities", []):
            logger.warning(f"Agent {agent_id} is not a data actor (missing 'data_query' capability)")

        self.agent_id = agent_id
        self.data_scope = meta.get("data_scope", {})

        # 从 data_scope 中提取业务上下文
        self.business_id = self.data_scope.get("business_id")
        self.database = self.data_scope.get("database")
        self.table_name = self.data_scope.get("table_name")

        if not all([self.business_id, self.database, self.table_name]):
            logger.error(f"Missing required fields in data_scope: {self.data_scope}")
            self.send(sender, {"error": "Incomplete data_scope"})
            return

        # 初始化 Vanna
        try:
            ddl = get_mysql_ddl(self.database, self.table_name)
            if f"`{self.database}`.`{self.table_name}`" not in ddl:
                ddl = ddl.replace(f"`{self.table_name}`", f"`{self.database}`.`{self.table_name}`")
            self.vn = QwenVanna(business_id=self.business_id)
            self.vn.train(ddl=ddl)
            self._initialized = True
            logger.info(f"[DataActor] Initialized for agent_id={agent_id}, biz={self.business_id}")
            self.send(sender, {"status": "initialized", "agent_id": agent_id})
        except Exception as e:
            logger.exception("Failed to initialize DataActor")
            self.send(sender, {"error": str(e)})  
    def _handle_query_request(self, req: DataQueryRequest, sender):
        try:
            # 确保组件已初始化（如 vn、数据库连接池等）
            self._ensure_initialized()

            # 使用记忆增强原始查询（如果 memory 存在）
            if self._memory is not None:
                enhanced_question = self._build_query_with_memory(req.query, self._memory)
            else:
                enhanced_question = req.query

            # 生成 SQL
            sql = self.vn.generate_sql(enhanced_question)

            # 安全审核
            if not self._is_safe_sql(sql):
                print("[SQL] SQL is not safe")
                raise ValueError("Generated SQL is not safe")

            # 执行 SQL
            conn = mysql_pool.get_connection(self.database)
            try:
                df = pd.read_sql(sql, conn)
                print(f"[SQL] {sql} | Rows: {len(df)}")
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
            print("🔥 CRITICAL ERROR:", error_detail)
            self.send(sender, DataQueryResponse(
                request_id=req.request_id,
                error=str(e),
                metadata={"detail": error_detail}
            ))
    def _ensure_initialized(self, msg):
        if self.vn is None:
            self.business_id = msg["business_id"]
            self.database = msg["database"]
            self.table_name = msg["table_name"]

            ddl = get_mysql_ddl(self.database, self.table_name)
            self.vn = QwenVanna(business_id=self.business_id)
            if f"`{self.database}`.`{self.table_name}`" not in ddl:
                ddl = ddl.replace(f"`{self.table_name}`", f"`{self.database}`.`{self.table_name}`")
            self.vn.train(ddl=ddl)  # 这会存入 Chroma

    def _is_safe_sql(self, sql: str) -> bool:
        from utils import is_safe_sql
        return is_safe_sql(sql)

    def log_successful_query(self, question: str, sql: str):
        # 可写入审核日志表，供人工复核
        print(f"[LEARN] biz={self.business_id} | Q: {question} | SQL: {sql}")