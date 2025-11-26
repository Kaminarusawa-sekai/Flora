from pathlib import Path
from typing import List, Optional
from new.capabilities.llm_memory.memory_interfaces import IProceduralRepository
import yaml
import numpy as np
from sentence_transformers import SentenceTransformer


class FileBasedProceduralRepository(IProceduralRepository):
    def __init__(self, procedures_dir: str):
        self.dir = Path(procedures_dir)
        self.dir.mkdir(exist_ok=True)
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self._load()

    def _load(self):
        self.procedures = []
        self.embeddings = []
        for f in self.dir.glob("*.yaml"):
            with open(f, "r", encoding="utf-8") as fp:
                proc = yaml.safe_load(fp)
                proc["id"] = f.stem
                text = f"{proc.get('title', '')}\n{proc.get('description', '')}\n{' '.join(proc.get('steps', []))}"
                proc["search_text"] = text
                self.procedures.append(proc)
        if self.procedures:
            texts = [p["search_text"] for p in self.procedures]
            self.embeddings = self.model.encode(texts)
        else:
            self.embeddings = np.array([])

    def add_procedure(self, domain, task_type, title, steps, description="", tags=None):
        proc_id = f"{domain}_{task_type}".replace(" ", "_").lower()
        path = self.dir / f"{proc_id}.yaml"
        data = {
            "domain": domain,
            "task_type": task_type,
            "title": title,
            "description": description,
            "steps": steps,
            "tags": tags or []
        }
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, indent=2)
        self._load()  # 热重载

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