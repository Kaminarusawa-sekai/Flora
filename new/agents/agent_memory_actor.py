from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

# 从原始模块导入必要的类和函数
from new.capability_actors.memory_actor import MemoryManager

def _extract_known_params(context: Dict[str, Any], memory: Dict[str, Any]) -> Dict[str, Any]:
    """
    从记忆中提取已知参数并丰富上下文
    
    Args:
        context: 原始上下文
        memory: 记忆数据
        
    Returns:
        丰富后的上下文
    """
    enriched_context = context.copy()
    
    # 从短期记忆中提取
    short_term_memories = memory.get("short_term", [])
    for mem in short_term_memories:
        content = mem.get("content", {})
        if isinstance(content, dict):
            # 将记忆中的内容合并到上下文中
            for key, value in content.items():
                if key not in enriched_context:
                    enriched_context[key] = value
    
    # 从长期记忆中提取
    long_term_memories = memory.get("long_term", [])
    for mem in long_term_memories:
        content = mem.get("content", {})
        if isinstance(content, dict):
            # 优先使用长期记忆中的领域特定信息
            if "domain" in content:
                enriched_context["domain_knowledge"] = content
    
    # 从上下文记忆中提取
    context_memories = memory.get("context", [])
    for mem in context_memories:
        content = mem.get("content", {})
        if isinstance(content, dict):
            # 上下文记忆有最高优先级
            for key, value in content.items():
                enriched_context[key] = value
    
    return enriched_context

