
from typing import List, Callable, Optional
from pathlib import Path


from agent.optimization.optimization_adapter import ImproverAdapter

from multifeature.logic import HornClause, Atom
from multifeature.categories import DataCategory
from multifeature.belief_revision import KnowledgeBase
from multifeature.metrics import LearningMetrics
from multifeature.inference import induction,deduction
from multifeature.reflection import generate_reflection

# === 保持原有的归纳学习改进器 ===
class InductiveImprover(ImproverAdapter):
    """
    基于归纳学习的改进器（保持原有逻辑）
    """
    def __init__(
        self,
        kb: KnowledgeBase,
        metrics: LearningMetrics,
        all_clauses: List[HornClause],
        data_generator: Optional[Callable[[int], DataCategory]] = None,
        reflection_enabled: bool = True,
        state_file: Optional[str] = None
    ):
        self.kb = kb
        self.metrics = metrics
        self.all_clauses = all_clauses
        self.data_generator = data_generator or self._default_data_generator
        self.reflection_enabled = reflection_enabled
        self.state_file = Path(state_file) if state_file else None
        self._step = 0

        # 启动时加载状态
        if self.state_file and self.state_file.exists():
            self._load_state()

    def improve(self, task_id: str, score: float):
        self._step += 1
        print(f"\n--- Inductive Learning Step {self._step} (Score: {score:.3f}) ---")

        # 1. 生成新数据（可以根据分数调整策略）
        data = self.data_generator(self._step, score)

        # 2. 执行归纳
        theory = induction(data, self.all_clauses)
        existing_clauses = {r for r in self.kb.rules}
        new_rules = [c for c in theory.clauses if c not in existing_clauses]

        # 3. 更新知识库
        for rule in new_rules:
            self.kb.add_rule(rule)

        # 4. 更新指标
        gamma, kappa = self.metrics.update(
            new_rules=len(new_rules),
            data_size=len(data.facts),
            conflicts=len(self.kb.conflict_history),
            total_rules=len(self.kb.rules)
        )

        # 5. 反思（日志）
        if self.reflection_enabled:
            conflict_rule = "None"
            if self.kb.conflict_history:
                conflict_rule = str(self.kb.conflict_history[-1][1][0])
            recent = str(new_rules[0]) if new_rules else "None"
            generate_reflection(self.metrics, recent, conflict_rule)

        # 6. 持久化状态（可选）
        if self.state_file:
            self._save_state()

    def _default_data_generator(self, step: int, score: float) -> DataCategory:
        """默认数据生成器"""
        data = DataCategory()
        # 根据分数调整数据生成策略
        if score > 0.8:
            # 高分时生成更复杂的场景
            data.add_facts({Atom("ComplexScenario"), Atom("HighQualityResult")})
        else:
            # 低分时生成基础场景用于学习
            data.add_facts({Atom("BasicScenario"), Atom("LearningOpportunity")})
        return data

    # def _save_state(self):
    #     """保存当前状态到文件"""
    #     state = {
    #         "step": self._step,
    #         "rules": [
    #             {
    #                 "head": {"predicate": r.head.predicate, "args": r.head.args},
    #                 "body": [{"predicate": a.predicate, "args": a.args} for a in r.body]
    #             }
    #             for r in self.kb.rules
    #         ],
    #         "conflicts": len(self.kb.conflict_history),
    #         "metrics": {
    #             "total_new_rules": self.metrics.total_new_rules,
    #             "total_data_points": self.metrics.total_data_points,
    #             "total_conflicts": self.metrics.total_conflicts,
    #             "total_rules": self.metrics.total_rules
    #         }
    #     }
    #     self.state_file.parent.mkdir(exist_ok=True)
    #     with open(self.state_file, 'w') as f:
    #         json.dump(state, f, indent=2)

    # def _load_state(self):
    #     """从文件加载状态"""
    #     try:
    #         with open(self.state_file, 'r') as f:
    #             state = json.load(f)
            
    #         # 重建规则
    #         self.kb.rules = []
    #         for rule_data in state.get("rules", []):
    #             head_atom = Atom(
    #                 predicate=rule_data["head"]["predicate"],
    #                 args=tuple(rule_data["head"]["args"])
    #             )
    #             body_atoms = {
    #                 Atom(predicate=a["predicate"], args=tuple(a["args"]))
    #                 for a in rule_data["body"]
    #             }
    #             clause = HornClause(body=body_atoms, head=head_atom)
    #             self.kb.rules.append(clause)
            
    #         # 重建指标
    #         metrics_data = state.get("metrics", {})
    #         self.metrics.total_new_rules = metrics_data.get("total_new_rules", 0)
    #         self.metrics.total_data_points = metrics_data.get("total_data_points", 0)
    #         self.metrics.total_conflicts = metrics_data.get("total_conflicts", 0)
    #         self.metrics.total_rules = metrics_data.get("total_rules", 0)
            
    #         self._step = state.get("step", 0)
    #         print(f"Loaded state up to step {self._step}")
    #     except Exception as e:
    #         print(f"Failed to load state: {e}")
