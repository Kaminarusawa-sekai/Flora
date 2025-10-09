# reward_calculator.py
def compute_reward(prev_result: dict, curr_result: dict) -> float:
    w_perf = 0.3
    w_qual = 0.4
    w_user = 0.3

    prev_metrics = prev_result.get("metrics", {})
    curr_metrics = curr_result.get("metrics", {})

    delta_duration = prev_metrics.get("duration_sec", 1) - curr_metrics.get("duration_sec", 1)
    perf_reward = delta_duration / max(prev_metrics.get("duration_sec", 1), 1)

    acc_delta = curr_metrics.get("accuracy", 0) - prev_metrics.get("accuracy", 0)
    token_eff = (prev_metrics.get("token_output", 1) - curr_metrics.get("token_output", 1)) / max(prev_metrics.get("token_output", 1), 1)
    qual_reward = 0.6 * acc_delta + 0.4 * token_eff

    user_reward = 0
    if curr_result.get("feedback"):
        rating = curr_result["feedback"].get("user_rating", 3)
        user_reward = (rating - 3) / 2

    total = w_perf * perf_reward + w_qual * qual_reward + w_user * user_reward
    return max(min(total, 1.0), -1.0)