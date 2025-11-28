"""示例：展示如何使用优化后的能力注册表架构"""
from capabilities.registry import CapabilityRegistry
from capabilities.llm.interface import ILLMCapability
from capabilities.llm.qwen_adapter import QwenAdapter
from capabilities.llm_memory.interface import IMemoryCapability
from capabilities.llm_memory.memory_capability import MemoryCapability


def run_example():
    """运行示例，展示优化后的架构使用方式"""
    # 1. 获取注册表实例
    registry = CapabilityRegistry()
    
    # 2. 注册能力
    # QwenAdapter 现在需要在 __init__ 中传递 api_key，而不是 initialize 方法
    registry.register(
        capability_type="qwen",
        factory=lambda: QwenAdapter(api_key="test_key")  # 使用测试key，实际运行时会失败，仅用于演示
    )
    
    # MemoryCapability 需要在 __init__ 中传递 user_id
    registry.register(
        capability_type="core_memory",
        factory=lambda: MemoryCapability(user_id="test_user")
    )
    
    # 3. 获取能力（IDE会自动识别类型）
    print("\n=== 获取LLM能力 ===")
    try:
        llm = registry.get_capability("qwen", expected_type=ILLMCapability)
        print(f"✓ 成功获取LLM能力，类型: {type(llm).__name__}")
        print(f"✓ 支持的方法: generate, generate_chat, embedding")
    except Exception as e:
        print(f"✗ 获取LLM能力失败: {e}")
    
    print("\n=== 获取Memory能力 ===")
    try:
        memory = registry.get_capability("core_memory", expected_type=IMemoryCapability)
        print(f"✓ 成功获取Memory能力，类型: {type(memory).__name__}")
        print(f"✓ 支持的方法: add_memory_intelligently, build_conversation_context, retrieve_relevant_memory")
    except Exception as e:
        print(f"✗ 获取Memory能力失败: {e}")
    
    # 4. 演示类型安全
    print("\n=== 演示类型安全 ===")
    print("# 现在IDE会自动补全方法，例如:")
    print("# llm.generate(prompt=\"你好\")")
    print("# memory.add_memory_intelligently(content=\"测试记忆\")")
    
    print("\n=== 示例完成 ===")


if __name__ == "__main__":
    run_example()