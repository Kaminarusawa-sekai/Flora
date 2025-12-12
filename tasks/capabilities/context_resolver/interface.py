from abc import abstractmethod
from typing import Dict, Any
from ..capability_base import CapabilityBase

class IContextResolverCapbility(CapabilityBase):
    """
    上下文解析能力的抽象定义
    定义了外界如何与上下文解析器交互，而不关心具体是基于树查找还是其他方式。
    """

    def get_capability_type(self) -> str:
        return 'context_resolver'

    @abstractmethod
    def set_dependencies(self, registry: Any, llm_client: Any = None) -> None:
        """
        注入外部依赖（因为 initialize 只接收 config）
        """
        pass

    @abstractmethod
    def resolve_context(self, context_requirements: Dict[str, str], agent_id: str) -> Dict[str, Any]:
        """
        核心方法：根据需求描述解析上下文变量
        
        Args:
            context_requirements: 需求字典 { "变量名": "自然语言描述" }
            agent_id: 请求发起者的 Agent ID (作为搜索起点)
        Returns:
            Dict[str, Any]: 解析结果 { "变量名": 节点元数据/具体值 }
        """
        pass
    
    @abstractmethod
    def extract_context(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        从任务原始数据中提取基础上下文（保留原有功能）
        """
        pass


    @abstractmethod
    def enhance_param_descriptions_with_context(self,
        base_param_descriptions: dict,
        current_inputs: dict
        ) -> dict:
        """
        基于当前输入和基础参数描述，增强参数描述（保留原有功能）
        """
        pass