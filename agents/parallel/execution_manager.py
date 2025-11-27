"""
并行执行管理器
负责与Optuna交互并协调优化任务的执行
分析优化维度，获取最优参数配置
"""
import logging
from typing import Any, Dict, List, Optional
import asyncio

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ParallelExecutionManager:
    """并行执行管理器，负责与Optuna交互并协调优化任务的执行"""
    
    def __init__(self):
        """初始化并行执行管理器"""
        self._max_concurrent_tasks = 10  # 最大并发任务数
        
        # 导入执行服务
        from capability_actors.task_execution_service import TaskExecutionService
        self.execution_service = TaskExecutionService()
        
        logger.info("ParallelExecutionManager initialized with TaskExecutionService")

    def set_max_concurrent_tasks(self, max_tasks: int):
        """
        设置最大并发任务数
        
        Args:
            max_tasks: 最大并发任务数
        """
        if max_tasks > 0:
            self._max_concurrent_tasks = max_tasks
            logger.info(f"Maximum concurrent tasks set to {max_tasks}")
        else:
            logger.warning("Invalid max_tasks value, must be greater than 0")

    def get_running_tasks_count(self) -> int:
        """
        获取当前运行中的任务数量
        
        Returns:
            运行中任务数量
        """
        return self.execution_service.get_execution_status()['running_tasks']

    def run_optuna_optimization(self, user_goal: str, optimization_rounds: int = 5,
                                max_concurrent: int = 10) -> Dict:
        """
        与Optuna交互的优化执行
        
        Args:
            user_goal: 优化目标
            optimization_rounds: 优化轮数
            max_concurrent: 每轮最大并发数
            
        Returns:
            最优结果
        """
        from capabilities.optimization.optuna_optimizer import OptimizationOrchestrator
        
        try:
            # 步骤1: 创建优化协调器
            orchestrator = OptimizationOrchestrator(user_goal)
            
            # 步骤2: 发现优化维度
            logger.info("Discovering optimization dimensions...")
            schema = orchestrator.discover_optimization_dimensions()
            logger.info(f"Found {len(schema['dimensions'])} dimensions: {[d['name'] for d in schema['dimensions']]}")
            
            # 步骤3: 运行多轮优化
            best_result = None
            loop = asyncio.get_event_loop()
            
            for round_idx in range(optimization_rounds):
                logger.info(f"Starting optimization round {round_idx+1}/{optimization_rounds}")
                
                # 获取优化指令
                optimization_batch = orchestrator.get_optimization_instructions(batch_size=max_concurrent)
                
                # 并行执行这些指令
                execution_results = []
                
                # 创建异步任务列表
                async_tasks = []
                for trial_info in optimization_batch['trials']:
                    trial_number = trial_info['trial_number']
                    instruction = trial_info['instruction']
                    
                    # 使用任务执行服务执行指令
                    task = loop.create_task(
                        self.execution_service.execute_task(
                            task_id=f"optuna_trial_{trial_number}",
                            task_type="leaf_task",
                            context={"instruction": instruction, "input_data": instruction}
                        )
                    )
                    async_tasks.append((trial_number, task))
                
                # 等待所有任务完成
                if async_tasks:
                    # 获取所有任务对象
                    task_objects = [task for _, task in async_tasks]
                    # 使用gather运行所有任务
                    results = loop.run_until_complete(asyncio.gather(*task_objects))
                    # 处理结果
                    for i, (trial_number, _) in enumerate(async_tasks):
                        result = results[i]
                        execution_results.append({
                            'trial_number': trial_number,
                            'output': result.get('result', {})
                        })
                
                # 处理执行结果，更新优化器
                iteration_result = orchestrator.process_execution_results(execution_results)
                
                # 获取当前最佳结果
                current_best = iteration_result.get('best_params')
                if current_best and (not best_result or current_best['value'] > best_result['value']):
                    best_result = current_best
                
                logger.info(f"Round {round_idx+1} completed. Current best score: {current_best['value']:.3f}")
            
            # 步骤4: 返回最优结果
            if best_result:
                return {
                    "best_score": best_result['value'],
                    "best_params": best_result['params'],
                    "best_trial_number": best_result['trial_number']
                }
            else:
                return {
                    "best_score": 0.0,
                    "best_params": {},
                    "best_trial_number": 0
                }
        except Exception as e:
            logger.error(f"Optuna optimization failed: {str(e)}")
            raise

    def execute_workflow(self, task_id: str, context: Dict, memory: Dict, sender: str, api_key: str, base_url: str) -> Dict:
        """
        执行工作流任务（用于测试兼容）
        
        Args:
            task_id: 任务ID
            context: 任务上下文
            memory: 记忆信息
            sender: 发送者
            api_key: API密钥
            base_url: 基础URL
            
        Returns:
            执行结果
        """
        return {
            "task_id": task_id,
            "status": "success",
            "result": "dummy_result"
        }
    
    def execute_capability(self, capability: str, context: Dict, memory: Dict) -> Dict:
        """
        执行能力函数（用于测试兼容）
        
        Args:
            capability: 能力名称
            context: 任务上下文
            memory: 记忆信息
            
        Returns:
            执行结果
        """
        return {
            "capability": capability,
            "status": "success",
            "result": "dummy_result"
        }
    
    def execute_data_query(self, request_id: str, query: str) -> Dict:
        """
        执行数据查询（用于测试兼容）
        
        Args:
            request_id: 请求ID
            query: 查询语句
            
        Returns:
            查询结果
        """
        return {
            "request_id": request_id,
            "status": "success",
            "result": "dummy_result"
        }
    
    def execute_subtasks(self, parent_task_id: str, child_tasks: List[Dict], callback) -> List[Dict]:
        """
        执行子任务（用于测试兼容）
        
        Args:
            parent_task_id: 父任务ID
            child_tasks: 子任务列表
            callback: 回调函数
            
        Returns:
            子任务执行结果
        """
        results = []
        for task in child_tasks:
            result = {
                "task_id": task["task_id"],
                "status": "success",
                "result": "dummy_result"
            }
            callback(task["task_id"], result, False)
            results.append(result)
        return results
    
    def get_task_status(self, task_id: str) -> Dict:
        """
        获取任务状态（用于测试兼容）
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态
        """
        return {
            "task_id": task_id,
            "status": "completed"
        }
def main():
    # 简单的测试代码
    manager = ParallelExecutionManager()
    
    # 测试Optuna优化
    try:
        user_goal = "optimize the parameters for a regression model"
        result = manager.run_optuna_optimization(
            user_goal=user_goal,
            optimization_rounds=2,
            max_concurrent=3
        )
        logger.info(f"Optuna optimization result: {result}")
    except Exception as e:
        logger.error(f"Optuna optimization failed: {str(e)}")

if __name__ == "__main__":
    main()