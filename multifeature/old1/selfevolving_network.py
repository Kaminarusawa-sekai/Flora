from multifeature.cognitive_engine import CognitiveEngine
from multifeature.evolver import Evolver
from multifeature.language_feature_set import LanguageFeatureSet
from multifeature.agent_role import AgentRole
from multifeature.memory_entry import MemoryEntry
from multifeature.rule_graph import RuleGraph
from multifeature.think_strategy import ThinkStrategy


# =================== 自演化网络主控类 ===================
class SelfEvolvingNetwork:
    def __init__(self,think_strategy: ThinkStrategy):
        self.engine = CognitiveEngine()
        self.memory = []
        self.evolver = Evolver(self.engine)
        self.think_strategy = think_strategy  # 注入思考策略

    def perceive(self, input_text: str):
        features = self.engine.agent_call(AgentRole.FEATURE_EXTRACTOR, {"input": input_text})
        desc = f"感知输入：{input_text}"
        fs = LanguageFeatureSet(description=desc, features=features)
        self.engine.add_feature_set(fs)
        self.memory.append(MemoryEntry("perceive", {"input": input_text, "features": features}))
        self.evolver.add_memory(MemoryEntry("perceive", {"input": input_text, "features": features}))

    def think(self):
            observed = self.engine.get_all_features()

            rule_desc = self.think_strategy.generate_rule(observed)
            goal = self.think_strategy.set_goal(observed)
            optimized_op = self.think_strategy.optimize_operation(
                operation="尝试分类对象",
                observed=observed
            )

            self.memory.append(MemoryEntry("think", {
                "rule": rule_desc,
                "goal": goal,
                "optimized_op": optimized_op,
            }))
            self.evolver.add_memory(MemoryEntry("think", {
                "rule": rule_desc,
                "goal": goal,
                "optimized_op": optimized_op,
            }))

    def evolve(self):
        self.evolver.generalize()

    def run(self, inputs: list, auto_evolve=True):
        for inp in inputs:
            print(">>> 输入感知：", inp)
            self.perceive(inp)
            self.think()
            if auto_evolve and len(self.memory) % 3 == 0:
                self.evolve()