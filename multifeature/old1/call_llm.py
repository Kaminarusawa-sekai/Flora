from llm.qwen import QwenLLM
from multifeature.agent_role import AgentRole

# =================== 调用 Qwen 接口 ===================
def call_qwen(prompt: str, role: AgentRole) -> str:
    try:
        llmservice= QwenLLM()
        response = llmservice.generate(
            prompt=prompt,
        )

        return response

    except Exception as e:
        print(f"[{role.value}] Exception during Qwen call: {e}")
        return ""