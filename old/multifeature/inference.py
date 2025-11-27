# inference.py
from logic import Atom, HornClause
from categories import DataCategory, TheoryCategory
from typing import Set, List
def deduction(deduce_from: TheoryCategory) -> Set[Atom]:
    """D: T → Data，返回所有可推导的事实"""
    # 简化：只返回被规则头直接匹配的事实
    result = set()
    for clause in deduce_from.clauses:
        # 实际应使用前向链推理，此处简化
        # 这里我们假设所有规则头都是已知事实（演示用）
        result.add(clause.head)
    return result

def induction(induce_from: DataCategory, all_possible_clauses: List[HornClause]) -> TheoryCategory:
    """I: Data → T，返回所有被数据蕴含的 Horn 子句"""
    theory = TheoryCategory()
    for clause in all_possible_clauses:
        # 检查数据是否满足前件，且后件在数据中
        if all(body in induce_from.facts for body in clause.body) and clause.head in induce_from.facts:
            theory.add_clause(clause)
    return theory