"""记忆能力Actor"""
from typing import Dict, Any, Optional, List
from thespian.actors import Actor
import logging
from ..capabilities.llm_memory.manager import UnifiedMemoryManager
from ..capabilities.registry import capability_registry


class MemoryActor(Actor):
    """
    记忆能力Actor
    负责管理和访问智能体的记忆系统
    从agent/memory/memory_actor.py迁移并重构
    """
    
    def __init__(self):
        """
        初始化记忆Actor
        """
        self.logger = logging.getLogger(__name__)
        self.manager = None
        self.agent_id = ""
        self.initialize_memory_manager()
    
    def initialize_memory_manager(self):
        """
        初始化记忆管理器
        使用capabilities中的LLM记忆能力
        """
        try:
            # 通过能力注册表获取记忆能力
            memory_capability = capability_registry.get_capability("memory_manager")
            
            if memory_capability:
                self.manager = memory_capability
            else:
                # 如果能力注册表中没有，直接创建
                self.manager = UnifiedMemoryManager()
                
            self.manager.initialize()
            self.logger.info("记忆管理器初始化成功")
        except Exception as e:
            self.logger.error(f"记忆管理器初始化失败: {e}")
    
    def receiveMessage(self, msg: Dict[str, Any], sender: str) -> None:
        """
        接收消息并处理
        
        Args:
            msg: 消息内容
            sender: 发送者
        """
        try:
            msg_type = msg.get("type", "")
            
            if msg_type == "initialize":
                self._handle_initialize(msg, sender)
            elif msg_type == "store":
                self._handle_store(msg, sender)
            elif msg_type == "retrieve":
                self._handle_retrieve(msg, sender)
            elif msg_type == "update":
                self._handle_update(msg, sender)
            elif msg_type == "delete":
                self._handle_delete(msg, sender)
            elif msg_type == "clear":
                self._handle_clear(msg, sender)
            elif msg_type == "search":
                self._handle_search(msg, sender)
            elif msg_type == "get_status":
                self._handle_get_status(msg, sender)
            else:
                self.logger.warning(f"未知消息类型: {msg_type}")
                self.send(sender, {"status": "error", "message": f"未知消息类型: {msg_type}"})
        
        except Exception as e:
            self.logger.error(f"处理消息失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
    
    def _handle_initialize(self, msg: Dict[str, Any], sender: str):
        """
        处理初始化消息
        """
        self.agent_id = msg.get("agent_id", "default")
        
        # 如果需要特定的配置
        if "config" in msg:
            self.manager = UnifiedMemoryManager(msg["config"])
            self.manager.initialize()
        
        self.send(sender, {"status": "success", "agent_id": self.agent_id})
    
    def _handle_store(self, msg: Dict[str, Any], sender: str):
        """
        存储记忆项
        """
        key = msg.get("key")
        value = msg.get("value")
        metadata = msg.get("metadata", {})
        memory_type = msg.get("type", "short_term")
        
        if not key:
            self.send(sender, {"status": "error", "message": "缺少key参数"})
            return
        
        try:
            result = self.manager.store_memory_item(
                key=key,
                value=value,
                metadata=metadata,
                memory_type=memory_type,
                agent_id=self.agent_id
            )
            self.send(sender, {"status": "success", "result": result})
        except Exception as e:
            self.logger.error(f"存储记忆失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
    
    def _handle_retrieve(self, msg: Dict[str, Any], sender: str):
        """
        检索记忆项
        """
        key = msg.get("key")
        memory_type = msg.get("type", "short_term")
        
        if key:
            # 通过key检索
            try:
                result = self.manager.retrieve_memory_item(
                    key=key,
                    memory_type=memory_type,
                    agent_id=self.agent_id
                )
                self.send(sender, {"status": "success", "result": result})
            except Exception as e:
                self.logger.error(f"检索记忆失败: {e}")
                self.send(sender, {"status": "error", "message": str(e)})
        else:
            # 获取所有记忆
            limit = msg.get("limit", 100)
            offset = msg.get("offset", 0)
            try:
                results = self.manager.get_all_memory_items(
                    memory_type=memory_type,
                    agent_id=self.agent_id,
                    limit=limit,
                    offset=offset
                )
                self.send(sender, {"status": "success", "results": results})
            except Exception as e:
                self.logger.error(f"获取所有记忆失败: {e}")
                self.send(sender, {"status": "error", "message": str(e)})
    
    def _handle_update(self, msg: Dict[str, Any], sender: str):
        """
        更新记忆项
        """
        key = msg.get("key")
        updates = msg.get("updates", {})
        memory_type = msg.get("type", "short_term")
        
        if not key:
            self.send(sender, {"status": "error", "message": "缺少key参数"})
            return
        
        try:
            result = self.manager.update_memory_item(
                key=key,
                updates=updates,
                memory_type=memory_type,
                agent_id=self.agent_id
            )
            self.send(sender, {"status": "success", "result": result})
        except Exception as e:
            self.logger.error(f"更新记忆失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
    
    def _handle_delete(self, msg: Dict[str, Any], sender: str):
        """
        删除记忆项
        """
        key = msg.get("key")
        memory_type = msg.get("type", "short_term")
        
        if not key:
            self.send(sender, {"status": "error", "message": "缺少key参数"})
            return
        
        try:
            result = self.manager.delete_memory_item(
                key=key,
                memory_type=memory_type,
                agent_id=self.agent_id
            )
            self.send(sender, {"status": "success", "result": result})
        except Exception as e:
            self.logger.error(f"删除记忆失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
    
    def _handle_clear(self, msg: Dict[str, Any], sender: str):
        """
        清空记忆
        """
        memory_type = msg.get("type")  # 如果为None，则清空所有类型
        
        try:
            result = self.manager.clear_memory(
                memory_type=memory_type,
                agent_id=self.agent_id
            )
            self.send(sender, {"status": "success", "result": result})
        except Exception as e:
            self.logger.error(f"清空记忆失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
    
    def _handle_search(self, msg: Dict[str, Any], sender: str):
        """
        搜索记忆
        """
        query = msg.get("query", "")
        filters = msg.get("filters", {})
        memory_type = msg.get("type", "short_term")
        limit = msg.get("limit", 10)
        
        try:
            results = self.manager.search_memory(
                query=query,
                filters=filters,
                memory_type=memory_type,
                agent_id=self.agent_id,
                limit=limit
            )
            self.send(sender, {"status": "success", "results": results})
        except Exception as e:
            self.logger.error(f"搜索记忆失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
    
    def _handle_get_status(self, msg: Dict[str, Any], sender: str):
        """
        获取记忆系统状态
        """
        try:
            status = self.manager.get_status(agent_id=self.agent_id)
            self.send(sender, {"status": "success", "status_info": status})
        except Exception as e:
            self.logger.error(f"获取状态失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
