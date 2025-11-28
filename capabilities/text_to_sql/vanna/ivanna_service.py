from abc import ABC, abstractmethod
from typing import List, Tuple, Any, Optional

class IVannaService(ABC):
    """
    Vanna 服务的抽象接口，用于解耦具体实现。
    """

    @abstractmethod
    def __init__(self, business_id: str, **kwargs):
        pass

    @abstractmethod
    def system_message(self, message: str) -> Any:
        pass

    @abstractmethod
    def user_message(self, message: str) -> Any:
        pass

    @abstractmethod
    def assistant_message(self, message: str) -> Any:
        pass

    @abstractmethod
    def submit_prompt(self, messages: List[Any]) -> str:
        pass

    # 可选方法：如果需要统一支持 generate_sql，则可加 @abstractmethod
    # 但 VannaBase 本身已有逻辑，这里保持最小契约
    def generate_sql(self, question: str, database: Optional[str] = None, **kwargs) -> str:
        """
        默认调用 VannaBase 的 generate_sql，子类可覆盖。
        """
        raise NotImplementedError("Subclasses should implement or inherit generate_sql.")

    @abstractmethod
    def train_ddl_with_database(self, database: str, table: str, ddl: str = None):
        pass

    # 其他可能需要的方法（如 get_related_ddl 等）可按需加入