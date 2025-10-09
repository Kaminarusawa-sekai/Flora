# belief_revision.py
from logic import HornClause
from categories import TheoryCategory
import time

class RuleWithPriority:
    def __init__(self, clause: HornClause):
        self.clause = clause
        self.verification_score = 1.0
        self.context_score = 1.0
        self.timestamp = time.time()
        self.use_count = 0

    def priority(self, alpha=0.4, beta=0.4, gamma=0.2, lambd=0.01):
        age_factor = 1.0
        if hasattr(self, 'last_used'):
            age_factor = max(0.1, 1.0 - lambd * (time.time() - self.timestamp))
        return alpha * self.verification_score + beta * self.context_score + gamma * age_factor

class KnowledgeBase:
    def __init__(self):
        self.rules: List[RuleWithPriority] = []
        self.conflict_history = []

    def add_rule(self, new_rule: HornClause, verify_fn=None):
        new_wrapped = RuleWithPriority(new_rule)
        
        # 检查冲突
        conflicts = []
        for existing in self.rules:
            if self._would_conflict(new_rule, existing.clause):
                conflicts.append(existing)

        if conflicts:
            print(f"Conflict detected: {new_rule} vs {conflicts[0].clause}")
            self.conflict_history.append((new_rule, [r.clause for r in conflicts]))

            # 优先级比较
            new_priority = new_wrapped.priority()
            old_priority = max(r.priority() for r in conflicts)
            if new_priority > old_priority:
                print("→ New rule wins. Removing old rules.")
                for r in conflicts:
                    self.rules.remove(r)
                self.rules.append(new_wrapped)
            else:
                print("→ Old rule wins. Discarding new rule.")
        else:
            self.rules.append(new_wrapped)

    def _would_conflict(self, r1: HornClause, r2: HornClause) -> bool:
        # 简化：检查是否 head 相同但 body 不同（可能矛盾）
        return r1.head == r2.head and r1.body != r2.body

    def get_theory(self) -> TheoryCategory:
        t = TheoryCategory()
        for r in self.rules:
            t.add_clause(r.clause)
        return t