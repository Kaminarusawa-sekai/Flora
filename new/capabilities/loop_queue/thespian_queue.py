"""基于Thespian框架的循环队列实现"""
from typing import Dict, Any, Callable, Optional
from threading import Thread
import time
from thespian.actors import ActorSystem
from ..capability_base import CapabilityBase


class ThespianLoopQueue(CapabilityBase, LoopQueueInterface):
    """
    基于Thespian框架的循环队列实现
    管理和执行循环任务
    """
    
    def __init__(self):
        """
        初始化Thespian循环队列
        """
        super().__init__()
        self.actor_system = None
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.running = False
        self.thread = None
        self.task_counter = 0
    
    def initialize(self) -> bool:
        """
        初始化Thespian循环队列
        """
        if not super().initialize():
            return False
        
        try:
            self.actor_system = ActorSystem()
            return True
        except Exception:
            return False
    
    def get_capability_type(self) -> str:
        """
        获取能力类型
        """
        return 'loop_queue'
    
    def add_task(self, task: Callable, interval: int) -> str:
        """
        添加循环任务
        """
        if not callable(task):
            raise ValueError("Task must be callable")
        
        if interval <= 0:
            raise ValueError("Interval must be positive")
        
        task_id = f"task_{self.task_counter}"
        self.task_counter += 1
        
        self.tasks[task_id] = {
            'task': task,
            'interval': interval,
            'last_run': time.time(),
            'running': True,
            'next_run': time.time() + interval
        }
        
        # 如果队列正在运行，确保新任务被执行
        if self.running and not self.thread:
            self._start_execution_thread()
        
        return task_id
    
    def remove_task(self, task_id: str) -> bool:
        """
        移除循环任务
        """
        if task_id in self.tasks:
            del self.tasks[task_id]
            return True
        return False
    
    def start(self) -> bool:
        """
        启动循环队列
        """
        if not self.is_initialized:
            return False
        
        if self.running:
            return True
        
        self.running = True
        self._start_execution_thread()
        return True
    
    def stop(self) -> bool:
        """
        停止循环队列
        """
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        return True
    
    def pause_task(self, task_id: str) -> bool:
        """
        暂停指定任务
        """
        if task_id in self.tasks:
            self.tasks[task_id]['running'] = False
            return True
        return False
    
    def resume_task(self, task_id: str) -> bool:
        """
        恢复指定任务
        """
        if task_id in self.tasks:
            self.tasks[task_id]['running'] = True
            # 重置下次运行时间
            self.tasks[task_id]['next_run'] = time.time() + self.tasks[task_id]['interval']
            return True
        return False
    
    def update_interval(self, task_id: str, new_interval: int) -> bool:
        """
        更新任务执行间隔
        """
        if task_id in self.tasks and new_interval > 0:
            self.tasks[task_id]['interval'] = new_interval
            # 重置下次运行时间
            self.tasks[task_id]['next_run'] = time.time() + new_interval
            return True
        return False
    
    def get_task_status(self, task_id: str) -> Optional[dict]:
        """
        获取任务状态
        """
        if task_id in self.tasks:
            task_info = self.tasks[task_id].copy()
            # 移除不可序列化的task对象
            task_info.pop('task', None)
            return task_info
        return None
    
    def _start_execution_thread(self) -> None:
        """
        启动执行线程
        """
        if not self.thread or not self.thread.is_alive():
            self.thread = Thread(target=self._execution_loop, daemon=True)
            self.thread.start()
    
    def _execution_loop(self) -> None:
        """
        任务执行循环
        """
        while self.running:
            current_time = time.time()
            tasks_to_run = []
            
            # 找出需要执行的任务
            for task_id, task_info in self.tasks.items():
                if task_info['running'] and current_time >= task_info['next_run']:
                    tasks_to_run.append((task_id, task_info))
            
            # 执行到期的任务
            for task_id, task_info in tasks_to_run:
                try:
                    # 使用Thespian执行任务（简化实现）
                    # 实际场景可能需要创建专门的Actor来执行任务
                    task_info['task']()
                    task_info['last_run'] = current_time
                    task_info['next_run'] = current_time + task_info['interval']
                except Exception as e:
                    # 任务执行失败，记录异常并继续
                    print(f"Task {task_id} failed: {e}")
            
            # 计算下次检查的等待时间
            wait_time = self._calculate_next_wait_time()
            time.sleep(min(wait_time, 1.0))  # 最多等待1秒，避免长时间阻塞
    
    def _calculate_next_wait_time(self) -> float:
        """
        计算下次检查的等待时间
        """
        next_runs = [task_info['next_run'] for task_info in self.tasks.values() 
                    if task_info['running']]
        
        if not next_runs:
            return 1.0  # 没有任务时默认等待1秒
        
        next_run_time = min(next_runs)
        wait_time = next_run_time - time.time()
        return max(wait_time, 0.1)  # 至少等待0.1秒
    
    def shutdown(self) -> None:
        """
        关闭循环队列，释放资源
        """
        self.stop()
        if self.actor_system:
            self.actor_system.shutdown()
            self.actor_system = None
        super().shutdown()
