# actors/orchestrator.py
from thespian.actors import Actor


class BatchResult:
    def __init__(self, results):
        self.results = results  # list of {"trial_number": int, "script": str}

class OptimizationOrchestrator(Actor):
    def receiveMessage(self, msg, sender):
        if msg.get("type") == "run_batch":
            instructions = msg["instructions"]  # list of str
            trial_numbers = msg["trial_numbers"]
            
            self.total = len(instructions)
            self.results = []
            self.sender = sender
            
            if self.total == 0:
                self.send(sender, BatchResult([]))
                return
                
            for inst, tnum in zip(instructions, trial_numbers):
                worker = self.createActor(VideoWorker)
                self.send(worker, {
                    "trial_number": tnum,
                    "instruction": inst,
                    "report_to": self.myAddress
                })
    
    def receiveMessage(self, msg, sender):
        if isinstance(msg, dict) and msg.get("trial_result"):
            self.results.append({
                "trial_number": msg["trial_number"],
                "script": msg["script"]
            })
            if len(self.results) == self.total:
                self.send(self.sender, BatchResult(self.results))

async def main():
    # 用户输入（任意任务）
    user_goal = input("🎯 请输入你的优化目标（例如：'生成更好的抖音脚本' 或 '提高客服回复满意度'）:\n> ").strip()
    
    orchestrator_llm = LLMOrchestrator(user_goal)
    
    # Step 1: LLM 自动发现优化维度
    print("\n🔍 正在分析任务并定义优化空间...")
    schema = await orchestrator_llm.discover_schema()
    print(f"✅ 发现 {len(schema['dimensions'])} 个优化维度: {[d['name'] for d in schema['dimensions']]}")

    # Step 2: 创建 Optuna study（在 [-1,1]^D 空间采样）
    study = optuna.create_study(direction="maximize")
    asys = ActorSystem('multiprocTCPBase')
    actor_orchestrator = asys.createActor("actors.orchestrator.OptimizationOrchestrator")

    for round_idx in range(OPTIMIZATION_ROUNDS):
        print(f"\n{'='*60}")
        print(f"ROUND {round_idx + 1}/{OPTIMIZATION_ROUNDS}")
        print('='*60)

        # 批量 ask
        trials = []
        instructions = []
        trial_numbers = []

        for _ in range(MAX_CONCURRENT):
            trial = study.ask()
            # 采样 D 维向量（Optuna 建议）
            vector = [trial.suggest_float(f"x{i}", -1.0, 1.0) for i in range(VECTOR_DIM)]
            
            # LLM: 向量 → 指令
            inst = await orchestrator_llm.vector_to_instruction(vector)
            
            trials.append(trial)
            instructions.append(inst)
            trial_numbers.append(trial.number)
            print(f"[Trial {trial.number}] 指令: {inst}")

        # 发送给 Actor 执行
        result_promise = asys.ask(
            actor_orchestrator,
            {
                "type": "run_batch",
                "instructions": instructions,
                "trial_numbers": trial_numbers
            },
            timeout=300
        )

        scores = []
        if hasattr(result_promise, 'results'):
            for item in result_promise.results:
                # LLM: 输出 → 分数
                eval_result = await orchestrator_llm.output_to_score(item["output"])
                scores.append(eval_result["score"])
                print(f"\n[Score: {eval_result['score']:.3f}] 反馈: {eval_result['feedback']}")
                # 补全历史中的 instruction
                orchestrator_llm.history[-1]["instruction"] = next(
                    inst for inst, tnum in zip(instructions, trial_numbers) if tnum == item["trial_number"]
                )
        else:
            scores = [0.0] * len(trials)

        # 告诉 Optuna
        for trial, score in zip(trials, scores):
            study.tell(trial, score)

        print(f"\n📈 当前最佳分数: {study.best_value:.3f}")

    asys.shutdown()
    print(f"\n🎉 优化完成！最终最佳分数: {study.best_value:.3f}")