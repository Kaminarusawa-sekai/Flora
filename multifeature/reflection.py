# reflection.py
def generate_reflection(metrics, recent_rule=None, conflict_rule=None):
    """使用 LLM 生成自省报告"""
    last = metrics.history[-1] if metrics.history else {'gamma': 0, 'kappa': 0}
    
    prompt = f"""
You are a self-reflective AI agent. Your recent performance:
- Learning Rate (γ): {last['gamma']:.3f}
- Conflict Index (κ): {last['kappa']:.3f}

Recent new rule: {recent_rule}
Recent conflict: {conflict_rule}

Reflect on:
1. Is your induction too aggressive or too conservative?
2. Are your predictions consistent with reality?
3. How can you improve your learning strategy?

Output a 3-sentence self-improvement plan.
"""
    # 模拟输出（实际可调用 Qwen）
    print("🔍 Self-Reflection Prompt:")
    print(prompt)
    print("\n🤖 AI Self-Reflection:")
    print("My learning rate is moderate but conflicts are rising. "
          "I may be overgeneralizing from limited data. "
          "I should increase verification before adding new rules.")