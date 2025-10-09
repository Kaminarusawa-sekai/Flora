# metrics.py
class LearningMetrics:
    def __init__(self):
        self.history = []

    def update(self, new_rules: int, data_size: int, conflicts: int, total_rules: int):
        gamma = new_rules / (data_size + 1e-8)  # 学习率
        kappa = conflicts / (total_rules + 1e-8) if total_rules > 0 else 0  # 冲突指数
        
        self.history.append({
            'gamma': gamma,
            'kappa': kappa,
            'new_rules': new_rules,
            'conflicts': conflicts
        })
        return gamma, kappa