# test_memory_manager.py

import os
import time
from datetime import datetime
from typing import List

# === 假设你的模块路径如下，请根据实际调整 ===
from capabilities.llm_memory.manager import UnifiedMemoryManager
from external.memory_store.memory_repos import (
    build_procedural_repo,
    build_resource_repo,
    build_vault_repo
)
# ==============================================
from mem0 import Memory
from config import MEM0_CONFIG
SHARED_MEM0_CLIENT = Memory.from_config(MEM0_CONFIG)

def main():
    print("🚀 开始测试 UnifiedMemoryManager 多用户功能...\n")


    mem0_client = SHARED_MEM0_CLIENT
    print(f"Mem0 Client Type: {type(mem0_client)}")
    
    print("🔍 正在检测 Mem0 多用户兼容性...")
    if not check_mem0_user_isolation(mem0_client):
        print("🛑 终止测试：Mem0 不支持安全的多用户隔离！")
        return
    
    print("✅ Mem0 兼容性检查通过，继续测试...\n")

    # ====== 1. 创建两个用户的 MemoryManager ======
    user_a = "user_alice"
    user_b = "user_bob"

    print(f"🔧 初始化用户 {user_a} 和 {user_b} 的记忆管理器...")
    manager_a = UnifiedMemoryManager(
        user_id=user_a,
        vault_repo=build_vault_repo(),
        procedural_repo=build_procedural_repo(),
        resource_repo=build_resource_repo(),
    )

    manager_b = UnifiedMemoryManager(
        user_id=user_b,
        vault_repo=build_vault_repo(),
        procedural_repo=build_procedural_repo(),
        resource_repo=build_resource_repo(),
    )

    # ====== 2. 用户 A 添加智能记忆 ======
    print(f"\n📝 用户 {user_a} 添加记忆: '我是前端工程师，喜欢用 React。我的 GitHub token 是 ghp_abc123xyz。'")
    manager_a.add_memory_intelligently("我是前端工程师，喜欢用 React。我的 GitHub token 是 ghp_abc123xyz。")
    time.sleep(1)  # 避免 Mem0 写入延迟影响检索

    # ====== 3. 用户 B 添加不同记忆 ======
    print(f"\n📝 用户 {user_b} 添加记忆: '我是数据科学家，常用 Python 和 pandas。'")
    manager_b.add_memory_intelligently("我是数据科学家，常用 Python 和 pandas。")
    time.sleep(1)

    # ====== 4. 验证核心记忆隔离 ======
    print(f"\n🔍 检查用户 {user_a} 的核心记忆:")
    core_a = manager_a.get_core_memory()
    print(f"  → {core_a}")

    print(f"\n🔍 检查用户 {user_b} 的核心记忆:")
    core_b = manager_b.get_core_memory()
    print(f"  → {core_b}")

    assert "前端" in core_a, "用户A的核心记忆应包含'前端'"
    assert "数据科学家" in core_b, "用户B的核心记忆应包含'数据科学家'"
    assert "前端" not in core_b, "用户B不应看到用户A的记忆！"
    print("✅ 核心记忆隔离验证通过！")

    # ====== 5. 测试 Vault 安全存储 ======
    print(f"\n🔐 用户 {user_a} 手动添加凭据到 Vault...")
    manager_a.add_vault_memory(
        category="github",
        key_name="token",
        value="ghp_REAL_SECRET_789"
    )

    print(f"  查看用户 {user_a} 的 Vault（脱敏前）:")
    raw_vault = manager_a.get_vault_memory()
    print(f"  → {raw_vault}")

    # ====== 6. 构建执行上下文（含敏感信息） ======
    print(f"\n🛠️ 为用户 {user_a} 构建执行上下文（包含敏感信息）...")
    exec_ctx_with_vault = manager_a.build_execution_context(
        task_description="使用 GitHub API 提交代码",
        include_sensitive=True
    )
    print(f"  执行上下文:\n{exec_ctx_with_vault}\n")

    # 验证敏感信息被脱敏
    assert "[REDACTED]" in exec_ctx_with_vault, "Vault 内容应被脱敏为 [REDACTED]"
    assert "ghp_REAL_SECRET_789" not in exec_ctx_with_vault, "原始 token 不应泄露！"
    print("✅ Vault 脱敏验证通过！")

    # ====== 7. 构建对话上下文 ======
    manager_a.stm.add_message("我想部署一个 React 应用")
    conv_ctx = manager_a.build_conversation_context("如何部署 React？")
    print(f"\n💬 用户 {user_a} 的对话上下文:\n{conv_ctx}\n")

    # ====== 8. 构建规划上下文 ======
    plan_ctx = manager_a.build_planning_context("部署 React 应用到 Vercel")
    print(f"\n🧩 用户 {user_a} 的规划上下文:\n{plan_ctx}\n")

    # ====== 9. 验证用户 B 看不到 A 的 Vault ======
    vault_b = manager_b.get_vault_memory()
    print(f"\n👀 用户 {user_b} 的 Vault 内容: '{vault_b}' (应为空)")
    assert vault_b == "", "用户B不应看到用户A的凭据！"
    print("✅ Vault 隔离验证通过！")

    print("\n🎉 所有测试通过！UnifiedMemoryManager 支持安全的多用户记忆管理。")



