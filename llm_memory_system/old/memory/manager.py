# memory/manager.py
from memory.core import CoreMemory
from memory.episodic import EpisodicMemory
from memory.procedural import ProceduralMemory
from memory.resource import ResourceMemory
from memory.vault import KnowledgeVault
from memory.semantic import SemanticMemory
from memory.short_term import ShortTermMemory
from chroma_db.chroma_client import add_semantic_fact, search_semantic
from utils.focus_extractor import extract_focus_keywords
from utils.qwen_client import call_qwen
from datetime import datetime
import json

class UnifiedMemoryManager:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 长期记忆
        self.core = CoreMemory(user_id)
        self.episodic = EpisodicMemory(user_id)
        self.procedural = ProceduralMemory(user_id)
        self.resource = ResourceMemory(user_id)
        self.vault = KnowledgeVault(user_id)
        self.semantic = SemanticMemory(user_id)

        # 短期记忆
        self.stm = ShortTermMemory()

    def ingest(self, content: str, role: str = "user", metadata: dict = None):
        self.stm.add_message(role, content, metadata)
        if role == "user":
            self._route_and_store_long_term(content, metadata)
            focus = extract_focus_keywords(content)
            self.stm.update_focus(focus)

    def _route_and_store_long_term(self, content: str, metadata: dict):
        """使用Qwen智能分配到不同记忆模块"""
        routing_prompt = f"""
你是一个智能记忆分配助手。请根据以下用户输入，判断它应该存储到哪个记忆模块中。

记忆模块选项：
1. core: 用户的核心个人信息，如姓名、偏好、设置等。
2. episodic: 用户叙述的事件、经历、对话历史等。
3. procedural: 步骤、流程、操作指南等。
4. resource: 文档、文件、资料等。
5. vault: 敏感信息，如密码、身份证号等。
6. semantic: 客观事实、知识、定义等。

请只回复一个JSON对象，包含一个 "module" 字段，值为上述选项之一。

用户输入: {content}
"""
        response = call_qwen([{"role": "user", "content": routing_prompt}], response_format="json_object")
        if response["status"] != "success":
            print(f"Qwen routing failed: {response['message']}")
            return # 或采用默认规则

        try:
            module = response["content"]["module"]
        except (KeyError, TypeError, json.JSONDecodeError) as e:
            print(f"Qwen routing response invalid: {e}")
            return

        print(f"[Routing] Input '{content[:20]}...' -> Module: {module}")

        # 存储到对应模块
        if module == "core":
            # 这里可以再调用Qwen提取key-value，为简化直接存整个句子
            # 示例：提取 "我叫张三" -> key: "name", value: "张三"
            kv_prompt = f"""
请从以下句子中提取键值对信息。例如：
输入: "我叫李雷，我喜欢蓝色"
输出: {{"name": "李雷", "likes": "蓝色"}}

只返回JSON对象。

输入: {content}
"""
            kv_response = call_qwen([{"role": "user", "content": kv_prompt}], response_format="json_object")
            if kv_response["status"] == "success":
                try:
                    kv_data = kv_response["content"]
                    for k, v in kv_data.items():
                        self.core.add(k, v)
                except Exception as e:
                    print(f"Failed to parse core KV: {e}")
                    self.core.add(f"raw_input_{int(datetime.now().timestamp())}", content)
            else:
                self.core.add(f"raw_input_{int(datetime.now().timestamp())}", content)

        elif module == "episodic":
            self.episodic.add(content, metadata.get("tags", []))

        elif module == "procedural":
            # 可以调用Qwen提取步骤
            steps_prompt = f"""
请将以下内容分解为清晰的步骤列表。例如：
输入: "如何煮咖啡：1. 加水 2. 加咖啡粉 3. 煮5分钟"
输出: ["加水", "加咖啡粉", "煮5分钟"]

只返回JSON数组。

输入: {content}
"""
            steps_response = call_qwen([{"role": "user", "content": steps_prompt}], response_format="json_object")
            steps = []
            if steps_response["status"] == "success":
                try:
                    steps = steps_response["content"]
                except:
                    pass
            name = metadata.get("name", f"流程_{int(datetime.now().timestamp())}")
            self.procedural.add(name, steps, metadata.get("domain", ""))

        elif module == "resource":
            title = metadata.get("title", f"资源_{int(datetime.now().timestamp())}")
            self.resource.add(title, content, metadata)

        elif module == "vault":
            key = metadata.get("key", f"sensitive_{int(datetime.now().timestamp())}")
            self.vault.add(key, content)

        elif module == "semantic":
            self.semantic.add(content)
            # 同时存入Chroma向量库
            fact_id = f"fact_{int(datetime.now().timestamp() * 1000000)}"
            add_semantic_fact("semantic_facts", fact_id, content)

    def build_context_for_llm(self, query: str = None) -> str:
        """
        使用Qwen判断查询意图，并进行语义匹配记忆查询
        """
        parts = []

        # 1. 核心记忆 (总是包含)
        core_info = self.core.to_prompt_string()
        if core_info:
            parts.append(f"[核心信息]\n{core_info}")

        # 2. 短期记忆: 最近对话
        recent_history = self.stm.get_history(6)
        if recent_history:
            chat = "\n".join([f"{m['role']}: {m['content']}" for m in recent_history[-4:]])
            parts.append(f"[最近对话]\n{chat}")

        # 3. 短期记忆: 当前焦点
        focus = self.stm.get_focus()
        if focus:
            parts.append(f"[当前焦点]\n{focus}")

        # 4. 长期记忆: 智能检索
        if query:
            # 4.1 使用Qwen判断需要查询的记忆类型
            intent_prompt = f"""
你是一个智能记忆检索助手。请根据用户的查询，判断需要从哪些长期记忆模块中检索信息。

记忆模块选项：
- core
- episodic
- procedural
- resource
- vault
- semantic

请只回复一个JSON对象，包含一个 "modules" 字段，值为一个包含模块名的数组。

用户查询: {query}
"""
            intent_response = call_qwen([{"role": "user", "content": intent_prompt}], response_format="json_object")
            target_modules = []
            if intent_response["status"] == "success":
                try:
                    target_modules = intent_response["content"].get("modules", [])
                except Exception as e:
                    print(f"Qwen intent analysis failed: {e}")
            # 默认查询语义记忆
            if not target_modules:
                target_modules = ["semantic"]

            print(f"[Intent Analysis] Query '{query}' -> Modules: {target_modules}")

            # 4.2 根据模块进行检索
            long_term_facts = []
            for module in target_modules:
                if module == "semantic":
                    # 使用Chroma进行语义搜索
                    semantic_results = search_semantic("semantic_facts", query, 3)
                    for fact_id, fact_text in semantic_results:
                        long_term_facts.append(fact_text)
                elif module == "episodic":
                    # 模糊匹配事件
                    # 注意：这里可以更复杂，比如用Qwen总结相关事件
                    pass # 暂略
                elif module == "procedural":
                    # 可以搜索流程名称
                    pass # 暂略

            if long_term_facts:
                facts_str = "\n".join(long_term_facts)
                parts.append(f"[相关知识]\n{facts_str}")

        return "\n\n".join(parts)

    # --- 其他辅助方法 ---
    def set_temp_variable(self, key: str, value):
        self.stm.set_state(key, value)

    def get_temp_variable(self, key: str, default=None):
        return self.stm.get_state(key, default)

    def is_session_expired(self, timeout_minutes: int = 30) -> bool:
        return self.stm.is_expired(timeout_minutes)

    def take_snapshot(self) -> dict:
        return self.stm.snapshot()

    def restore_snapshot(self, snapshot: dict):
        self.stm.restore_from_snapshot(snapshot)

    def start_new_session(self):
        self.stm.reset()
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")



