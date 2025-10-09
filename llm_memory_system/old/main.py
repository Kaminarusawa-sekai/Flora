# main.py
import os
from memory.manager import UnifiedMemoryManager

# 设置你的DashScope API Key
os.environ["DASHSCOPE_API_KEY"] = "your_actual_api_key_here"

def main():
    mm = UnifiedMemoryManager("user_001")

    print("--- 模拟对话与记忆存储 ---")
    mm.ingest("我叫张三，我喜欢编程和读书", role="user")
    mm.ingest("你好，张三！我可以帮你记录信息或回答问题。", role="assistant")
    mm.ingest("《哈利·波特》是J.K.罗琳写的", role="user")
    mm.ingest("昨天我和朋友去爬山了", role="user")
    mm.ingest("我想知道怎么合并GitHub分支", role="user")

    print("\n--- 构建上下文 (查询: 合并分支) ---")
    context = mm.build_context_for_llm("合并GitHub分支的步骤")
    print(context)

    print("\n--- 工作状态 ---")
    mm.set_temp_variable("form_step", 2)
    print("Current form step:", mm.get_temp_variable("form_step"))

    print("\n--- STM 快照 ---")
    snap = mm.take_snapshot()
    print({k: v for k, v in snap.items() if k != "history"}) # 隐藏历史以简化输出

if __name__ == "__main__":
    main()



