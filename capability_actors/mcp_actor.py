"""MCP能力Actor"""
from typing import Dict, Any, Optional, List
from thespian.actors import Actor
import logging
from ..capabilities.registry import capability_registry


class MCPCapabilityActor(Actor):
    """
    MCP能力Actor
    负责MCP（Master Control Program）相关功能
    从agent/mcp/mcp_actor.py迁移
    """
    
    def __init__(self):
        """
        初始化MCP能力Actor
        """
        self.logger = logging.getLogger(__name__)
        self.mcp_capability = None
        self.agent_id = ""
        self.initialize_mcp_capability()
    
    def initialize_mcp_capability(self):
        """
        初始化MCP能力
        """
        try:
            # 通过能力注册表获取MCP能力
            self.mcp_capability = capability_registry.get_capability("mcp")
            
            if self.mcp_capability:
                self.logger.info("MCP能力初始化成功")
            else:
                self.logger.warning("MCP能力未找到，将使用基础实现")
        except Exception as e:
            self.logger.error(f"MCP能力初始化失败: {e}")
    
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
            elif msg_type == "control":
                self._handle_control(msg, sender)
            elif msg_type == "monitor":
                self._handle_monitor(msg, sender)
            elif msg_type == "config":
                self._handle_config(msg, sender)
            elif msg_type == "status":
                self._handle_status(msg, sender)
            elif msg_type == "command":
                self._handle_command(msg, sender)
            elif msg_type == "alert":
                self._handle_alert(msg, sender)
            else:
                self.logger.warning(f"未知消息类型: {msg_type}")
                self.send(sender, {"status": "error", "message": f"未知消息类型: {msg_type}"})
        
        except Exception as e:
            self.logger.error(f"处理MCP请求失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
    
    def _handle_initialize(self, msg: Dict[str, Any], sender: str):
        """
        处理初始化消息
        """
        self.agent_id = msg.get("agent_id", "mcp_default")
        config = msg.get("config", {})
        
        # 可以在这里根据配置初始化特定的MCP能力
        if self.mcp_capability and hasattr(self.mcp_capability, "initialize"):
            try:
                self.mcp_capability.initialize(config)
            except Exception as e:
                self.logger.error(f"初始化MCP能力配置失败: {e}")
        
        self.send(sender, {"status": "success", "agent_id": self.agent_id})
    
    def _handle_control(self, msg: Dict[str, Any], sender: str):
        """
        处理控制命令
        """
        control_type = msg.get("control_type")
        target = msg.get("target")
        parameters = msg.get("parameters", {})
        
        if not control_type or not target:
            self.send(sender, {"status": "error", "message": "缺少必要参数"})
            return
        
        try:
            if self.mcp_capability and hasattr(self.mcp_capability, "control"):
                result = self.mcp_capability.control(
                    control_type=control_type,
                    target=target,
                    parameters=parameters,
                    agent_id=self.agent_id
                )
                self.send(sender, {"status": "success", "result": result})
            else:
                # 基础控制逻辑
                result = self._basic_control(control_type, target, parameters)
                self.send(sender, {"status": "success", "result": result})
        except Exception as e:
            self.logger.error(f"执行控制命令失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
    
    def _handle_monitor(self, msg: Dict[str, Any], sender: str):
        """
        处理监控请求
        """
        monitor_type = msg.get("monitor_type", "all")
        targets = msg.get("targets", [])
        
        try:
            if self.mcp_capability and hasattr(self.mcp_capability, "monitor"):
                results = self.mcp_capability.monitor(
                    monitor_type=monitor_type,
                    targets=targets
                )
                self.send(sender, {"status": "success", "results": results})
            else:
                # 基础监控逻辑
                results = self._basic_monitor(monitor_type, targets)
                self.send(sender, {"status": "success", "results": results})
        except Exception as e:
            self.logger.error(f"执行监控失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
    
    def _handle_config(self, msg: Dict[str, Any], sender: str):
        """
        处理配置管理
        """
        config_type = msg.get("config_type")
        action = msg.get("action", "get")
        config_data = msg.get("data", {})
        
        try:
            if self.mcp_capability and hasattr(self.mcp_capability, "configure"):
                result = self.mcp_capability.configure(
                    config_type=config_type,
                    action=action,
                    config_data=config_data
                )
                self.send(sender, {"status": "success", "result": result})
            else:
                # 基础配置逻辑
                result = self._basic_config(config_type, action, config_data)
                self.send(sender, {"status": "success", "result": result})
        except Exception as e:
            self.logger.error(f"配置管理失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
    
    def _handle_status(self, msg: Dict[str, Any], sender: str):
        """
        处理状态查询
        """
        components = msg.get("components", ["all"])
        
        try:
            if self.mcp_capability and hasattr(self.mcp_capability, "get_status"):
                status = self.mcp_capability.get_status(components)
                self.send(sender, {"status": "success", "status": status})
            else:
                # 基础状态查询
                status = self._basic_status(components)
                self.send(sender, {"status": "success", "status": status})
        except Exception as e:
            self.logger.error(f"获取状态失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
    
    def _handle_command(self, msg: Dict[str, Any], sender: str):
        """
        处理通用命令
        """
        command = msg.get("command")
        args = msg.get("args", [])
        kwargs = msg.get("kwargs", {})
        
        if not command:
            self.send(sender, {"status": "error", "message": "缺少命令"})
            return
        
        try:
            if self.mcp_capability and hasattr(self.mcp_capability, "execute_command"):
                result = self.mcp_capability.execute_command(
                    command=command,
                    args=args,
                    kwargs=kwargs
                )
                self.send(sender, {"status": "success", "result": result})
            else:
                # 基础命令执行
                result = self._basic_command(command, args, kwargs)
                self.send(sender, {"status": "success", "result": result})
        except Exception as e:
            self.logger.error(f"执行命令失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
    
    def _handle_alert(self, msg: Dict[str, Any], sender: str):
        """
        处理告警消息
        """
        alert_type = msg.get("alert_type")
        severity = msg.get("severity", "info")
        message = msg.get("message")
        data = msg.get("data", {})
        
        try:
            if self.mcp_capability and hasattr(self.mcp_capability, "process_alert"):
                result = self.mcp_capability.process_alert(
                    alert_type=alert_type,
                    severity=severity,
                    message=message,
                    data=data
                )
                self.send(sender, {"status": "success", "result": result})
            else:
                # 基础告警处理
                self.logger.warning(f"[告警] [{severity}] {alert_type}: {message}")
                self.send(sender, {"status": "success", "processed": True})
        except Exception as e:
            self.logger.error(f"处理告警失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
    
    # 基础实现方法
    def _basic_control(self, control_type: str, target: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        基础控制逻辑
        """
        return {
            "control_type": control_type,
            "target": target,
            "parameters": parameters,
            "message": "基础控制执行"
        }
    
    def _basic_monitor(self, monitor_type: str, targets: List[str]) -> List[Dict[str, Any]]:
        """
        基础监控逻辑
        """
        return [
            {
                "target": target,
                "status": "unknown",
                "timestamp": "now"
            } for target in targets
        ]
    
    def _basic_config(self, config_type: str, action: str, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        基础配置逻辑
        """
        return {
            "config_type": config_type,
            "action": action,
            "data": config_data
        }
    
    def _basic_status(self, components: List[str]) -> Dict[str, Any]:
        """
        基础状态查询
        """
        return {
            "status": "running",
            "components": components,
            "timestamp": "now"
        }
    
    def _basic_command(self, command: str, args: List[Any], kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        基础命令执行
        """
        return {
            "command": command,
            "args": args,
            "kwargs": kwargs,
            "result": "command executed"
        }
