inputs = [
    "这个人喜欢独处，不喜欢社交活动。",
    "他总是很焦虑，容易紧张。",
    "她善于倾听，乐于助人。",
]
from selfevolving_network import SelfEvolvingNetwork
from cognitive_engine import CognitiveEngine
from strategy.personality_strategy import PersonalityStrategy

# 初始化网络并注入人格分析策略
network = SelfEvolvingNetwork(PersonalityStrategy(engine=CognitiveEngine()))
network.run(inputs)