# vanna_gpt_chroma.py

from typing import List, Any, Optional
from vanna.base import VannaBase
from vanna.chromadb import ChromaDB_VectorStore
from .ivanna_service import IVannaService
from .vanna_factory import register_vanna
from openai import OpenAI
import os

@register_vanna("gpt-chroma")
class GPTVanna(ChromaDB_VectorStore, VannaBase, IVannaService):
    def __init__(
        self,
        business_id: str,
        model: str = "gpt-4o",
        api_key: str = None,
        base_url: str = None,
        chroma_path: str = "./chroma",
        **kwargs
    ):
        ChromaDB_VectorStore.__init__(self, config={"path": chroma_path, "collection": business_id})
        self.business_id = business_id
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY env var.")
        self.client = OpenAI(api_key=self.api_key, base_url=base_url)

    def system_message(self, message: str) -> Any:
        return {"role": "system", "content": message}

    def user_message(self, message: str) -> Any:
        return {"role": "user", "content": message}

    def assistant_message(self, message: str) -> Any:
        return {"role": "assistant", "content": message}

    def submit_prompt(self, messages: List[Any]) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.0
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise RuntimeError(f"Failed to call OpenAI API: {e}")

    def train_ddl_with_database(self, database: str, table: str, ddl: str = None):
        if ddl is None:
            from .data_actor import get_mysql_ddl
            ddl = get_mysql_ddl(database, table)
        if f"`{database}`.`{table}`" not in ddl:
            ddl = ddl.replace(f"`{table}`", f"`{database}`.`{table}`")
        self.train(ddl=ddl)