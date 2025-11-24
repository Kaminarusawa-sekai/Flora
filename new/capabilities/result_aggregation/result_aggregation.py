"""结果聚合能力组件"""
from typing import Dict, Any, List


class ResultAggregator:
    @staticmethod
    def aggregate_sequential(results: dict) -> any:
        """取最后一个结果"""
        if not results:
            return None
        return list(results.values())[-1]

    @staticmethod
    def aggregate_vote(results: dict) -> any:
        # 可扩展：多数投票、加权平均等
        raise NotImplementedError

    @staticmethod
    def aggregate(results: Dict, strategy: str = 'sequential') -> Any:
        """
        通用聚合方法，根据指定策略聚合结果
        
        Args:
            results: 要聚合的结果字典
            strategy: 聚合策略，支持 'sequential', 'vote' 和 'map_reduce'
            
        Returns:
            聚合后的结果
        """
        if strategy == 'sequential':
            return ResultAggregator.aggregate_sequential(results)
        elif strategy == 'vote':
            return ResultAggregator.aggregate_vote(results)
        elif strategy == 'map_reduce':
            return ResultAggregator._default_reduce(results)
        else:
            raise ValueError(f"Unsupported aggregation strategy: {strategy}")
    
    @staticmethod
    def _default_reduce(results: List[Dict]) -> Dict[str, Any]:
        """
        默认的归约函数
        简单聚合结果
        
        Args:
            results: 任务执行结果列表
            
        Returns:
            聚合后的结果
        """
        # 过滤出成功的结果
        success_results = [r for r in results if r.get('success', False)]
        failed_results = [r for r in results if not r.get('success', False)]
        
        # 聚合成功结果中的数据
        aggregated_data = []
        for result in success_results:
            if 'result' in result:
                aggregated_data.append(result['result'])
            elif 'output' in result:
                aggregated_data.append(result['output'])
            elif 'data' in result:
                aggregated_data.append(result['data'])
        
        return {
            'success': len(success_results) > 0,
            'success_rate': len(success_results) / len(results) if results else 0,
            'success_count': len(success_results),
            'failure_count': len(failed_results),
            'aggregated_data': aggregated_data
        }

    @staticmethod
    def aggregate_subtask_results(task: Dict, subtasks: List[Dict]) -> Any:
        """
        聚合子任务结果
        
        Args:
            task: 任务信息
            subtasks: 子任务列表
            
        Returns:
            聚合后的结果
        """
        results = []
        
        # 收集所有子任务结果
        for subtask in subtasks:
            subtask_result = subtask.get('result')
            if subtask_result:
                results.append(subtask_result)
        
        # 检查是否有子任务失败
        failed_subtasks = [subtask for subtask in subtasks if subtask['status'] == 'failed']
        if failed_subtasks:
            # 如果有失败的子任务，返回错误信息
            error_messages = [f"Subtask {subtask['task_id']} failed: {subtask.get('error', 'Unknown error')}" 
                            for subtask in failed_subtasks]
            return {
                "success": False,
                "error": "\n".join(error_messages),
                "failed_subtasks": len(failed_subtasks),
                "total_subtasks": len(subtasks),
                "results": results
            }
        
        # 根据任务类型进行聚合
        task_type = task['task_type']
        
        if task_type == 'workflow':
            # 工作流任务：合并所有输出到一个列表
            aggregated_output = [result.get('output', {}) for result in results]
            return {
                "success": True,
                "output": aggregated_output,
                "subtasks_count": len(subtasks),
                "results": results
            }
        elif task_type == 'data_processing':
            # 数据处理任务：合并所有data字段
            aggregated_data = []
            total_items = 0
            
            for result in results:
                data = result.get('data', [])
                if isinstance(data, list):
                    aggregated_data.extend(data)
                    total_items += len(data)
                elif isinstance(data, dict):
                    aggregated_data.append(data)
                    total_items += 1
            
            return {
                "success": True,
                "data": aggregated_data,
                "total_items": total_items,
                "subtasks_count": len(subtasks),
                "results": results
            }
        else:
            # 默认：生成包含子任务数量的摘要
            return {
                "success": True,
                "summary": f"Completed {len(subtasks)} subtasks",
                "subtasks_count": len(subtasks),
                "results": results
            }



# 注册能力
from ..registry import capability_registry

class ResultAggregationCapability:
    """结果聚合能力"""
    def __init__(self):
        self.aggregator = ResultAggregator()

    def get_capability_type(self) -> str:
        return "result_aggregation"

    def aggregate(self, results: Dict, strategy: str = 'sequential') -> Any:
        return self.aggregator.aggregate(results, strategy)

    def aggregate_subtask_results(self, task: Dict, subtasks: List[Dict]) -> Any:
        return self.aggregator.aggregate_subtask_results(task, subtasks)


# 注册结果聚合能力
capability_registry.register("result_aggregation", ResultAggregationCapability)

