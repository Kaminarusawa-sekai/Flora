# vanna_doubao_chroma.py

from typing import List, Any, Optional
import json
from vanna.base import VannaBase
from vanna.chromadb import ChromaDB_VectorStore
from ivanna_service import IVannaService
from vanna_factory import register_vanna
from volcengine.maas import MaasService
import os

@register_vanna("doubao-chroma")
class DoubaoVanna(ChromaDB_VectorStore, VannaBase, IVannaService):
    def __init__(
        self,
        business_id: str,
        model: str = "doubao-pro-32k",
        access_key: str = None,
        secret_key: str = None,
        region: str = "cn-beijing",
        chroma_path: str = "./chroma",
        **kwargs
    ):
        ChromaDB_VectorStore.__init__(self, config={"path": chroma_path, "collection": business_id})
        self.business_id = business_id
        self.model = model
        self.access_key = access_key or os.getenv("VOLC_ACCESS_KEY")
        self.secret_key = secret_key or os.getenv("VOLC_SECRET_KEY")
        if not self.access_key or not self.secret_key:
            raise ValueError("VOLC_ACCESS_KEY and VOLC_SECRET_KEY are required for Doubao.")

        self.maas = MaasService(region)
        self.maas.set_ak(self.access_key)
        self.maas.set_sk(self.secret_key)

    def system_message(self, message: str) -> Any:
        return {"role": "system", "content": message}

    def user_message(self, message: str) -> Any:
        return {"role": "user", "content": message}

    def assistant_message(self, message: str) -> Any:
        return {"role": "assistant", "content": message}

    def submit_prompt(self, messages: List[Any]) -> str:
        try:
            # 火山引擎要求 messages 必须以 user 开头（不能以 system 开头？实测可带 system）
            # 构造 req
            req = {
                "model": {
                    "name": self.model,
                },
                "parameters": {
                    "max_new_tokens": 1024,
                    "temperature": 0.1,
                },
                "messages": messages
            }
            resp = self.maas.chat(req)
            if resp.get("code", 0) != 0:
                raise RuntimeError(f"Doubao API error [{resp.get('code')}]: {resp.get('message')}")
            return resp["result"]["content"]
        except Exception as e:
            raise RuntimeError(f"Failed to call Doubao API: {e}")

    def train_ddl_with_database(self, database: str, table: str, ddl: str = None):
        if ddl is None:
            from .data_actor import get_mysql_ddl
            ddl = get_mysql_ddl(database, table)
        if f"`{database}`.`{table}`" not in ddl:
            ddl = ddl.replace(f"`{table}`", f"`{database}`.`{table}`")
        self.train(ddl=ddl)