"""外部系统交互模块"""

# 只导入不依赖外部服务的仓储类
from .repositories.task_repo import TaskRepository
from .repositories.draft_repo import DraftRepository

__all__ = [
    # Repositories
    'TaskRepository',
    'DraftRepository',
    
    # 其他模块按需导入，避免不必要的依赖
    # AgentStructureRepository, Database, Clients, Message Queue 等模块需要时单独导入
]
