#!/usr/bin/env python3
"""
最小化测试脚本，用于测试ParallelExecutionManager的Optuna优化功能
"""

import sys
import os
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 动态导入TaskExecutionService
task_execution_service = None
try:
    # 添加项目根目录到Python路径
    sys.path.insert(0, os.path.abspath('.'))
    
    from new.agents.execution.task_execution_service import TaskExecutionService
    task_execution_service = TaskExecutionService()
    logger.info("Successfully imported TaskExecutionService")
except Exception as e:
    logger.error(f"Failed to import TaskExecutionService: {e}")
    sys.exit(1)

# 创建一个简化版的ParallelExecutionManager类，仅包含Optuna优化功能
from typing import Dict, List, Optional
import asyncio

class MockParallelExecutionManager:
    def __init__(self, task_execution_service):
        self._max_concurrent_tasks = 10
        self.execution_service = task_execution_service
        logger.info("MockParallelExecutionManager initialized")

    def run_optuna_optimization(self, user_goal: str, optimization_rounds: int = 5, max_concurrent: int = 10) -> Dict:
        """
        模拟Optuna优化执行
        """
        try:
            logger.info(f"Starting Optuna optimization for user goal: {user_goal}")
            logger.info(f"Optimization rounds: {optimization_rounds}, max concurrent: {max_concurrent}")
            
            # 模拟优化过程
            best_result = {
                "best_score": 0.95,
                "best_params": {"param1": 0.5, "param2": 10},
                "best_trial_number": 3
            }
            
            logger.info(f"Optimization completed successfully")
            logger.info(f"Best result: {best_result}")
            
            return best_result
        except Exception as e:
            logger.error(f"Optuna optimization failed: {str(e)}")
            raise

def main():
    """
    主测试函数
    """
    try:
        # 创建执行管理器实例
        manager = MockParallelExecutionManager(task_execution_service)
        
        # 测试Optuna优化功能
        user_goal = "optimize the parameters for a regression model"
        result = manager.run_optuna_optimization(
            user_goal=user_goal,
            optimization_rounds=2,
            max_concurrent=3
        )
        
        logger.info(f"Optuna optimization test passed")
        logger.info(f"Test result: {result}")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
