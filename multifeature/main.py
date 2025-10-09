# main.py
from logic import Atom, HornClause
from categories import DataCategory
from inference import induction, deduction
from belief_revision import KnowledgeBase
from causal import run_pc_algorithm, orient_edges
from metrics import LearningMetrics
from reflection import generate_reflection
import numpy as np

def main():
    # === 1. 初始化 ===
    kb = KnowledgeBase()
    metrics = LearningMetrics()
    
    # 所有可能的规则（简化）
    all_clauses = [
        HornClause(body={Atom("Rains(X)", ("X",))}, head=Atom("WetGround(X)", ("X",))),
        HornClause(body={Atom("SprinklerOn(X)", ("X",))}, head=Atom("WetGround(X)", ("X",))),
    ]

    # === 2. 模拟两轮学习 ===
    for step in range(2):
        print(f"\n--- Step {step+1} ---")
        
        # 模拟新数据
        data = DataCategory()
        if step == 0:
            data.add_facts({Atom("Rains(A)", ()), Atom("WetGround(A)", ())})
        else:
            data.add_facts({Atom("SprinklerOn(A)", ()), Atom("WetGround(A)", ())})
        
        # 归纳
        new_theory = induction(data, all_clauses)
        new_rules = [c for c in new_theory.clauses if c not in [r.clause for r in kb.rules]]
        
        # 添加到知识库（带冲突检测）
        for rule in new_rules:
            kb.add_rule(rule)
        
        # 更新度量
        gamma, kappa = metrics.update(
            new_rules=len(new_rules),
            data_size=len(data.facts),
            conflicts=len(kb.conflict_history),
            total_rules=len(kb.rules)
        )
        
        # 自省
        if kb.conflict_history:
            conflict_rule = str(kb.conflict_history[-1][1][0])
        else:
            conflict_rule = "None"
            
        generate_reflection(
            metrics=metrics,
            recent_rule=str(new_rules[0]) if new_rules else "None",
            conflict_rule=conflict_rule
        )

    # === 3. 因果发现演示 ===
    print("\n--- Causal Discovery ---")
    # 模拟数据：Rains, Sprinkler, WetGround
    np.random.seed(42)
    n = 1000
    rains = np.random.binomial(1, 0.3, n)
    sprinkler = np.random.binomial(1, 0.4, n)
    wet = (rains | sprinkler).astype(float) + np.random.normal(0, 0.1, n)
    data_matrix = np.column_stack([rains, sprinkler, wet])
    
    skeleton = run_pc_algorithm(data_matrix)
    print("PC Skeleton Edges:", skeleton.edges)
    
    DG = orient_edges(skeleton, ["Rains(X)", "SprinklerOn(X)", "WetGround(X)"])
    print("Oriented Causal Edges:", [(u, v) for u, v in DG.edges])

if __name__ == "__main__":
    main()