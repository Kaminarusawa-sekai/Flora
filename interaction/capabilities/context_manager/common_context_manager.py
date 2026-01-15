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
        self.logger.info(f"添加对话轮次，role={turn.role}, session_id={turn.session_id}, user_id={turn.user_id}")
        if not self.repo:
            self.logger.error("上下文管理器未初始化，无法执行操作")
            raise ValueError("Context manager not initialized")
        turn_id = self.repo.save_turn(turn)
        self.logger.info(f"对话轮次添加成功，turn_id={turn_id}")
        return turn_id
    
    def get_turn(self, turn_id: int) -> Optional[DialogTurn]:
        """
        根据ID获取对话轮次
        
        Args:
            turn_id: 轮次ID
            
        Returns:
            对话轮次对象，不存在则返回None
        """
        self.logger.info(f"根据ID获取对话轮次，turn_id={turn_id}")
        if not self.repo:
            raise ValueError("Context manager not initialized")
        turn = self.repo.get_turn_by_id(turn_id)
        if turn:
            self.logger.info(f"成功获取对话轮次，turn_id={turn_id}, role={turn.role}")
        else:
            self.logger.info(f"未找到对话轮次，turn_id={turn_id}")
        return turn
    
    def get_recent_turns(self, limit: int = 10, session_id: Optional[str] = None) -> List[DialogTurn]:
        """
        获取最近的对话轮次
        
        Args:
            limit: 返回的最大轮次数
            session_id: 会话ID，可选。如果提供，只获取指定会话的最近轮次
            
        Returns:
            对话轮次列表，按时间戳倒序排列
        """
        self.logger.info(f"获取最近的对话轮次，limit={limit}, session_id={session_id}")
        if not self.repo:
            raise ValueError("Context manager not initialized")
        all_turns = self.repo.get_all_turns(session_id)
        recent_turns = all_turns[-limit:][::-1]
        self.logger.info(f"成功获取最近{len(recent_turns)}轮对话")
        return recent_turns
    
    def get_all_turns(self, session_id: Optional[str] = None) -> List[DialogTurn]:
        """
        获取所有对话轮次
        
        Args:
            session_id: 会话ID，可选。如果提供，只获取指定会话的所有轮次
            
        Returns:
            对话轮次列表，按时间戳正序排列
        """
        self.logger.info(f"获取所有对话轮次，session_id={session_id}")
        if not self.repo:
            raise ValueError("Context manager not initialized")
        all_turns = self.repo.get_all_turns(session_id)
        self.logger.info(f"成功获取所有对话轮次，共{len(all_turns)}轮")
        return all_turns
    
    def update_turn(self, turn_id: int, enhanced_utterance: str) -> bool:
        """
        更新对话轮次的增强型对话
        
        Args:
            turn_id: 轮次ID
            enhanced_utterance: 增强型对话内容
            
        Returns:
            更新是否成功
        """
        self.logger.info(f"更新对话轮次增强型对话，turn_id={turn_id}")
        if not self.repo:
            raise ValueError("Context manager not initialized")
        success = self.repo.update_turn(turn_id, enhanced_utterance)
        self.logger.info(f"对话轮次增强型对话更新{'成功' if success else '失败'}, turn_id={turn_id}")
        return success
    
    def compress_context(self, n: int, session_id: Optional[str] = None) -> bool:
        """
        压缩上下文，将最近的n轮对话合并或精简
        
        Args:
            n: 要压缩的轮次数
            session_id: 会话ID，可选。如果提供，只压缩指定会话的上下文
            
        Returns:
            压缩是否成功
        """
        self.logger.info(f"压缩上下文，n={n}, session_id={session_id}")
        if not self.repo:
            raise ValueError("Context manager not initialized")
        
        # 获取最早的n个轮次
        old_turns = self.repo.get_oldest_turns(n, session_id)
        if not old_turns:
            self.logger.info(f"没有找到可压缩的对话轮次，n={n}, session_id={session_id}")
            return False
        
        self.logger.info(f"找到{len(old_turns)}个可压缩的对话轮次")
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
            compressed_turn_id = self.repo.save_turn(compressed_turn)
            self.logger.info(f"上下文压缩成功，删除{len(turn_ids_to_delete)}个旧轮次，创建新轮次turn_id={compressed_turn_id}")
            return True
        self.logger.exception(f"上下文压缩失败，删除旧轮次失败")
        return False
    
    def clear_context(self, n: int = 10, session_id: Optional[str] = None) -> bool:
        """
        清空n轮前的上下文，保留最近的n轮对话
        
        Args:
            n: 要保留的最近轮次数，默认10
            session_id: 会话ID，可选。如果提供，只清空指定会话的上下文
            
        Returns:
            清空是否成功
        """
        self.logger.info(f"清空上下文，保留最近{n}轮对话，session_id={session_id}")
        if not self.repo:
            raise ValueError("Context manager not initialized")
        success = self.repo.delete_old_turns(n, session_id)
        self.logger.info(f"上下文清空{'成功' if success else '失败'}")
        return success
    
    def get_context_length(self, session_id: Optional[str] = None) -> int:
        """
        获取当前上下文的长度
        
        Args:
            session_id: 会话ID，可选。如果提供，只获取指定会话的上下文长度
            
        Returns:
            对话轮次数量
        """
        self.logger.info(f"获取上下文长度，session_id={session_id}")
        if not self.repo:
            raise ValueError("Context manager not initialized")
        all_turns = self.repo.get_all_turns(session_id)
        context_length = len(all_turns)
        self.logger.info(f"上下文长度为{context_length}轮")
        return context_length
    
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
        self.logger.info(f"根据会话ID获取对话轮次，session_id={session_id}, limit={limit}, offset={offset}")
        if not self.repo:
            raise ValueError("Context manager not initialized")
        turns = self.repo.get_turns_by_session(session_id, limit, offset)
        self.logger.info(f"成功获取{len(turns)}个对话轮次")
        return turns
    
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
        self.logger.info(f"根据用户ID获取对话轮次，user_id={user_id}, limit={limit}, offset={offset}")
        if not self.repo:
            raise ValueError("Context manager not initialized")
        turns = self.repo.get_turns_by_user(user_id, limit, offset)
        self.logger.info(f"成功获取{len(turns)}个对话轮次")
        return turns
    
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
        self.logger.info(f"更新会话中所有轮次的用户ID，session_id={session_id}, old_user_id={old_user_id}, new_user_id={new_user_id}")
        if not self.repo:
            raise ValueError("Context manager not initialized")
        success = self.repo.update_turns_user_id(session_id, old_user_id, new_user_id)
        self.logger.info(f"会话用户ID更新{'成功' if success else '失败'}")
        return success