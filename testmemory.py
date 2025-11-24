# main.py
import os
from typing import Dict, Any



# === 在此处粘贴你已有的 UnifiedMemoryManager 和 MemoryCapability 类 ===
# （包括上面提供的 ShortTermMemory 等最小实现）

# ... [UnifiedMemoryManager, MemoryCapability, ShortTermMemory, ResourceMemory, KnowledgeVault 的完整定义] ...
from new.capabilities.llm_memory.manager import UnifiedMemoryManager, MemoryCapability
# === 主测试函数 ===
def main():
    print("🚀 启动记忆能力测试...\n")

    cap = MemoryCapability()
    user_id = "test_user_001"

    # 1. 摄入信息（触发 Mem0 长期记忆 + STM）
    print("1️⃣ 摄入用户信息...")
    result = cap.execute({
        "action": "ingest",
        "user_id": user_id,
        "content": "我叫张三，住在北京市朝阳区，喜欢爬山和摄影。",
        "role": "user"
    })
    print("   ➤", result)
    print()

    # 2. 存储结构化记忆
    print("2️⃣ 存储键值对...")
    result = cap.execute({
        "action": "store",
        "user_id": user_id,
        "key": "favorite_hobby",
        "value": "摄影"
    })
    print("   ➤", result)
    print()

    # 3. 检索结构化记忆
    print("3️⃣ 检索键值对...")
    result = cap.execute({
        "action": "retrieve",
        "user_id": user_id,
        "key": "favorite_hobby"
    })
    print("   ➤", result)
    print()

    # 4. 语义搜索长期记忆
    print("4️⃣ 语义搜索长期记忆...")
    result = cap.execute({
        "action": "search",
        "user_id": user_id,
        "query": "用户住在哪里？"
    })
    print("   ➤", result)
    print()

    # 5. 构建 LLM 上下文
    print("5️⃣ 构建 LLM 上下文...")
    result = cap.execute({
        "action": "build_context",
        "user_id": user_id,
        "query": "介绍一下你自己"
    })
    print("   ➤ Context:\n")
    print(result.get("context", "无上下文"))
    print()

    # 6. 清空记忆（仅清临时，Mem0 不清）
    print("6️⃣ 清空临时记忆...")
    result = cap.execute({
        "action": "clear",
        "user_id": user_id
    })
    print("   ➤", result)
    print()

    # 7. 再次检索（应失败）
    print("7️⃣ 再次检索 favorite_hobby（应失败）...")
    result = cap.execute({
        "action": "retrieve",
        "user_id": user_id,
        "key": "favorite_hobby"
    })
    print("   ➤", result)
    print()

    print("✅ 测试完成！检查输出是否符合预期。")
    print("\n💡 注意：Mem0 的长期记忆不会被 'clear' 删除，如需清除需调用 mem0.delete_all(user_id)")


if __name__ == "__main__":
    main()