# check_mem0_compatibility.py

import uuid
import time
from typing import Any, Dict

def check_mem0_user_isolation(mem0_client: Any) -> bool:
    """
    检测 Mem0 是否支持 user_id 隔离。
    
    返回 True 表示兼容，False 表示存在风险（可能串号）。
    
    使用方式：
        from your_project.clients import get_shared_mem0_client
        client = get_shared_mem0_client()
        if not check_mem0_user_isolation(client):
            raise RuntimeError("Mem0 不支持 user_id 隔离！请升级或检查配置。")
    """
    # 生成唯一测试用户 ID（避免污染真实数据）
    test_user_a = f"test_user_{uuid.uuid4().hex[:8]}"
    test_user_b = f"test_user_{uuid.uuid4().hex[:8]}"
    test_content = "This is a secret memory for compatibility test."

    try:
        print(f"[Mem0 Compatibility] 正在测试 user_id 隔离能力...")
        print(f"  - 用户 A: {test_user_a}")
        print(f"  - 用户 B: {test_user_b}")

        # Step 1: 向用户 A 写入记忆
        print(f"  → 向 {test_user_a} 写入记忆...")
        mem0_client.add(
            test_content,
            user_id=test_user_a,
            metadata={"type": "compatibility_test", "timestamp": str(time.time())}
        )
        time.sleep(1)  # 等待索引（部分后端需要）

        # Step 2: 用户 A 搜索，应能查到
        print(f"  → 用户 {test_user_a} 执行搜索...")
        # Step 2: 用户 A 搜索，应能查到
        results_a = mem0_client.search(
            query="secret memory",
            user_id=test_user_a,
            filters={"type": "compatibility_test"},
            limit=5
        )
        has_a = len(results_a.get("results", [])) > 0
        print(f"    ↳ 用户 A 结果数量: {len(results_a.get('results', []))} | 有结果: {has_a}")

        if not has_a:
            print("  ❌ 失败：用户 A 无法检索自己写入的记忆！")
            return False

        # Step 3: 用户 B 搜索，应查不到
        results_b = mem0_client.search(
            query="secret memory",
            user_id=test_user_b,
            filters={"type": "compatibility_test"},
            limit=5
        )
        has_b = len(results_b.get("results", [])) > 0
        print(f"    ↳ 用户 B 结果数量: {len(results_b.get('results', []))} | 泄露: {has_b}")

        if has_b:
            print("  ❌ 严重错误：用户 B 看到了用户 A 的记忆！")
            return False
        # Step 4: 尝试不传 user_id 搜索（应失败或返回空）
        print(f"  → 尝试不传 user_id 搜索（应无结果）...")
        try:
            results_no_user = mem0_client.search(
                query="secret memory",
                # user_id 未传！
                filters={"type": "compatibility_test"},
                limit=5
            )
            memories_no_user = [r.get("memory", "") for r in results_no_user.get("results", [])]
            if memories_no_user:
                print("  ⚠️ 警告：未传 user_id 也能查到数据！可能存在全局泄露风险。")
                # 可选：视为失败，或仅警告
                # return False
        except Exception as e:
            print(f"    ↳ 不传 user_id 时报错（正常）: {type(e).__name__}")

        print("  ✅ Mem0 user_id 隔离测试通过！")
        return True

    except Exception as e:
        print(f"  ❌ Mem0 兼容性检测异常: {e}")
        return False

    finally:
        # 可选：清理测试数据（如果 Mem0 支持 delete by user_id）
        try:
            if hasattr(mem0_client, 'delete'):
                mem0_client.delete(user_id=test_user_a)
                mem0_client.delete(user_id=test_user_b)
                print("  🧹 已清理测试数据")
        except Exception:
            pass  # 忽略清理失败

if __name__ == "__main__":
    main()