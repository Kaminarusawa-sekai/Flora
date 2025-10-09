from multifeature.think_strategy import ThinkStrategy
from multifeature.agent_role import AgentRole



class PersonalityStrategy(ThinkStrategy):
    def generate_rule(self, observed: list):
        prompt = {
            "observed": [f.to_dict() for f in observed],
            "task": "从观察到的人格特征中归纳出一条通用规则"
        }
        return self.engine.agent_call(AgentRole.RULE_GENERATOR, prompt)

    def set_goal(self, observed: list):
        prompt = {
            "state": [f.to_dict() for f in observed],
            "task": "基于当前人格特征设定下一步分析目标"
        }
        return self.engine.agent_call(AgentRole.GOAL_SETTER, prompt)

    def optimize_operation(self, operation: str, observed: list):
        prompt = {
            "operation": operation,
            "state": [f.to_dict() for f in observed]
        }
        return self.engine.agent_call(AgentRole.OPERATION_OPTIMIZER, prompt)

    def get_name(self):
        return "PersonalityStrategy"