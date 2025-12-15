# vanna_qwen_chroma.py

import os
import re
from typing import List, Tuple, Any, Optional
from vanna.base import VannaBase
from vanna.chromadb import ChromaDB_VectorStore
from dashscope import Generation
from config import DASHSCOPE_API_KEY
from .ivanna_service import IVannaService  # 引入接口

from .vanna_factory import register_vanna


@register_vanna("qwen_chroma")
class QwenChromeVanna(ChromaDB_VectorStore, VannaBase, IVannaService):
    """
    集成 Qwen（通义千问）作为 LLM，Chroma 作为向量数据库的 Vanna 实现。
    强制生成带 `database.table` 的 SELECT SQL。
    """

    def __init__(
        self,
        business_id: str,
        model: str = "qwen-max",
        api_key: str = None,
        chroma_path: str = "./chroma",
        **kwargs
    ):
        ChromaDB_VectorStore.__init__(self, config={"path": chroma_path, "collection": business_id})
        self.business_id = business_id
        self.model = model
        self.api_key = api_key or DASHSCOPE_API_KEY
        if not self.api_key:
            raise ValueError("DashScope API key is required. Set DASHSCOPE_API_KEY env var or pass api_key.")

    def system_message(self, message: str) -> Any:
        return {"role": "system", "content": message}

    def user_message(self, message: str) -> Any:
        return {"role": "user", "content": message}

    def assistant_message(self, message: str) -> Any:
        return {"role": "assistant", "content": message}

    def submit_prompt(self, messages: List[Any]) -> str:
        try:
            response = Generation.call(
                model=self.model,
                api_key=self.api_key,
                messages=messages,
                result_format='message'
            )
            if response.status_code != 200:
                raise RuntimeError(f"Qwen API error [{response.code}]: {response.message}")
            return response.output.choices[0].message.content.strip()
        except Exception as e:
            raise RuntimeError(f"Failed to call Qwen API: {e}")

    def train_ddl_with_database(self, database: str, table: str, ddl: str = None):
        if ddl is None:
            from .data_actor import get_mysql_ddl
            ddl = get_mysql_ddl(database, table)
        if f"`{database}`.`{table}`" not in ddl:
            ddl = ddl.replace(f"`{table}`", f"`{database}`.`{table}`")
        self.train(ddl=ddl)

    # 如果你取消注释了 generate_sql，确保它存在
    # （这里我们让它继承 VannaBase 的逻辑，除非特别需要覆盖）
     # ==============================
    # ✅ 可选：覆盖 generate_sql 以强化 database.table 约束（推荐）
    # ==============================

    # def generate_sql(self, question: str, database: str = None, **kwargs) -> str:
    #     """
    #     生成 SQL，确保 DDL 和示例中包含 database 前缀。
    #     如果提供了 database，会在 prompt 中强调必须使用 `database.table`。
    #     """
    #     ddls = self.get_related_ddl(question)
    #     docs = self.get_related_documentation(question)
    #     examples = self.get_similar_question_sql(question)

    #     # 如果指定了 database，确保 DDL 中包含库名（训练时应已处理，此处为兜底）
    #     if database:
    #         ddls = [
    #             re.sub(r"CREATE TABLE `([^`]+)`", f"CREATE TABLE `{database}`.`\\1`", ddl)
    #             for ddl in ddls
    #         ]

    #     # 构造 messages
    #     messages = []
    #     system_prompt = (
    #         "你是一个专业的 MySQL 数据分析师。请根据提供的表结构和示例，"
    #         "生成**仅包含 SELECT 的 SQL 查询语句**。\n"
    #         "⚠️ **必须使用完整的 `数据库名.表名` 格式**（例如：`eqiai_wecom.crm_channel_active_info`）。\n"
    #         "⚠️ **不要生成任何解释、注释或额外文本，只输出 SQL 语句。**"
    #     )
    #     messages.append(self.system_message(system_prompt))

    #     if ddls:
    #         messages.append(self.user_message("以下是相关表的结构定义（DDL）：\n" + "\n".join(ddls)))
    #     if docs:
    #         messages.append(self.user_message("业务背景说明：\n" + "\n".join(docs)))
    #     if examples:
    #         ex_str = "\n".join([f"问题：{q}\nSQL：{sql}" for q, sql in examples[:3]])
    #         messages.append(self.user_message("参考示例（请严格遵循格式）：\n" + ex_str))

    #     messages.append(self.user_message(f"问题：{question}\nSQL："))

    #     sql = self.submit_prompt(messages)

    #     # 清理可能的多余文本（如 "```sql"）
    #     if sql.startswith("```sql"):
    #         sql = sql[6:]
    #     if sql.endswith("```"):
    #         sql = sql[:-3]
    #     return sql.strip()