class AgentMemoryActor:
    def __init__(self, agent_id: str, params: Dict[str, Any] = None):
        """
        初始化AgentMemoryActor
        
        Args:
            agent_id: 代理ID
            params: 初始化参数
        """
        self.agent_id = agent_id
        self.params = params or {}
        self.logger = logging.getLogger(f"AgentMemoryActor_{agent_id}")
        
        # AgentActor相关属性
        self.actor_ref = None
        self.data_actor = None
        self.task_reports = {}
        self.task_id_to_sender = {}
        self.pending_memory_requests = {}
        self.task_groups = {}
        
        # MemoryActor相关属性
        self.manager = MemoryManager(agent_id=agent_id)
    
    def receiveMessage(self, message: Any, sender: str):
        """
        接收消息并根据类型路由到相应的处理方法
        """
        if isinstance(message, dict):
            self.receiveMsg_Dict(message, sender)
        else:
            self.logger.warning(f"未知消息类型: {type(message)}")
    
    def receiveMsg_Dict(self, message: Dict[str, Any], sender: str):
        """
        处理字典类型消息
        """
        # 处理AgentActor相关消息
        msg_type = message.get("type")
        if msg_type == "task":
            self._handle_task(message, sender)
        elif msg_type == "task_result":
            self._handle_execution_result(message, sender)
        elif msg_type == "task_error":
            self._handle_execution_error(message, sender)
        elif msg_type == "task_group_created":
            self._handle_task_group_created(message, sender)
        elif msg_type == "task_group_result":
            self._handle_task_group_result(message, sender)
        elif msg_type == "initialize":
            self._initialize(message, sender)
        
        # 处理MemoryActor相关消息
        elif msg_type == "store":
            self._handle_store(message, sender)
        elif msg_type == "retrieve":
            self._handle_retrieve(message, sender)
        elif msg_type == "update":
            self._handle_update(message, sender)
        elif msg_type == "clear":
            self._handle_clear(message, sender)
        elif msg_type == "search":
            self._handle_search(message, sender)
        elif msg_type == "get_status":
            self._handle_get_status(message, sender)
        elif msg_type == "memory_response":
            self._handle_memory_dict_response(message, sender)
        else:
            self.logger.warning(f"未知消息类型: {msg_type}")
    
    def _initialize(self, message: Dict[str, Any], sender: str):
        """
        初始化Actor
        """
        self.actor_ref = sender
        
        # 初始化数据actor（如果需要）
        if message.get("init_data_actor", False):
            # 简化版数据actor初始化逻辑
            pass
        
        # 初始化记忆管理器（直接使用内部的manager）
        try:
            self.manager.initialize()
            self.send(sender, {"status": "success", "message": "初始化成功"})
        except Exception as e:
            self.logger.error(f"初始化失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
    
    def _handle_task(self, task: Dict[str, Any], sender: str):
        """
        处理任务，整合任务处理和记忆检索
        """
        task_id = task.get("task_id")
        if not task_id:
            self.logger.error("任务缺少task_id")
            return
        
        # 存储发送者信息
        self.task_id_to_sender[task_id] = sender
        
        # 构造上下文记忆的键
        context_memory_key = f"context_{task_id}"
        
        # 存储待处理的记忆请求
        self.pending_memory_requests[task_id] = {
            "type": "task",
            "task": task,
            "context_memory_key": context_memory_key
        }
        
        # 向自身发送短期记忆检索请求（内部方法调用）
        short_term_query = {
            "task_type": task.get("type", ""),
            "task_content": task.get("content", ""),
            "max_results": 3
        }
        
        try:
            # 直接调用内部记忆检索方法
            short_term_memory = self._retrieve_internal(
                query=short_term_query,
                memory_type="short_term",
                limit=3
            )
            
            # 检索上下文记忆
            context_memory = self._retrieve_internal(
                query={"key": context_memory_key},
                memory_type="context",
                limit=1
            )
            
            # 检索长期记忆
            long_term_query = {
                "task_type": task.get("type", ""),
                "domain": task.get("domain", ""),
                "max_results": 5
            }
            long_term_memory = self._retrieve_internal(
                query=long_term_query,
                memory_type="long_term",
                limit=5
            )
            
            # 合并记忆并处理任务
            merged_memory = {
                "short_term": short_term_memory,
                "context": context_memory,
                "long_term": long_term_memory
            }
            
            self._process_task_after_memory(task_id, task, merged_memory)
        except Exception as e:
            self.logger.error(f"记忆检索失败: {e}")
            # 出错时仍处理任务，但不包含记忆
            self._process_task_after_memory(task_id, task, {})
    
    def _process_task_after_memory(self, task_id: str, task: Dict[str, Any], memory: Dict[str, Any]):
        """
        获取记忆后处理任务
        """
        # 丰富任务上下文
        enriched_context = self._enrich_context_with_memory(task.get("context", {}), memory)
        task["context"] = enriched_context
        
        # 判断任务类型并执行
        if self._is_leaf_task(task):
            self._execute_leaf_task(task_id, task)
        else:
            self._execute_intermediate_task(task_id, task)
    
    def _enrich_context_with_memory(self, context: Dict[str, Any], memory: Dict[str, Any]):
        """
        使用记忆丰富上下文
        """
        # 调用原始函数
        return _extract_known_params(context, memory)
    
    def _is_leaf_task(self, task: Dict[str, Any]) -> bool:
        """
        判断是否为叶子任务
        """
        task_type = task.get("type", "")
        # 简化版判断逻辑
        return task_type in ["action", "query", "decision"]
    
    def _execute_leaf_task(self, task_id: str, task: Dict[str, Any]):
        """
        执行叶子任务
        """
        # 简化版执行逻辑
        try:
            # 这里应该是实际的任务执行逻辑
            # 为了演示，我们直接返回成功
            result = {"status": "success", "output": "任务执行结果"}
            
            # 存储短期记忆
            self._store_internal(
                content={
                    "task_id": task_id,
                    "task_type": task.get("type"),
                    "task_content": task.get("content"),
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                },
                memory_type="short_term"
            )
            
            # 发送任务结果
            sender = self.task_id_to_sender.get(task_id)
            if sender:
                self.send(sender, {
                    "type": "task_result",
                    "task_id": task_id,
                    "result": result
                })
        except Exception as e:
            self.logger.error(f"执行任务失败: {e}")
            # 发送错误信息
            sender = self.task_id_to_sender.get(task_id)
            if sender:
                self.send(sender, {
                    "type": "task_error",
                    "task_id": task_id,
                    "error": str(e)
                })
    
    def _execute_intermediate_task(self, task_id: str, task: Dict[str, Any]):
        """
        执行中间任务
        """
        # 简化版中间任务执行逻辑
        try:
            # 这里应该是实际的任务规划逻辑
            # 存储任务报告
            self.task_reports[task_id] = {
                "status": "processing",
                "created_at": datetime.now().isoformat()
            }
            
            # 存储长期记忆（节点选择历史）
            self._store_internal(
                content={
                    "task_id": task_id,
                    "task_type": task.get("type"),
                    "domain": task.get("domain"),
                    "timestamp": datetime.now().isoformat()
                },
                memory_type="long_term"
            )
            
            # 这里应该是任务分解和子任务创建逻辑
            # 为了演示，我们假设任务已完成
            result = {"status": "success", "output": "中间任务执行结果"}
            
            sender = self.task_id_to_sender.get(task_id)
            if sender:
                self.send(sender, {
                    "type": "task_result",
                    "task_id": task_id,
                    "result": result
                })
        except Exception as e:
            self.logger.error(f"执行中间任务失败: {e}")
            sender = self.task_id_to_sender.get(task_id)
            if sender:
                self.send(sender, {
                    "type": "task_error",
                    "task_id": task_id,
                    "error": str(e)
                })
    
    # MemoryActor内部方法
    def _retrieve_internal(self, query: Dict[str, Any], memory_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        内部记忆检索方法
        """
        try:
            results = self.manager.retrieve_memory(
                query=query,
                memory_type=memory_type,
                agent_id=self.agent_id,
                limit=limit
            )
            return results
        except Exception as e:
            self.logger.error(f"内部记忆检索失败: {e}")
            return []
    
    def _store_internal(self, content: Dict[str, Any], memory_type: str):
        """
        内部记忆存储方法
        """
        try:
            self.manager.store_memory(
                content=content,
                memory_type=memory_type,
                agent_id=self.agent_id
            )
        except Exception as e:
            self.logger.error(f"内部记忆存储失败: {e}")
    
    # MemoryActor处理方法
    def _handle_store(self, msg: Dict[str, Any], sender: str):
        """
        处理存储记忆请求
        """
        content = msg.get("content", {})
        memory_type = msg.get("type", "short_term")
        
        try:
            result = self.manager.store_memory(
                content=content,
                memory_type=memory_type,
                agent_id=self.agent_id
            )
            self.send(sender, {"status": "success", "result": result})
        except Exception as e:
            self.logger.error(f"存储记忆失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
    
    def _handle_retrieve(self, msg: Dict[str, Any], sender: str):
        """
        处理检索记忆请求
        """
        query = msg.get("query", {})
        memory_type = msg.get("type", "short_term")
        limit = msg.get("limit", 10)
        
        try:
            results = self.manager.retrieve_memory(
                query=query,
                memory_type=memory_type,
                agent_id=self.agent_id,
                limit=limit
            )
            self.send(sender, {"status": "success", "results": results})
        except Exception as e:
            self.logger.error(f"检索记忆失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
    
    def _handle_update(self, msg: Dict[str, Any], sender: str):
        """
        处理更新记忆请求
        """
        memory_id = msg.get("id")
        content = msg.get("content", {})
        memory_type = msg.get("type", "short_term")
        
        if not memory_id:
            self.send(sender, {"status": "error", "message": "缺少记忆ID"})
            return
        
        try:
            result = self.manager.update_memory(
                memory_id=memory_id,
                content=content,
                memory_type=memory_type,
                agent_id=self.agent_id
            )
            self.send(sender, {"status": "success", "result": result})
        except Exception as e:
            self.logger.error(f"更新记忆失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
    
    def _handle_clear(self, msg: Dict[str, Any], sender: str):
        """
        处理清空记忆请求
        """
        memory_type = msg.get("type")
        
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
        处理搜索记忆请求
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
        处理获取状态请求
        """
        try:
            status = self.manager.get_status(agent_id=self.agent_id)
            self.send(sender, {"status": "success", "status_info": status})
        except Exception as e:
            self.logger.error(f"获取状态失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
    
    def _handle_memory_dict_response(self, response: Dict[str, Any], sender: str):
        """
        处理记忆响应
        """
        # 简化版处理逻辑
        request_id = response.get("request_id")
        if not request_id:
            self.logger.error("记忆响应缺少request_id")
            return
        
        # 这里应该处理与请求ID相关的任务
        # 由于我们现在直接在内部处理记忆检索，这个方法可能不再需要
        # 但保留它以保持兼容性
    
    def _handle_execution_result(self, result: Dict[str, Any], sender: str):
        """
        处理执行结果
        """
        task_id = result.get("task_id")
        if not task_id:
            self.logger.error("执行结果缺少task_id")
            return
        
        # 简化版结果处理
        self.logger.info(f"任务 {task_id} 执行成功")
        
        # 存储结果到短期记忆
        self._store_internal(
            content={
                "task_id": task_id,
                "result": result.get("result"),
                "timestamp": datetime.now().isoformat()
            },
            memory_type="short_term"
        )
    
    def _handle_execution_error(self, error: Dict[str, Any], sender: str):
        """
        处理执行错误
        """
        task_id = error.get("task_id")
        if not task_id:
            self.logger.error("执行错误缺少task_id")
            return
        
        # 简化版错误处理
        error_msg = error.get("error", "未知错误")
        self.logger.error(f"任务 {task_id} 执行失败: {error_msg}")
    
    def _handle_task_group_created(self, message: Dict[str, Any], sender: str):
        """
        处理任务组创建
        """
        task_group_id = message.get("task_group_id")
        if not task_group_id:
            self.logger.error("任务组创建消息缺少task_group_id")
            return
        
        self.task_groups[task_group_id] = {
            "created_at": datetime.now().isoformat(),
            "tasks": [],
            "status": "created"
        }
    
    def _handle_task_group_result(self, message: Dict[str, Any], sender: str):
        """
        处理任务组结果
        """
        task_group_id = message.get("task_group_id")
        if not task_group_id or task_group_id not in self.task_groups:
            self.logger.error(f"未知任务组ID: {task_group_id}")
            return
        
        self.task_groups[task_group_id]["status"] = "completed"
        self.task_groups[task_group_id]["completed_at"] = datetime.now().isoformat()
    
    def send(self, target: str, message: Any):
        """
        发送消息
        
        Args:
            target: 目标actor ID
            message: 要发送的消息
        """
        # 这里应该是实际的消息发送逻辑
        # 为了演示，我们只是记录日志
        self.logger.info(f"向 {target} 发送消息: {message}")

# 工厂函数
def create_agent_memory_actor(agent_id: str, params: Dict[str, Any] = None) -> AgentMemoryActor:
    """
    创建AgentMemoryActor实例
    
    Args:
        agent_id: 代理ID
        params: 初始化参数
        
    Returns:
        AgentMemoryActor实例
    """
    return AgentMemoryActor(agent_id=agent_id, params=params)