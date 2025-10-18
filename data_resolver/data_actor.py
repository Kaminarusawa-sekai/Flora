# actor.py
import thespian.actors as actors
from vanna_qwen_chroma import QwenVanna
from utils import should_learn
from mysql_pool import mysql_pool
import pandas as pd

from pymysql.cursors import Cursor  # 普通元组游标

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
        self.business_id = None
        self.database = None
        self.table_name = None
        print("[DataActor] Initialized")

    def receiveMessage(self, msg, sender):
        print("[DataActor] Received message:", msg)
        if msg.get("type") == "query":
            try:
                self._ensure_initialized(msg)
                question = msg["question"]

                # 生成 SQL
                sql = self.vn.generate_sql(question)

                # 安全审核
                if not self._is_safe_sql(sql):
                    print("[SQL] SQL is not safe")
                    raise ValueError("Generated SQL is not safe")

                # 执行
                conn = mysql_pool.get_connection(self.database)
                try:
                    df = pd.read_sql(sql, conn)
                    print(f"[SQL] {sql} | Rows: {len(df)}")
                finally:
                    conn.close()

                # ✅ 审核后自动学习
                if should_learn(df, sql):
                    self.vn.train(question=question, sql=sql)
                    # 可选：记录日志用于人工复核
                    self.log_successful_query(question, sql)

                self.send(sender, {
                    "success": True,
                    "result": df.to_dict(orient="records"),
                    "sql": sql
                })

            except Exception as e:
                import traceback
                error_detail = traceback.format_exc()
                print("🔥 CRITICAL ERROR:", error_detail)
                self.send(sender, {"success": False, "error": str(e),"detail": error_detail})

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