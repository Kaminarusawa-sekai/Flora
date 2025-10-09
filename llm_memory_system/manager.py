# memory/manager.py
from short_term import ShortTermMemory
from resourcememory import ResourceMemory
from vault import KnowledgeVault
from mem0 import Memory
from config import MEM0_CONFIG
from typing import Dict, Any

class UnifiedMemoryManager:
    """
    统一记忆管理器：融合短期记忆 + Mem0（长期） + 资源库 + 保险库
    """
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.stm = ShortTermMemory(max_history=10)
        
        # ✅ 使用 Mem0 处理长期记忆（语义、情景、核心）
        self.mem0 = Memory.from_config(MEM0_CONFIG)
        
        # 自定义模块
        self.resource_db = ResourceMemory()
        self.vault = KnowledgeVault(user_id)

    def ingest(self, content: str, role: str = "user"):
        """摄入新信息"""
        # 1. 短期记忆
        self.stm.add_message(role, content)

        # 2. 如果是用户输入，交给 Mem0 提取长期记忆
        if role == "user":
            self.mem0.add(content, user_id=self.user_id)

        # 3. 特殊指令：存入保险库
        if "请记住" in content or "重要信息" in content:
            self.vault.add(content, source=role)

        # 4. 如果是文档类内容，也可存入资源库（可选）
        # if "上传文件" in content:
        #     self.resource_db.add(content, metadata={"type": "note"})

    def build_context_for_llm(self, query: str = None) -> str:
        """为 LLM 构建上下文"""
        context_parts = []

        # 1. 对话历史（短期记忆）
        chat_history = self.stm.format_history(n=6)
        context_parts.append(f"[对话历史]\n{chat_history}")

        # 2. Mem0 提取的相关长期记忆
        if query:
            memories = self.mem0.get(query, user_id=self.user_id, limit=5)
            if memories:
                facts = "\n".join([f"• {m['memory']}" for m in memories])
                context_parts.append(f"[相关记忆]\n{facts}")

        # 3. 保险库中的高价值知识
        vault_knowledge = self.vault.search(query or "")
        if vault_knowledge:
            vault_text = "\n".join([f"📌 {k}" for k in vault_knowledge])
            context_parts.append(f"[重要知识]\n{vault_knowledge}")

        # 4. 资源库中的文档内容
        resources = self.resource_db.search(query or "")
        if resources:
            docs = "\n".join([f"📄 {r['content'][:200]}..." for r in resources])
            context_parts.append(f"[参考资料]\n{docs}")

        return "\n\n".join(context_parts)

    def search_memories(self, query: str, limit: int = 5):
        """直接查询 Mem0 记忆（用于调试）"""
        return self.mem0.get(query, user_id=self.user_id, limit=limit)

    def get_all_memories(self):
        """获取所有记忆（用于导出）"""
        return self.mem0.get_all(user_id=self.user_id)

    def clear_short_term(self):
        self.stm.clear()