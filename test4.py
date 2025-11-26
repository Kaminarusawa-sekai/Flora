from mem0 import Memory
from config import MEM0_CONFIG
from time import sleep
import time

# 使用你的配置
from mem0 import Memory

mem0 = Memory.from_config(MEM0_CONFIG)  # 或默认初始化

# 清理（如果支持）
try:
    mem0.delete(user_id="test_u1")
    mem0.delete(user_id="test_u2")
except:
    pass

# 写入两个用户
mem0.add("Alice's secret", user_id="test_u1", metadata={"type": "test"})
mem0.add("Bob's secret", user_id="test_u2", metadata={"type": "test"})

time.sleep(2)

# 分别搜索
r1 = mem0.search("secret", user_id="test_u1", filters={"type": "test"})
r2 = mem0.search("secret", user_id="test_u2", filters={"type": "test"})

print("U1 sees:", [x["memory"] for x in r1["results"]])
print("U2 sees:", [x["memory"] for x in r2["results"]])