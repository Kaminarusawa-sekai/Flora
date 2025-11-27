#!/usr/bin/env python3
"""
执行管理器启动器
用于启动执行管理器并与Optuna交互
"""

import sys
import logging
from typing import Dict, Any

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """
    主函数，用于启动执行管理器并处理命令行参数
    """
    try:
        # 导入执行管理器
        from agents.parallel.execution_manager import ParallelExecutionManager
        
        # 初始化执行管理器
        execution_manager = ParallelExecutionManager()
        
        logger.info("Execution manager launcher started successfully")
        
        # 示例：运行Optuna优化
        if len(sys.argv) > 1:
            user_goal = sys.argv[1]
            optimization_rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 5
            max_concurrent = int(sys.argv[3]) if len(sys.argv) > 3 else 10
            
            logger.info(f"Running Optuna optimization for user goal: {user_goal}")
            logger.info(f"Optimization rounds: {optimization_rounds}, max concurrent: {max_concurrent}")
            
            result = execution_manager.run_optuna_optimization(
                user_goal=user_goal,
                optimization_rounds=optimization_rounds,
                max_concurrent=max_concurrent
            )
            
            logger.info(f"Optimization result: {result}")
        else:
            logger.error("No user goal provided. Usage: python execution_manager_launcher.py <user_goal> <optimization_rounds> <max_concurrent>")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Failed to run execution manager: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()