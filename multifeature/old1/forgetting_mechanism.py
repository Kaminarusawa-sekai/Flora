from datetime import datetime


# =================== 遗忘机制 ===================
class ForgettingMechanism:
    def __init__(self, decay_rate: float = 0.95, threshold: float = 0.1):
        self.usage_times = {}
        self.decay_rate = decay_rate
        self.threshold = threshold

    def use_rule(self, rule_id: str):
        self.usage_times[rule_id] = datetime.now()

    def decay_all(self):
        now = datetime.now()
        to_remove = []
        for rule_id, last_used in self.usage_times.items():
            delta_days = (now - last_used).total_seconds() / 86400
            decay_factor = self.decay_rate ** delta_days
            if decay_factor < self.threshold:
                to_remove.append(rule_id)
        for rule_id in to_remove:
            del self.usage_times[rule_id]
        return to_remove

    def is_forgotten(self, rule_id: str):
        return rule_id not in self.usage_times
