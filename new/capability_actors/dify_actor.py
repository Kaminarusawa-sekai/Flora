"""Dify能力Actor"""
from typing import Dict, Any, Optional, List
from thespian.actors import Actor
import logging
from ..external.execution_connectors.dify.connector import DifyConnector
from ..capabilities.registry import capability_registry


class DifyCapabilityActor(Actor):
    """
    Dify能力Actor
    负责与Dify服务的交互
    从agent/excute/dify_actor.py迁移并重构
    """
    
    def __init__(self):
        """
        初始化Dify能力Actor
        """
        self.logger = logging.getLogger(__name__)
        self.dify_connector = None
        self.agent_id = ""
        self.initialize_dify_connector()
    
    def initialize_dify_connector(self):
        """
        初始化Dify连接器
        """
        try:
            # 从配置中获取Dify相关配置
            from ..common.config.config_manager import get_config
            dify_config = get_config("dify")
            
            if dify_config and dify_config.get("enabled", True):
                self.dify_connector = DifyConnector(dify_config)
                self.logger.info("Dify连接器初始化成功")
            else:
                self.logger.warning("Dify未启用或配置不存在")
        except Exception as e:
            self.logger.error(f"Dify连接器初始化失败: {e}")
    
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
            elif msg_type == "chat":
                self._handle_chat(msg, sender)
            elif msg_type == "completion":
                self._handle_completion(msg, sender)
            elif msg_type == "workflow":
                self._handle_workflow(msg, sender)
            elif msg_type == "tool":
                self._handle_tool(msg, sender)
            elif msg_type == "embedding":
                self._handle_embedding(msg, sender)
            elif msg_type == "status":
                self._handle_status(msg, sender)
            elif msg_type == "config":
                self._handle_config(msg, sender)
            else:
                self.logger.warning(f"未知消息类型: {msg_type}")
                self.send(sender, {"status": "error", "message": f"未知消息类型: {msg_type}"})
        
        except Exception as e:
            self.logger.error(f"处理Dify请求失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
    
    def _handle_initialize(self, msg: Dict[str, Any], sender: str):
        """
        处理初始化消息
        """
        self.agent_id = msg.get("agent_id", "dify_default")
        config = msg.get("config", {})
        
        # 使用提供的配置重新初始化
        if config:
            try:
                self.dify_connector = DifyConnector(config)
                self.logger.info("Dify连接器重新初始化成功")
            except Exception as e:
                self.logger.error(f"重新初始化Dify连接器失败: {e}")
                self.send(sender, {"status": "error", "message": str(e)})
                return
        
        self.send(sender, {"status": "success", "agent_id": self.agent_id})
    
    def _handle_chat(self, msg: Dict[str, Any], sender: str):
        """
        处理聊天请求
        """
        if not self.dify_connector:
            self.send(sender, {"status": "error", "message": "Dify连接器未初始化"})
            return
        
        message = msg.get("message")
        conversation_id = msg.get("conversation_id")
        user = msg.get("user", "user")
        params = msg.get("params", {})
        
        if not message:
            self.send(sender, {"status": "error", "message": "缺少消息内容"})
            return
        
        try:
            result = self.dify_connector.chat(
                message=message,
                conversation_id=conversation_id,
                user=user,
                **params
            )
            self.send(sender, {"status": "success", "result": result})
        except Exception as e:
            self.logger.error(f"聊天请求失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
    
    def _handle_completion(self, msg: Dict[str, Any], sender: str):
        """
        处理文本补全请求
        """
        if not self.dify_connector:
            self.send(sender, {"status": "error", "message": "Dify连接器未初始化"})
            return
        
        prompt = msg.get("prompt")
        params = msg.get("params", {})
        
        if not prompt:
            self.send(sender, {"status": "error", "message": "缺少提示内容"})
            return
        
        try:
            result = self.dify_connector.completion(prompt=prompt, **params)
            self.send(sender, {"status": "success", "result": result})
        except Exception as e:
            self.logger.error(f"文本补全失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
    
    def _handle_workflow(self, msg: Dict[str, Any], sender: str):
        """
        处理工作流请求
        """
        if not self.dify_connector:
            self.send(sender, {"status": "error", "message": "Dify连接器未初始化"})
            return
        
        workflow_id = msg.get("workflow_id")
        inputs = msg.get("inputs", {})
        user = msg.get("user", "user")
        
        if not workflow_id:
            self.send(sender, {"status": "error", "message": "缺少工作流ID"})
            return
        
        try:
            result = self.dify_connector.run_workflow(
                workflow_id=workflow_id,
                inputs=inputs,
                user=user
            )
            self.send(sender, {"status": "success", "result": result})
        except Exception as e:
            self.logger.error(f"工作流执行失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
    
    def _handle_tool(self, msg: Dict[str, Any], sender: str):
        """
        处理工具调用请求
        """
        if not self.dify_connector:
            self.send(sender, {"status": "error", "message": "Dify连接器未初始化"})
            return
        
        tool_name = msg.get("tool_name")
        tool_params = msg.get("params", {})
        
        if not tool_name:
            self.send(sender, {"status": "error", "message": "缺少工具名称"})
            return
        
        try:
            result = self.dify_connector.call_tool(
                tool_name=tool_name,
                **tool_params
            )
            self.send(sender, {"status": "success", "result": result})
        except Exception as e:
            self.logger.error(f"工具调用失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
    
    def _handle_embedding(self, msg: Dict[str, Any], sender: str):
        """
        处理嵌入向量请求
        """
        if not self.dify_connector:
            self.send(sender, {"status": "error", "message": "Dify连接器未初始化"})
            return
        
        text = msg.get("text")
        
        if not text:
            self.send(sender, {"status": "error", "message": "缺少文本内容"})
            return
        
        try:
            embedding = self.dify_connector.get_embedding(text=text)
            self.send(sender, {"status": "success", "embedding": embedding})
        except Exception as e:
            self.logger.error(f"获取嵌入向量失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
    
    def _handle_status(self, msg: Dict[str, Any], sender: str):
        """
        处理状态查询
        """
        try:
            status = {
                "connected": self.dify_connector is not None,
                "version": self.dify_connector.get_version() if self.dify_connector else "unknown",
                "agent_id": self.agent_id
            }
            self.send(sender, {"status": "success", "status": status})
        except Exception as e:
            self.logger.error(f"获取Dify状态失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
    
    def _handle_config(self, msg: Dict[str, Any], sender: str):
        """
        处理配置管理
        """
        action = msg.get("action", "get")
        config_data = msg.get("data", {})
        
        try:
            if action == "get":
                # 获取当前配置
                if self.dify_connector:
                    config = self.dify_connector.get_config()
                    self.send(sender, {"status": "success", "config": config})
                else:
                    self.send(sender, {"status": "error", "message": "Dify连接器未初始化"})
            elif action == "update":
                # 更新配置
                if self.dify_connector:
                    self.dify_connector.update_config(config_data)
                    self.send(sender, {"status": "success", "updated": True})
                else:
                    self.send(sender, {"status": "error", "message": "Dify连接器未初始化"})
            else:
                self.send(sender, {"status": "error", "message": f"未知操作: {action}"})
        except Exception as e:
            self.logger.error(f"配置管理失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
