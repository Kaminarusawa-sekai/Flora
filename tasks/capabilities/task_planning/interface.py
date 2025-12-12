from abc import abstractmethod
from typing import Any
from ..capability_base import CapabilityBase
from typing import Any, Dict, List, Optional


class ITaskPlanningCapability(CapabilityBase):
    """
    任务规划能力的抽象接口。
    定义了外界如何请求生成执行计划，而不关心内部是基于 LLM 还是规则引擎。
    """

    def get_capability_type(self) -> str:
        return "task_planning"



    @abstractmethod
    def generate_execution_plan(
        self, 
        agent_id: str, 
        user_input: str, 
        memory_context: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        [核心API] 生成完整的执行规划链。
        
        Returns:
            List[Dict]: 包含 step, type(AGENT/MCP), executor, params 等字段的有序列表。
        """
        pass

    @abstractmethod
    def plan_subtasks(self, parent_agent_id: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        [子能力API] 针对特定节点及其依赖进行局部规划（通常用于处理隐性依赖）。
        """
        pass