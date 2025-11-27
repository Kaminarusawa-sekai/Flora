# example.py
from manager import UnifiedMemoryManager

# 初始化
manager = UnifiedMemoryManager(user_id="user_001")

# 模拟对话
manager.ingest("我叫李明，我在北京工作。", role="user")
manager.ingest("你喜欢北京吗？", role="assistant")
manager.ingest("还行，但我更喜欢上海，我妈妈在上海。", role="user")
manager.ingest("请记住：我的密码是 123456", role="user")  # 会被存入 vault
manager.ingest("我下个月要搬到上海了", role="user")

# 查询
query = "我妈妈住在哪里？"
context = manager.build_context_for_llm(query)
print(context)