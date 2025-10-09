from multifeature.agent_role import AgentRole
from multifeature.language_feature_set import LanguageFeatureSet
import json
from multifeature.call_llm import call_qwen

class CognitiveEngine:
    def __init__(self):
        self.feature_db = {}
        self.agents = {
            AgentRole.RULE_GENERATOR: self.generate_rule,
            AgentRole.OPERATION_OPTIMIZER: self.optimize_operation,
            AgentRole.GOAL_SETTER: self.set_goal,
            AgentRole.STATE_EVALUATOR: self.evaluate_state,
            AgentRole.FEATURE_EXTRACTOR: self.extract_features
        }

    def add_feature_set(self, fs: LanguageFeatureSet):
        self.feature_db[fs.id] = fs

    def get_all_features(self):
        return list(self.feature_db.values())

    def agent_call(self, role: AgentRole, context: dict):
        return self.agents[role](context)

    def generate_rule(self, context: dict):
        prompt = f"""
你是规则生成器，请根据以下上下文生成一条新的抽象规则：
上下文：{json.dumps(context)}

请输出一条规则的自然语言描述，例如：
- 如果观察到多个相似对象，则进一步收集信息
- 如果特征之间有交集，则抽象出共性特征
"""
        return call_qwen(prompt, AgentRole.RULE_GENERATOR)

    def optimize_operation(self, context: dict):
        prompt = f"""
你是操作优化器，请根据以下操作描述和当前状态优化该操作：
当前操作：{context.get('operation')}
当前状态：{context.get('state')}

请输出优化后的操作建议。
"""
        return call_qwen(prompt, AgentRole.OPERATION_OPTIMIZER)

    def set_goal(self, context: dict):
        prompt = f"""
你是目标设定者，请根据以下系统状态设定下一步目标：
系统状态：{context.get('state')}

请输出下一步目标的自然语言描述。
"""
        return call_qwen(prompt, AgentRole.GOAL_SETTER)

    def evaluate_state(self, context: dict):
        prompt = f"""
你是状态评估器，请评估以下系统状态并给出评分（0-10）：
系统状态：{context.get('state')}

请输出评分和简要说明。
"""
        return call_qwen(prompt, AgentRole.STATE_EVALUATOR)

    def extract_features(self, context: dict):
        prompt = f"""
你是特征提取器，请从以下输入中提取关键特征：
输入内容：{context.get('input')}

请输出一个特征列表，格式为 key:value。
"""
        raw_output = call_qwen(prompt, AgentRole.FEATURE_EXTRACTOR)
        features = {}
        for line in raw_output.split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                features[k.strip()] = v.strip()
        return features