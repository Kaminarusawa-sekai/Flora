# optimization/engine.py
import optuna

from optuna.samplers import TPESampler, CmaEsSampler, RandomSampler
from optuna.pruners import MedianPruner
from typing import Dict, Any, List, Optional
import httpx
import asyncio
import logging
from config import settings
from .schemas import OptimizationConfig, StrategyParams, FeedbackData
import dashscope
from dashscope import Generation
import json5
import json



logger = logging.getLogger(__name__)


def get_default_strategy(level: str) -> Dict[str, Any]:
        """返回默认策略，防止 Qwen 失效"""
        return {
        "exploration_level": level,
        "strategy_reason": "Using default strategy due to Qwen API failure.",
        "parameter_suggestions": {
        "float": {"range": "normal", "example_low": 0.1, "example_high": 0.9},
        "int": {"range": "normal"},
        "categorical": {"focus": "all"}
        }
        }

class OptimizationEngine:
    def __init__(self):
        self.active_studies: Dict[str, optuna.Study] = {}
        self.study_configs: Dict[str, OptimizationConfig] = {}
        self.feedback_data: Dict[str, List[FeedbackData]] = {}



    # 在文件顶部添加

    # --- 新增: Qwen 决策函数 ---
    async def get_exploration_strategy_qwen(
        self,
        study: optuna.Study,
        available_resources: int,
        max_resources: int,
        initial_trials_count: int,
        total_trials: int
    ) -> Dict[str, Any]:
        """
        调用 Qwen API，根据当前状态决定探索策略。
        返回一个 dict，包含每个参数的建议范围或类型 (e.g., "conservative", "balanced", "aggressive")
        """
        # 准备上下文信息
        current_progress = len(study.trials)
        best_value = study.best_value if study.best_value is not None else "unknown"
        resource_utilization = available_resources / max_resources if max_resources > 0 else 0.0
        
        # 构建 Prompt
        prompt = f"""
            你是一个智能优化系统的决策AI，负责在资源受限的情况下，动态平衡“模仿已知好策略”和“探索新策略”。
            请根据以下信息，决定本次试验的探索强度，并为每个参数指定一个探索范围。

            **系统状态:**
            - 优化研究名称: {study.study_name}
            - 优化方向: {"最大化" if study.direction == optuna.study.StudyDirection.MAXIMIZE else "最小化"}
            - 已完成试验数: {current_progress} / {total_trials}
            - 当前最佳得分: {best_value}
            - 自定义初值 (模仿) 数量: {initial_trials_count}
            - 总试验次数: {total_trials}

            **资源状态:**
            - 当前可用执行器数量: {available_resources}
            - 最大允许并发数: {max_resources}
            - 资源利用率: {resource_utilization:.2%}

            **决策要求:**
            1. 分析当前状态，判断应该偏向“模仿”(conservative)、“平衡”(balanced) 还是“激进探索”(aggressive)。
            2. 为以下参数类型返回建议的采样范围或策略。你的输出必须是严格的 JSON 格式。
            3. 输出格式:
            ```json
            {{
            "exploration_level": "conservative|balanced|aggressive",
            "strategy_reason": "你的分析理由，1-2句话",
            "parameter_suggestions": {{
                "float": {{
                "range": "narrow|normal|wide",
                "example_low": 0.1,
                "example_high": 0.9
                }},
                "int": {{
                "range": "narrow|normal|wide"
                }},
                "categorical": {{
                "focus": "subset|all",
                "example_subset": ["option1", "option2"]
                }}
            }}
            }}
            """
        #注意:

        #"narrow" 范围表示模仿，接近已知好策略。
        #"wide" 范围表示探索，尝试极端值。
        #"subset" 表示只探索部分高潜力类别。
        #"all" 表示探索所有类别。
        #请确保 JSON 有效且可被 Python json.loads() 解析。
        try:
            # 调用 Qwen API
            response = Generation.call(
            model=settings.QWEN_MODEL,
            api_key=settings.QWEN_API_KEY,
            prompt=prompt,
            temperature=0.3,  # 降低随机性，保证决策稳定
            top_p=0.8,
            result_format='message'  # 返回 message 格式
            )
            if response.status_code == 200:
                # 提取模型返回的内容
                content = response.output.choices[0].message.content.strip()
                logger.info(f"Qwen raw response: {content}")
                
                # 尝试提取 JSON (有时模型会在文本中包含 JSON)
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start != -1 and json_end != -1:
                    json_str = content[json_start:json_end]
                    try:
                        decision = json5.loads(json_str)
                        return decision
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse Qwen JSON: {e}")
                        # 如果解析失败，返回默认保守策略
                        return get_default_strategy("conservative")
                else:
                    logger.error("No JSON found in Qwen response.")
                    return get_default_strategy("conservative")
            else:
                logger.error(f"Qwen API call failed: {response.code}, {response.message}")
                return get_default_strategy("balanced")  # API 失败时使用平衡策略
        except Exception as e:
            logger.error(f"Exception during Qwen API call: {e}")
            return get_default_strategy("balanced")
    

    async def create_study(self, config: OptimizationConfig):
        """创建一个新的优化研究"""
        study_name = config.study_name
        
        if study_name in self.active_studies:
            raise ValueError(f"Study {study_name} already exists.")
        
        # 1. 创建 Sampler
        sampler_map = {
            "tpe": TPESampler(),
            "cmaes": CmaEsSampler(),
            "random": RandomSampler()
        }
        sampler = sampler_map.get(config.sampler, TPESampler())
        
        # 2. 创建 Study
        study = optuna.create_study(
            study_name=study_name,
            direction=config.direction,
            sampler=sampler,
            pruner=MedianPruner(n_startup_trials=3, n_warmup_steps=5)
        )
        
        # 3. 添加自定义初值 (模仿)
        for initial_params in config.initial_trials:
            try:
                study.enqueue_trial(initial_params)
                logger.info(f"Enqueued initial trial for study {study_name}: {initial_params}")
            except Exception as e:
                logger.warning(f"Failed to enqueue initial trial {initial_params}: {e}")
        
        # 4. 保存
        self.active_studies[study_name] = study
        self.study_configs[study_name] = config
        self.feedback_data[study_name] = []
        
        logger.info(f"Created study: {study_name} with {len(config.initial_trials)} initial trials.")
        
        return study

    async def run_optimization(self, study_name: str):
        """运行优化循环"""
        if study_name not in self.active_studies:
            raise ValueError(f"Study {study_name} not found.")
        
        study = self.active_studies[study_name]
        config = self.study_configs[study_name]
        
        async def objective(trial: optuna.Trial) -> float:
            # === 1. 资源平衡算法 ===
            # if config.use_resource_balancing and config.resource_check_url:
            #     try:
            #         async with httpx.AsyncClient() as client:
            #             response = await client.get(config.resource_check_url)
            #             response.raise_for_status()
            #             resource_data = response.json()
            #             available_executors = resource_data.get("available", 0)
            #             max_allowed = settings.MAX_CONCURRENT_EXECUTIONS
            #             if available_executors < max_allowed * 0.3:  # 少于30%资源
            #                 logger.warning(f"Low resources ({available_executors}), using conservative params.")
            #                 # 这里可以动态调整 suggest 的范围，示例简化为记录
            #                 pass
            #     except Exception as e:
            #         logger.error(f"Failed to check resources: {e}")
            if config.use_resource_balancing and config.resource_check_url:
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(config.resource_check_url)
                        response.raise_for_status()
                        resource_data = response.json()
                        available_executors = resource_data.get("available", 0)
                        max_allowed = settings.MAX_CONCURRENT_EXECUTIONS
                            # 调用 Qwen 获取智能决策
                        qwen_decision = await self.get_exploration_strategy_qwen(
                            study=study,
                            available_resources=available_executors,
                            max_resources=max_allowed,
                            initial_trials_count=len(config.initial_trials),
                            total_trials=config.n_trials
                        )
                    
                    exploration_level = qwen_decision["exploration_level"]
                    strategy_reason = qwen_decision["strategy_reason"]
                    param_suggestions = qwen_decision["parameter_suggestions"]
                    
                    logger.info(f"Qwen Decision: {exploration_level.upper()} - {strategy_reason}")
                    
                except Exception as e:
                    logger.error(f"Failed in Qwen-driven resource balancing: {e}")
                    # 失败时使用默认平衡策略
                    qwen_decision = get_default_strategy("balanced")
                    param_suggestions = qwen_decision["parameter_suggestions"]
            else:
                # 如果未启用资源平衡，使用默认平衡策略
                qwen_decision = get_default_strategy("balanced")
                param_suggestions = qwen_decision["parameter_suggestions"]

            #=== 2. 根据 Qwen 的建议动态构建参数 ===
            params = {}
            for param_name, param_def in config.search_space.items():
                if param_def.type == "float":
                    # 根据 Qwen 建议的范围调整采样
                    if param_suggestions["float"]["range"] == "narrow" and study.best_trial:
                    # 模仿: 在当前最佳值附近窄范围搜索
                        center = study.best_trial.params.get(param_name, (param_def.low + param_def.high) / 2)
                        margin = (param_def.high - param_def.low) * 0.1  # 10% 范围
                        low = max(param_def.low, center - margin)
                        high = min(param_def.high, center + margin)
                    elif param_suggestions["float"]["range"] == "wide":
                        # 激进探索: 使用全范围
                        low, high = param_def.low, param_def.high
                    else:  # normal
                        low, high = param_def.low, param_def.high
                        params[param_name] = trial.suggest_float(param_name, low, high, step=param_def.step)
                elif param_def.type == "int":
                    if param_suggestions["int"]["range"] == "narrow" and study.best_trial:
                        center = study.best_trial.params.get(param_name, (param_def.low + param_def.high) // 2)
                        margin = int((param_def.high - param_def.low) * 0.1)
                        low = max(int(param_def.low), center - margin)
                        high = min(int(param_def.high), center + margin)
                    elif param_suggestions["int"]["range"] == "wide":
                        low, high = int(param_def.low), int(param_def.high)
                    else:
                        low, high = int(param_def.low), int(param_def.high)
                    params[param_name] = trial.suggest_int(param_name, low, high, step=int(param_def.step) if param_def.step else 1)
                    
                elif param_def.type == "categorical":
                    choices = param_def.choices
                    if param_suggestions["categorical"]["focus"] == "subset" and study.best_trial:
                        # 探索与当前最佳策略相似的子集
                        # 简化: 取前几个选项，或根据领域知识
                        subset_size = max(2, len(choices) // 2)
                        effective_choices = choices[:subset_size]
                    else:  # "all"
                        effective_choices = choices
                    params[param_name] = trial.suggest_categorical(param_name, effective_choices)
            # === 2. 从配置中构建参数空间并采样 ===
            # params = {}
            # for param_name, param_def in config.search_space.items():
            #     if param_def.type == "float":
            #         params[param_name] = trial.suggest_float(
            #             param_name, param_def.low, param_def.high, step=param_def.step
            #         )
            #     elif param_def.type == "int":
            #         params[param_name] = trial.suggest_int(
            #             param_name, int(param_def.low), int(param_def.high), step=int(param_def.step) if param_def.step else 1
            #         )
            #     elif param_def.type == "categorical":
            #         params[param_name] = trial.suggest_categorical(param_name, param_def.choices)
            
            # logger.info(f"[{study_name}] Trial {trial.number} suggested params: {params}")
            
            # === 3. 调用自定义执行 (HTTP POST) ===
            strategy_payload = StrategyParams(
                params=params,
                trial_number=trial.number,
                study_name=study_name
            ).dict()
            
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    # 假设你的执行器有一个 /execute 端点
                    response = await client.post(
                        f"{settings.EXECUTOR_BASE_URL}/execute",
                        json=strategy_payload
                    )
                    response.raise_for_status()
                    execution_id = response.json().get("execution_id")
                    logger.info(f"Started execution for trial {trial.number}, ID: {execution_id}")
            except Exception as e:
                logger.error(f"Failed to start execution for trial {trial.number}: {e}")
                # 可以返回一个极差分数或重试
                return -1e6
            
            # === 4. 等待 & 定期调用反馈感知 (轮询) ===
            feedback_url = f"{settings.EXECUTOR_BASE_URL}/feedback/{execution_id}"
            max_wait_time = 3600  # 最大等待1小时
            check_interval = 60   # 每60秒检查一次
            start_time = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - start_time) < max_wait_time:
                await asyncio.sleep(check_interval)
                
                try:
                    async with httpx.AsyncClient() as client:
                        resp = await client.get(feedback_url)
                        resp.raise_for_status()
                        feedback = resp.json()
                        
                        # 记录反馈 (可用于分析或早停)
                        fb_data = FeedbackData(
                            trial_number=trial.number,
                            study_name=study_name,
                            metric_name="current_performance",
                            value=feedback.get("score", 0.0)
                        )
                        self.feedback_data[study_name].append(fb_data)
                        
                        logger.info(f"Trial {trial.number} feedback: {feedback}")
                        
                        # --- 早停 (Pruning) ---
                        if trial.should_prune():
                            current_score = feedback.get("score", 0.0)
                            # 示例：如果当前得分低于某个阈值，提前终止
                            if current_score < 100:
                                logger.info(f"Trial {trial.number} pruned due to low performance.")
                                raise optuna.TrialPruned()
                        
                        # 检查执行是否完成
                        if feedback.get("status") == "completed":
                            final_score = feedback.get("final_score", current_score)
                            logger.info(f"Trial {trial.number} completed. Final score: {final_score}")
                            return final_score
                            
                except Exception as e:
                    logger.warning(f"Error fetching feedback for trial {trial.number}: {e}")
                    # 可能还在运行，继续等待
            
            # 超时未完成
            logger.warning(f"Trial {trial.number} timed out.")
            return -1e6  # 超时返回极差分数
        
        # === 5. 开始优化 ===
        logger.info(f"Starting optimization for study {study_name}, {config.n_trials} trials.")
        try:
            study.optimize(objective, n_trials=config.n_trials, n_jobs=1)
            logger.info(f"Optimization for {study_name} completed.")
        except Exception as e:
            logger.error(f"Optimization for {study_name} failed: {e}")
            raise

    async def get_status(self, study_name: str) -> dict:
        """获取研究状态"""
        if study_name not in self.active_studies:
            return {"error": "Study not found"}
        
        study = self.active_studies[study_name]
        best_trial = study.best_trial if study.best_trial else None
        
        return {
            "study_name": study_name,
            "status": "completed" if study.trials else "running", # 简化
            "n_trials": len(study.trials),
            "best_value": best_trial.value if best_trial else None,
            "best_params": best_trial.params if best_trial else None
        }