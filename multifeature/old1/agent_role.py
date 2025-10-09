from enum import Enum

# =================== 智能体角色定义 ===================
class AgentRole(Enum):
    RULE_GENERATOR = "rule_generator"
    OPERATION_OPTIMIZER = "operation_optimizer"
    GOAL_SETTER = "goal_setter"
    STATE_EVALUATOR = "state_evaluator"
    FEATURE_EXTRACTOR = "feature_extractor"