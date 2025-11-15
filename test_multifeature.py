import sys
import os

# 确保new目录被添加到sys.path
new_path = os.path.abspath(r'e:\Data\Flora\new')
if new_path not in sys.path:
    sys.path.insert(0, new_path)

# 移除旧的multifeature目录如果存在
old_multifeature_path = r'e:\Data\Flora'
if old_multifeature_path in sys.path:
    sys.path.remove(old_multifeature_path)

# 现在可以直接从multifeature导入
from capabilities.multifeature import KnowledgeBase, MultifeatureOptimizer

# 测试知识库功能
print("--- Testing KnowledgeBase ---")
kb = KnowledgeBase()

# 添加测试规则
rule1 = {
    'type': 'success_pattern',
    'pattern': {'params': {'a': 1, 'b': 2}},
    'action': 'reinforce',
    'confidence': 0.8
}

rule2 = {
    'type': 'success_pattern',
    'pattern': {'params': {'a': 1, 'b': 2}},
    'action': 'avoid',
    'confidence': 0.9
}

print("Adding rule 1...")
kb.add_rules([rule1])
print(f'Number of rules: {len(kb.rules)}')

print("\nAdding conflicting rule 2...")
kb.add_rules([rule2])
print(f'Number of rules: {len(kb.rules)}')

print(f'\nAll success_pattern rules: {kb.get_rules_by_type("success_pattern")}')

# 测试适用规则
print("\n--- Testing get_applicable_rules ---")
context = {'a': 1, 'b': 2}
applicable_rules = kb.get_applicable_rules(context)
print(f'Context: {context}')
print(f'Applicable rules: {applicable_rules}')

# 测试自优化器
print("\n--- Testing MultifeatureOptimizer ---")
optimizer = MultifeatureOptimizer()
print('MultifeatureOptimizer initialized successfully')

# 测试优化任务
print("\n--- Testing optimize_task ---")
task = {'context': {'a': 1, 'b': 2}}
history_data = [{'params': {'a': 1, 'b': 2}, 'score': 0.8}]
result = optimizer.optimize_task(task, history_data)
print(f'Optimization result: {result}')

print("\nAll tests completed successfully!")