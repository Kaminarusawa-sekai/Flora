from typing import List, Optional
from common.dialog import DialogTurn
from .interface import IContextManagerCapability
from external.database import SQLiteConnectionPool, DialogRepository



class CommonContextManager(IContextManagerCapability):
    """
    通用上下文管理器实现，使用SQLite存储对话历史
    """
    
    def __init__(self):
        super().__init__()
        self.pool = None
        self.repo = None
        self.db_path = None
    
    def initialize(self, config: dict) -> None:
        """
        初始化上下文管理器
        
        Args:
            config: 配置字典，包含数据库路径等配置
        """
        self.db_path = config.get("db_path", "./dialog.db")
        max_connections = config.get("max_connections", 5)
        self.logger.info(f"初始化上下文管理器，数据库路径: {self.db_path}，最大连接数: {max_connections}")
        self.pool = SQLiteConnectionPool(self.db_path, max_connections)
        self.repo = DialogRepository(self.pool)
        self.logger.info("上下文管理器初始化完成")
    
    def shutdown(self) -> None:
        """
        关闭上下文管理器，释放资源
        """
        self.logger.info("关闭上下文管理器，释放资源")
        if self.pool:
            self.pool.close_all()
            self.pool = None
            self.logger.info("数据库连接池已关闭")
        self.repo = None
        self.logger.info("上下文管理器关闭完成")
    
    def get_capability_type(self) -> str:
        """
        获取能力类型
        
        Returns:
            能力类型字符串
        """
        return "context_manager"
    
    def add_turn(self, turn: DialogTurn) -> int:
        """
        添加一个对话轮次到上下文
        
        Args:
            turn: 对话轮次对象
            
        Returns:
            轮次ID
        """
        if not self.repo:
            raise ValueError("Context manager not initialized")
        return self.repo.save_turn(turn)
    
    def get_turn(self, turn_id: int) -> Optional[DialogTurn]:
        """
        根据ID获取对话轮次
        
        Args:
            turn_id: 轮次ID
            
        Returns:
            对话轮次对象，不存在则返回None
        """
        if not self.repo:
            raise ValueError("Context manager not initialized")
        return self.repo.get_turn_by_id(turn_id)
    
    def get_recent_turns(self, limit: int = 10) -> List[DialogTurn]:
        """
        获取最近的对话轮次
        
        Args:
            limit: 返回的最大轮次数
            
        Returns:
            对话轮次列表，按时间戳倒序排列
        """
        if not self.repo:
            raise ValueError("Context manager not initialized")
        all_turns = self.repo.get_all_turns()
        return all_turns[-limit:][::-1]
    
    def get_all_turns(self) -> List[DialogTurn]:
        """
        获取所有对话轮次
        
        Returns:
            对话轮次列表，按时间戳正序排列
        """
        if not self.repo:
            raise ValueError("Context manager not initialized")
        return self.repo.get_all_turns()
    
    def update_turn(self, turn_id: int, enhanced_utterance: str) -> bool:
        """
        更新对话轮次的增强型对话
        
        Args:
            turn_id: 轮次ID
            enhanced_utterance: 增强型对话内容
            
        Returns:
            更新是否成功
        """
        if not self.repo:
            raise ValueError("Context manager not initialized")
        return self.repo.update_turn(turn_id, enhanced_utterance)
    
    def compress_context(self, n: int) -> bool:
        """
        压缩上下文，将最近的n轮对话合并或精简
        
        Args:
            n: 要压缩的轮次数
            
        Returns:
            压缩是否成功
        """
        if not self.repo:
            raise ValueError("Context manager not initialized")
        
        # 获取最早的n个轮次
        old_turns = self.repo.get_oldest_turns(n)
        if not old_turns:
            return False
        
        # 合并这些轮次为一个摘要
        compressed_text = "\n".join([f"{turn['role']}: {turn['utterance']}" for turn in old_turns])
        
        # 创建新的压缩轮次
        from common.dialog import DialogTurn
        import time
        # 使用第一个旧轮次的 session_id 和 user_id
        session_id = old_turns[0].get('session_id', 'compressed')
        user_id = old_turns[0].get('user_id', 'system')
        compressed_turn = DialogTurn(
            role="system",
            utterance=f"[压缩摘要] {compressed_text}",
            timestamp=time.time(),
            enhanced_utterance="压缩后的对话摘要",
            session_id=session_id,
            user_id=user_id
        )
        
        # 获取要删除的轮次ID
        turn_ids_to_delete = [turn['id'] for turn in old_turns]
        
        # 删除旧轮次并添加新轮次
        if self.repo.delete_turns_by_ids(turn_ids_to_delete):
            self.repo.save_turn(compressed_turn)
            return True
        return False
    
    def clear_context(self, n: int = 10) -> bool:
        """
        清空n轮前的上下文，保留最近的n轮对话
        
        Args:
            n: 要保留的最近轮次数，默认10
            
        Returns:
            清空是否成功
        """
        if not self.repo:
            raise ValueError("Context manager not initialized")
        return self.repo.delete_old_turns(n)
    
    def get_context_length(self) -> int:
        """
        获取当前上下文的长度
        
        Returns:
            对话轮次数量
        """
        if not self.repo:
            raise ValueError("Context manager not initialized")
        all_turns = self.repo.get_all_turns()
        return len(all_turns)
    
    def get_turns_by_session(self, session_id: str, limit: int = 20, offset: int = 0) -> List[DialogTurn]:
        """
        根据会话ID获取对话轮次
        
        Args:
            session_id: 会话ID
            limit: 返回的最大轮次数
            offset: 偏移量
            
        Returns:
            对话轮次列表，按时间戳倒序排列
        """
        if not self.repo:
            raise ValueError("Context manager not initialized")
        return self.repo.get_turns_by_session(session_id, limit, offset)
    
    def get_turns_by_user(self, user_id: str, limit: int = 20, offset: int = 0) -> List[DialogTurn]:
        """
        根据用户ID获取对话轮次
        
        Args:
            user_id: 用户ID
            limit: 返回的最大轮次数
            offset: 偏移量
            
        Returns:
            对话轮次列表，按时间戳倒序排列
        """
        if not self.repo:
            raise ValueError("Context manager not initialized")
        return self.repo.get_turns_by_user(user_id, limit, offset)
    
    def update_turn_user_id(self, session_id: str, old_user_id: str, new_user_id: str) -> bool:
        """
        更新会话中所有轮次的用户ID（用于匿名转正式）
        
        Args:
            session_id: 会话ID
            old_user_id: 旧用户ID
            new_user_id: 新用户ID
            
        Returns:
            更新是否成功
        """
        if not self.repo:
            raise ValueError("Context manager not initialized")
        return self.repo.update_turns_user_id(session_id, old_user_id, new_user_id)