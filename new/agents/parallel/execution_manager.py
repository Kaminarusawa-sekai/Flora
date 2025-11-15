"""
并行执行管理器
负责协调和管理任务的并行执行
支持工作流执行、能力函数执行、数据查询执行和子任务并行执行
"""
import logging
import time
from typing import Any, Dict, List, Optional, Callable
from thespian.actors import Actor, ActorSystem, ActorAddress
from thespian.troupe import troupe

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import threading

class ParallelExecutionManager:
    """并行执行管理器，负责与Optuna交互并管理多个执行actor"""
    
    def __init__(self):
        """初始化并行执行管理器"""
        self.actor_system = ActorSystem('multiprocTCPBase')
        self._running_tasks: Dict[str, ActorAddress] = {}  # task_id: actor_address
        self._task_results: Dict[str, Any] = {}  # task_id: result
        self._task_errors: Dict[str, str] = {}  # task_id: error_message
        self._callback_handlers: Dict[str, Callable] = {}  # task_id: callback
        self._max_concurrent_tasks = 10  # 最大并发任务数
        self.execution_actors = []  # 存储执行actor实例
        
        # 初始化执行actor池
        for _ in range(self._max_concurrent_tasks):
            actor = self.actor_system.createActor('new.capability_actors.execution_actor.ExecutionActor')
            self.execution_actors.append(actor)

    def execute_workflow(self, task_id: str, context: Dict, memory: Dict, 
                       sender: ActorAddress, api_key: str,
                       base_url: str) -> Dict:
        """
        并行执行工作流任务
        
        Args:
            task_id: 任务ID
            context: 任务上下文
            memory: 任务记忆
            sender: 发送者地址
            api_key: API密钥
            base_url: API基础URL
            
        Returns:
            工作流执行结果
        """
        try:
            # 检查是否有正在运行的同名任务
            if task_id in self._running_tasks:
                logger.warning(f"Task {task_id} is already running, waiting for completion...")
                result = self.actor_system.ask(self._running_tasks[task_id], None, timeout=60)
                
                # 返回已完成任务的结果
                if task_id in self._task_errors:
                    raise Exception(self._task_errors[task_id])
                return self._task_results[task_id]
            
            # 检查并发任务数限制
            if len(self._running_tasks) >= self._max_concurrent_tasks:
                logger.warning(f"Maximum concurrent tasks ({self._max_concurrent_tasks}) reached, waiting...")
                # 等待任意一个任务完成
                if self._running_tasks:
                    # 从运行的任务中随机选择一个等待
                    first_task_id = next(iter(self._running_tasks.keys()))
                    self.actor_system.ask(self._running_tasks[first_task_id], None, timeout=60)
            
            # 创建工作流Actor并发送消息
            actor = self.actor_system.createActor(WorkflowActor)
            self._running_tasks[task_id] = actor
            
            try:
                result, is_error = self.actor_system.ask(actor, (task_id, context, memory, api_key, base_url), timeout=300)
                if is_error:
                    self._task_errors[task_id] = result
                    raise Exception(result)
                
                self._task_results[task_id] = result
                return result
            except Exception as e:
                self._task_errors[task_id] = str(e)
                raise
            finally:
                if task_id in self._running_tasks:
                    self.actor_system.tell(self._running_tasks[task_id], 'quit')
                    del self._running_tasks[task_id]
                    
        except Exception as e:
            logger.error(f"Error executing workflow {task_id}: {str(e)}")
            raise

    def execute_capability(self, capability: str, context: Dict,
                               memory: Dict = None) -> Any:
        """
        并行执行能力函数
        
        Args:
            capability: 能力名称
            context: 执行上下文
            memory: 记忆数据
            
        Returns:
            能力函数执行结果
        """
        if memory is None:
            memory = {}
            
        task_id = f"capability_{capability}_{id(context)}"
        
        try:
            # 检查并发任务数限制
            if len(self._running_tasks) >= self._max_concurrent_tasks:
                logger.warning(f"Maximum concurrent tasks ({self._max_concurrent_tasks}) reached, waiting...")
                # 等待任意一个任务完成
                if self._running_tasks:
                    first_task_id = next(iter(self._running_tasks.keys()))
                    self.actor_system.ask(self._running_tasks[first_task_id], None, timeout=60)
            
            # 创建能力执行Actor并发送消息
            actor = self.actor_system.createActor(CapabilityActor)
            self._running_tasks[task_id] = actor
            
            try:
                result, is_error = self.actor_system.ask(actor, (capability, context, memory), timeout=300)
                if is_error:
                    self._task_errors[task_id] = result
                    raise Exception(result)
                
                self._task_results[task_id] = result
                return result
            except Exception as e:
                self._task_errors[task_id] = str(e)
                raise
            finally:
                if task_id in self._running_tasks:
                    self.actor_system.tell(self._running_tasks[task_id], 'quit')
                    del self._running_tasks[task_id]
                    
        except Exception as e:
            logger.error(f"Error executing capability {capability}: {str(e)}")
            raise

    def execute_data_query(self, request_id: str, query: str) -> Dict:
        """
        执行数据查询（非并行）
        
        Args:
            request_id: 请求ID
            query: 查询语句
            
        Returns:
            查询结果
        """
        try:
            logger.info(f"Executing data query {request_id}: {query}")
            
            # 直接调用DataActor执行查询（非并行）
            from new.capability_actors.data_actor import DataActor
            data_actor = self.actor_system.createActor(DataActor)
            result = self.actor_system.ask(data_actor, (request_id, query), timeout=300)
            
            self._task_results[request_id] = result
            return result
        except Exception as e:
            logger.error(f"Error executing data query {request_id}: {str(e)}")
            self._task_errors[request_id] = str(e)
            raise

    def execute_subtasks(self, parent_task_id: str, child_tasks: List[Dict],
                              callback: Callable) -> Dict:
        """
        并行执行子任务
        
        Args:
            parent_task_id: 父任务ID
            child_tasks: 子任务列表
            callback: 任务完成回调函数
            
        Returns:
            所有子任务的执行结果
        """
        # 保存回调函数
        self._callback_handlers[parent_task_id] = callback
        
        # 并行执行所有子任务
        results = {}
        
        for i, child_task in enumerate(child_tasks):
            task_id = child_task["task_id"]
            agent_id = child_task["agent_id"]
            context = child_task["context"]
            capability = child_task.get("capability")
            
            # 使用执行actor执行任务
            actor = self.execution_actors[i % len(self.execution_actors)]
            
            # 创建任务消息
            task_msg = {
                "type": "leaf_task",
                "task_id": task_id,
                "context": context,
                "memory": {},
                "capability": capability,
                "agent_id": agent_id
            }
            
            try:
                result = self.actor_system.ask(actor, task_msg, timeout=300)
                results[task_id] = result
                if callback:
                    callback(task_id, result, False)
                self._task_results[task_id] = result
            except Exception as e:
                error_msg = str(e)
                results[task_id] = error_msg
                if callback:
                    callback(task_id, error_msg, True)
                self._task_errors[task_id] = error_msg
        
        # 清理回调
        if parent_task_id in self._callback_handlers:
            del self._callback_handlers[parent_task_id]
        
        return results

    def cancel_task(self, task_id: str) -> bool:
        """
        取消指定任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            取消是否成功
        """
        if task_id in self._running_tasks:
            actor = self._running_tasks[task_id]
            self.actor_system.tell(actor, 'quit')
            del self._running_tasks[task_id]  # 立即移除，因为已发送停止消息
            logger.info(f"Task {task_id} cancelled")
            return True
        return False

    def get_task_status(self, task_id: str) -> Dict:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态信息
        """
        if task_id in self._running_tasks:
            return {
                "status": "running",
                "task_id": task_id
            }
        elif task_id in self._task_errors:
            return {
                "status": "failed",
                "task_id": task_id,
                "error": self._task_errors[task_id]
            }
        elif task_id in self._task_results:
            return {
                "status": "completed",
                "task_id": task_id,
                "result": self._task_results[task_id]
            }
        else:
            return {
                "status": "not_found",
                "task_id": task_id
            }

    def clear_task_results(self, task_id: str = None):
        """
        清理任务结果缓存
        
        Args:
            task_id: 任务ID，如果为None则清理所有结果
        """
        if task_id is None:
            self._task_results.clear()
            self._task_errors.clear()
        else:
            if task_id in self._task_results:
                del self._task_results[task_id]
            if task_id in self._task_errors:
                del self._task_errors[task_id]

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
        return len(self._running_tasks)
        
    def execute_instruction(self, instruction: str) -> str:
        """
        执行指令并返回结果
        注意：这是一个示例方法，实际实现应该调用适当的执行器
        """
        # 这里应该调用实际的执行逻辑
        # 为了示例，返回一个模拟结果
        return f"执行结果: {instruction}"

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
        from new.capabilities.optimization.optuna_optimizer import OptimizationOrchestrator
        
        try:
            # 步骤1: 创建优化协调器
            orchestrator = OptimizationOrchestrator(user_goal)
            
            # 步骤2: 发现优化维度
            logger.info("Discovering optimization dimensions...")
            schema = orchestrator.discover_optimization_dimensions()
            logger.info(f"Found {len(schema['dimensions'])} dimensions: {[d['name'] for d in schema['dimensions']]}")
            
            # 步骤3: 运行多轮优化
            best_result = None
            for round_idx in range(optimization_rounds):
                logger.info(f"Starting optimization round {round_idx+1}/{optimization_rounds}")
                
                # 获取优化指令
                optimization_batch = orchestrator.get_optimization_instructions(batch_size=max_concurrent)
                
                # 并行执行这些指令
                execution_results = []
                for trial_info in optimization_batch['trials']:
                    # 使用执行管理器执行指令
                    instruction = trial_info['instruction']
                    
                    # 这里调用实际的执行逻辑，而不是Optuna执行
                    # 假设我们有一个execute_instruction方法
                    output = self.execute_instruction(instruction)
                    
                    execution_results.append({
                        'trial_number': trial_info['trial_number'],
                        'output': output
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
    
    def _execute_trials_parallel(self, instructions: List[str], trial_numbers: List[int]) -> List[Dict]:
        """
        并行执行试验任务
        
        Args:
            instructions: 任务指令列表
            trial_numbers: 试验编号列表
            
        Returns:
            执行结果列表
        """
        results = []
        
        for i, (inst, trial_num) in enumerate(zip(instructions, trial_numbers)):
            # 轮询使用执行actor
            actor = self.execution_actors[i % len(self.execution_actors)]
            
            # 创建任务消息
            task_msg = {
                "type": "leaf_task",
                "task_id": f"trial_{trial_num}",
                "context": {"instruction": inst},
                "memory": {},
                "capability": "execute_instruction",
                "agent_id": f"agent_{i}"
            }
            
            # 执行任务
            try:
                result = self.actor_system.ask(actor, task_msg, timeout=300)
                results.append({
                    "trial_number": trial_num,
                    "result": result,
                    "success": True
                })
            except Exception as e:
                results.append({
                    "trial_number": trial_num,
                    "result": str(e),
                    "success": False
                })
        
        return results

def main():
    # 简单的测试代码
    manager = ParallelExecutionManager()
    
    # 测试工作流执行
    try:
        result = manager.execute_workflow("test_workflow_123", 
                                         {"input": "test"}, 
                                         {"history": []}, 
                                         "test_sender", "test_key", "http://example.com")
        logger.info(f"Workflow execution result: {result}")
    except Exception as e:
        logger.error(f"Workflow execution failed: {str(e)}")

# 移除了异步辅助函数，因为所有方法现在都是同步的
if __name__ == "__main__":
    main()