# logic.py
from dataclasses import dataclass
from typing import Set, List, Tuple
from pyeda.boolalg.expr import exprvar, And, Or, Not, Implies

@dataclass(frozen=True)
class Atom:
    predicate: str
    args: Tuple[str, ...]

    def __str__(self):
        return f"{self.predicate}({', '.join(self.args)})"

@dataclass(frozen=True)
class HornClause:
    body: Set[Atom]  # 前件（可为空）
    head: Atom       # 后件

    def __str__(self):
        if not self.body:
            return str(self.head)
        body_str = " ∧ ".join(str(a) for a in self.body)
        return f"{body_str} → {self.head}"

    def entails(self, fact: Atom) -> bool:
        """简单模拟：如果 head 匹配，则蕴含"""
        return self.head == fact