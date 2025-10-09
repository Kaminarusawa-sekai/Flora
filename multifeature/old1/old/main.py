# main.py

from storage import UserProfiler
from prompt_engineer import BehaviorFeatureExtractor
from personality_miner import PersonalityMiner

profiler = UserProfiler()
extractor = BehaviorFeatureExtractor()
miner = PersonalityMiner(profiler)

# 创建用户
user_id = profiler.create_user()

# 多轮对话模拟
dialogue_rounds = [
    {
        "behavior": "用户花大量时间阅读文档，并在代码中添加详细注释",
        "round": 1
    },
    {
        "behavior": "用户很少参与讨论，但在关键问题上给出高质量反馈",
        "round": 2
    },
    {
        "behavior": "用户倾向于自己解决问题，而不是寻求帮助",
        "round": 3
    }
]

print("【开始多轮对话分析】")
for r in dialogue_rounds:
    print(f"\n--- 第 {r['round']} 轮行为 ---")
    print("行为描述:", r["behavior"])

    current_profile = profiler.get_profile(user_id)
    prev_features = current_profile.get_features() if current_profile else []

    new_features = extractor.extract_from_behavior(r["behavior"], prev_features)
    print("提取出的新特征:")
    for f in new_features:
        print(f"- {f}")

    profiler.update_profile(user_id, new_features)
    print("当前完整特征集:")
    print(profiler.get_profile(user_id))

# 自我进化：发现典型类型
print("\n【正在聚类并生成典型人格类型】")
clusters = miner.cluster_users(eps=0.6, min_samples=1)
for label, users in clusters.items():
    print(f"\nCluster {label} 包含用户: {users}")
    name, features = miner.generate_personality_type(label, users)
    print(f"生成类型 {name}:")
    print(features)