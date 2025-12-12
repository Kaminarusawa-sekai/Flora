from pathlib import Path
from typing import List, Optional
from tasks.capabilities.llm_memory.unified_manageer.memory_interfaces import IProceduralRepository
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
                # 确保有 user_id 字段（兼容旧数据）
                if "user_id" not in proc:
                    proc["user_id"] = "default"  # 或跳过？根据需求
                text = f"{proc.get('title', '')}\n{proc.get('description', '')}\n{' '.join(proc.get('steps', []))}"
                proc["search_text"] = text
                self.procedures.append(proc)
        if self.procedures:
            texts = [p["search_text"] for p in self.procedures]
            self.embeddings = self.model.encode(texts)
        else:
            self.embeddings = np.array([])

    def add_procedure(self, user_id: str, domain: str, task_type: str, title: str, steps: List[str], description: str = "", tags: List[str] = None):
        # 建议用 user_id + domain + task_type 组合作为文件名，避免冲突
        proc_id = f"{user_id}_{domain}_{task_type}".replace(" ", "_").lower()
        path = self.dir / f"{proc_id}.yaml"
        data = {
            "user_id": user_id,          # 👈 保存 user_id
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

    def search(self, user_id: str, query: str, domain: Optional[str] = None, limit: int = 3) -> List[str]:
        if not self.procedures:
            return []
        
        query_emb = self.model.encode([query])[0]
        scores = np.dot(self.embeddings, query_emb)
        
        results = []
        # 遍历所有条目，按得分从高到低筛选
        for idx in np.argsort(scores)[::-1]:
            proc = self.procedures[idx]
            # 按 user_id 过滤
            if proc.get("user_id") != user_id:
                continue
            # 按 domain 过滤（如果指定了）
            if domain is not None and proc.get("domain") != domain:
                continue
            formatted = (
                f"【{proc['title']}】\n"
                f"用户: {proc['user_id']} | 领域: {proc['domain']} | 类型: {proc['task_type']}\n"
                f"步骤:\n" + "\n".join(f"- {step}" for step in proc["steps"])
            )
            results.append(formatted)
            if len(results) >= limit:
                break
        
        return results