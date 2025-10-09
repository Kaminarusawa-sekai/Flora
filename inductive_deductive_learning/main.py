# main.py
import uuid
from datetime import datetime
from database import init_db, save_execution_result
from context_builder import ContextBuilder
from policy_engine import PolicyEngine
from reward_calculator import compute_reward
from models import ExecutionResult, OptimizationEpisode
from qwen_client import call_qwen
import json

def run_optimization_cycle(current_result: dict):
    # 1. 保存执行结果
    save_execution_result(current_result)

    # 2. 构建上下文
    builder = ContextBuilder()
    state = builder.build_state(current_result)

    # 3. 增强状态（Qwen 语义摘要）
    summary_prompt = f"请用一句话总结以下问题：{state['current']}"
    state["context_summary"] = call_qwen(summary_prompt)

    # 4. 策略选择
    policy_engine = PolicyEngine()
    action = policy_engine.select_action(state)

    # 5. 记录 episode（模拟应用动作后的结果）
    episode = OptimizationEpisode(
        episode_id=f"ep-{uuid.uuid4().hex[:8]}",
        task_id=current_result["task_id"],
        state_before=state,
        action_taken=action,
        applied_by="auto",
        timestamp=datetime.utcnow().isoformat()
    )

    # 6. 模拟 reward（需传入上一次结果）
    # reward = compute_reward(prev_result, current_result)
    # episode.reward = reward

    # 7. 保存 episode（可扩展为写入数据库）
    print(json.dumps(episode.dict(), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    init_db()

    # 模拟输入
    current_result = {
        "task_id": "sales_report_daily",
        "run_id": "20250918-001",
        "timestamp": "2025-09-18T08:00:00Z",
        "status": "partial",
        "prompt": "生成昨日销售摘要报告...",
        "output": "销售额120万...",
        "metrics": {"duration_sec": 60, "accuracy": 0.88, "token_output": 900},
        "feedback": {"user_rating": 3, "comments": "图表不清晰"},
        "logs": ["warning: chart slow"],
        "outputs": {},
        "metadata": {}
    }

    run_optimization_cycle(current_result)