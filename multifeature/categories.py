# categories.py
from typing import Set
from logic import Atom, HornClause

class DataCategory:
    def __init__(self):
        self.facts: Set[Atom] = set()

    def add_facts(self, facts: Set[Atom]):
        self.facts |= facts

    def subset(self, other: 'DataCategory') -> bool:
        return self.facts.issubset(other.facts)

class TheoryCategory:
    def __init__(self):
        self.clauses: Set[HornClause] = set()

    def add_clause(self, clause: HornClause):
        self.clauses.add(clause)

    def entails(self, fact: Atom) -> bool:
        return any(c.entails(fact) for c in self.clauses)

    def __str__(self):
        return "\n".join(str(c) for c in self.clauses)