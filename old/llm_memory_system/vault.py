# memory/vault.py
from typing import Dict, List
import json
import os

class KnowledgeVault:
    """用于存储用户明确要求“记住”的高价值知识"""
    def __init__(self, user_id: str, path="./vaults"):
        self.user_id = user_id
        self.path = os.path.join(path, f"{user_id}.json")
        os.makedirs(path, exist_ok=True)
        self.data = self._load()

    def _load(self) -> List[Dict]:
        if os.path.exists(self.path):
            with open(self.path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def add(self, knowledge: str, source: str = "user"):
        entry = {
            "knowledge": knowledge,
            "source": source,
            "timestamp": self._timestamp()
        }
        self.data.append(entry)
        self._save()

    def search(self, query: str) -> List[str]:
        # 简单关键词匹配，可替换为向量化搜索
        return [item["knowledge"] for item in self.data if query.lower() in item["knowledge"].lower()]

    def _timestamp(self):
        from datetime import datetime
        return datetime.now().isoformat()