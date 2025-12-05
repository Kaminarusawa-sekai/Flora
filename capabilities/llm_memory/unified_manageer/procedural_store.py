# procedural_store.py
import os
import yaml
import json
from pathlib import Path
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
import numpy as np
import pickle

PROCEDURES_DIR = "procedures"
EMBEDDINGS_FILE = "procedures_embeddings.pkl"

class ProceduralStore:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.procedures_dir = Path(PROCEDURES_DIR)
        self.procedures_dir.mkdir(exist_ok=True)
        self.model = SentenceTransformer(model_name)
        self.procedures = []      # List[Dict]
        self.embeddings = None    # np.ndarray
        self._load_procedures()

    def _load_procedures(self):
        """从 YAML/Markdown 加载所有流程"""
        self.procedures = []
        for f in self.procedures_dir.glob("*.yaml"):
            with open(f, "r", encoding="utf-8") as fp:
                proc = yaml.safe_load(fp)
                proc["id"] = f.stem
                # 构建用于检索的文本
                text = f"{proc.get('title', '')}\n{proc.get('description', '')}\n{' '.join(proc.get('steps', []))}"
                proc["search_text"] = text
                self.procedures.append(proc)

        if self.procedures:
            texts = [p["search_text"] for p in self.procedures]
            self.embeddings = self.model.encode(texts)
            # 可选：缓存 embeddings
            with open(EMBEDDINGS_FILE, "wb") as f:
                pickle.dump((self.procedures, self.embeddings), f)
        else:
            self.embeddings = np.array([])

    def add_procedure(
        self,
        domain: str,
        task_type: str,
        title: str,
        steps: List[str],
        description: str = "",
        tags: Optional[List[str]] = None
    ):
        proc_id = f"{domain}_{task_type}".replace(" ", "_").lower()
        proc_path = self.procedures_dir / f"{proc_id}.yaml"
        data = {
            "domain": domain,
            "task_type": task_type,
            "title": title,
            "description": description,
            "steps": steps,
            "tags": tags or []
        }
        with open(proc_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, indent=2)
        self._load_procedures()  # 重新加载

    def search(self, query: str, domain: Optional[str] = None, limit: int = 3) -> List[str]:
        if not self.procedures:
            return []

        query_emb = self.model.encode([query])[0]
        scores = np.dot(self.embeddings, query_emb)
        top_indices = np.argsort(scores)[::-1][:limit]

        results = []
        for i in top_indices:
            proc = self.procedures[i]
            if domain and proc.get("domain") != domain:
                continue
            formatted = (
                f"【{proc['title']}】\n"
                f"领域: {proc['domain']} | 类型: {proc['task_type']}\n"
                f"步骤:\n" + "\n".join(f"- {step}" for step in proc["steps"])
            )
            results.append(formatted)
        return results[:limit]