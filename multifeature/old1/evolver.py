from datetime import datetime
from itertools import combinations
import json
from multifeature.memory_entry import MemoryEntry
from multifeature.call_llm import call_qwen
from multifeature.cognitive_engine import CognitiveEngine
from multifeature.agent_role import AgentRole
from multifeature.rule_graph import RuleGraph
from multifeature.rule_prioritizer import RulePrioritizer
from multifeature.forgetting_mechanism import ForgettingMechanism


# =================== 自演化核心模块 ===================
class Evolver:
    def __init__(self, cognitive_engine):
        self.engine = cognitive_engine
        self.memory = []
        self.rule_pool = {}  # rule_id -> rule_description
        self.rule_graph = RuleGraph()
        self.prioritizer = RulePrioritizer()
        self.forgetter = ForgettingMechanism(decay_rate=0.95, threshold=0.1)

    def add_memory(self, entry: MemoryEntry):
        self.memory.append(entry)

    def get_recent_memories(self, n=5):
        return self.memory[-n:]

    def evolve_rules(self):
        recent = self.get_recent_memories(5)
        if not recent:
            return

        context = "\n".join([f"{m.type}: {json.dumps(m.content)}" for m in recent])
        prompt = f"""
你是进化系统，请从以下最近的记忆中归纳出一条新的抽象规则：
{
context
}

请输出该规则的自然语言描述。例如：
- 如果观察到多个相似对象，则进一步收集信息
- 如果特征之间有交集，则抽象出共性特征
"""
        new_rule = self.engine.agent_call(AgentRole.RULE_GENERATOR, {"context": context})
        if new_rule:
            rule_id = f"rule_{len(self.rule_pool)}"
            self.rule_pool[rule_id] = new_rule
            self.rule_graph.add_rule(rule_id, new_rule)
            self.prioritizer.boost_rule(rule_id)
            print(f"🧬 归纳出的新规则 [{rule_id}]: {new_rule}")

    def connect_similar_rules(self):
        rule_ids = list(self.rule_pool.keys())
        if len(rule_ids) < 2:
            return

        for a, b in combinations(rule_ids, 2):
            prompt = f"""
请判断以下两条规则是否相似：
规则A：{self.rule_pool[a]}
规则B：{self.rule_pool[b]}

回答仅限“是”或“否”
"""
            response = call_qwen(prompt, AgentRole.RULE_GENERATOR)
            if "是" in response:
                self.rule_graph.link_rules(a, b, relation="similar")
                print(f"🔗 已连接规则 {a} 和 {b}（相似）")

    def prioritize_rules(self):
        for rule_id in self.rule_pool:
            self.prioritizer.boost_rule(rule_id, 0.1)

    def forget_old_rules(self):
        removed = self.forgetter.decay_all()
        for rule_id in removed:
            if rule_id in self.rule_pool:
                print(f"💤 忘记规则 [{rule_id}]: {self.rule_pool[rule_id]}")
                del self.rule_pool[rule_id]

    def generalize(self):
        print("🔄 开始自我演化...")
        self.evolve_rules()
        self.connect_similar_rules()
        self.prioritize_rules()
        self.forget_old_rules()
        print("✅ 演化完成")