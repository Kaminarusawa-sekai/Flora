from collections import defaultdict

# =================== 规则优先级排序 ===================
class RulePrioritizer:
    def __init__(self):
        self.rule_scores = defaultdict(float)

    def update_score(self, rule_id: str, score_change: float):
        self.rule_scores[rule_id] += score_change

    def rank_rules(self, rules: list):
        ranked = sorted(rules, key=lambda r: (-self.rule_scores.get(r, 0)))
        return ranked

    def boost_rule(self, rule_id: str, amount: float = 1.0):
        self.update_score(rule_id, amount)

    def penalize_rule(self, rule_id: str, amount: float = 1.0):
        self.update_score(rule_id, -amount)