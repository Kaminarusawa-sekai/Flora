from abc import abstractmethod
from typing import Dict, Any
from ..capability_base import CapabilityBase


class IChartDrawer(CapabilityBase):
    """
    图表绘制能力的抽象接口
    定义了将查询结果转换为可视化图表的能力规范
    """
    
    def get_capability_type(self) -> str:
        """
        返回能力类型
        """
        return "chart_drawing"
    
    @abstractmethod
    def enhance_with_charts(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        对 resolve_context 的结果进行后处理：
          - 若某个 value 是 list[dict]（即查询结果 records），
            且满足可视化条件，则将其替换为 Plotly 图表 HTML 字符串。
          - 其他值（单值、None、非列表）保持不变。
        
        Args:
            result: 需要处理的查询结果字典
            
        Returns:
            增强后的结果字典，包含图表 HTML 字符串
        """
        pass
