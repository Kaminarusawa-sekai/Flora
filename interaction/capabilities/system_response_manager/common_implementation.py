from typing import Dict, Any, Optional, List
from .interface import ISystemResponseManager
from ...common import (
    SystemResponseDTO,
    SuggestedActionDTO,
    ActionType,
    TaskStatusSummary
)
from tasks.capabilities import get_capability
from tasks.capabilities.llm.interface import ILLMCapability

class CommonSystemResponseManager(ISystemResponseManager):
    """系统响应管理器 - 统一生成系统响应，包括文本和结构化数据"""
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化系统响应管理器"""
        self.config = config
        # 获取LLM能力
        self.llm = get_capability("llm", expected_type=ILLMCapability)
    
    def shutdown(self) -> None:
        """关闭系统响应管理器"""
        pass
    
    def get_capability_type(self) -> str:
        """返回能力类型"""
        return "response_generation"
    
    def generate_response(self, session_id: str, response_text: str, 
                         suggested_actions: List[SuggestedActionDTO] = None, 
                         task_status: Optional[TaskStatusSummary] = None, 
                         requires_input: bool = False, 
                         awaiting_slot: Optional[str] = None, 
                         display_data: Optional[Dict[str, Any]] = None) -> SystemResponseDTO:
        """生成系统响应
        
        Args:
            session_id: 会话ID
            response_text: 响应文本
            suggested_actions: 建议操作列表
            task_status: 任务状态摘要
            requires_input: 是否需要用户输入
            awaiting_slot: 正在等待的槽位
            display_data: 结构化展示数据
            
        Returns:
            系统响应DTO
        """
        return SystemResponseDTO(
            session_id=session_id,
            response_text=response_text,
            suggested_actions=suggested_actions or [],
            task_status=task_status,
            requires_input=requires_input,
            awaiting_slot=awaiting_slot,
            display_data=display_data
        )
    
    def generate_task_creation_response(self, session_id: str, task_id: str, task_title: str) -> SystemResponseDTO:
        """生成任务创建成功的响应
        
        Args:
            session_id: 会话ID
            task_id: 任务ID
            task_title: 任务标题
            
        Returns:
            系统响应DTO
        """
        response_text = f"任务 '{task_title}' 已成功创建，任务ID: {task_id}"
        
        # 生成建议操作
        suggested_actions = [
            SuggestedActionDTO(
                type=ActionType.QUERY,
                title="查看任务状态",
                payload=f"QUERY_TASK_{task_id}"
            ),
            SuggestedActionDTO(
                type=ActionType.CANCEL,
                title="取消任务",
                payload=f"CANCEL_TASK_{task_id}"
            )
        ]
        
        return self.generate_response(
            session_id=session_id,
            response_text=response_text,
            suggested_actions=suggested_actions,
            requires_input=False
        )
    
    def generate_task_status_response(self, session_id: str, task_status_info: Dict[str, Any]) -> SystemResponseDTO:
        """生成任务状态响应
        
        Args:
            session_id: 会话ID
            task_status_info: 任务状态信息
            
        Returns:
            系统响应DTO
        """
        task_id = task_status_info["task_id"]
        status = task_status_info["status"]
        title = task_status_info["title"]
        progress = task_status_info["progress"]
        
        # 生成响应文本
        if status == "RUNNING":
            response_text = f"任务 '{title}' 正在运行中，进度: {int(progress * 100)}%"
        elif status == "COMPLETED":
            response_text = f"任务 '{title}' 已成功完成"
        elif status == "FAILED":
            response_text = f"任务 '{title}' 执行失败，请检查日志"
        elif status == "PAUSED":
            response_text = f"任务 '{title}' 已暂停"
        elif status == "CANCELLED":
            response_text = f"任务 '{title}' 已取消"
        else:
            response_text = f"任务 '{title}' 状态: {status}"
        
        # 生成建议操作
        suggested_actions = []
        if status == "RUNNING":
            suggested_actions.append(
                SuggestedActionDTO(
                    type=ActionType.PAUSE,
                    title="暂停任务",
                    payload=f"PAUSE_TASK_{task_id}"
                )
            )
        elif status == "PAUSED":
            suggested_actions.append(
                SuggestedActionDTO(
                    type=ActionType.RESUME,
                    title="恢复任务",
                    payload=f"RESUME_TASK_{task_id}"
                )
            )
        
        suggested_actions.extend([
            SuggestedActionDTO(
                type=ActionType.QUERY,
                title="查看详细日志",
                payload=f"QUERY_TASK_LOGS_{task_id}"
            ),
            SuggestedActionDTO(
                type=ActionType.CANCEL,
                title="取消任务",
                payload=f"CANCEL_TASK_{task_id}"
            )
        ])
        
        # 生成任务状态摘要
        task_status = TaskStatusSummary(
            task_id=task_id,
            status=status,
            progress=progress,
            message=response_text
        )
        
        return self.generate_response(
            session_id=session_id,
            response_text=response_text,
            suggested_actions=suggested_actions,
            task_status=task_status,
            requires_input=False
        )
    
    def generate_fill_slot_response(self, session_id: str, missing_slots: List[str], draft_id: str) -> SystemResponseDTO:
        """生成填槽请求响应
        
        Args:
            session_id: 会话ID
            missing_slots: 缺失的槽位列表
            draft_id: 草稿ID
            
        Returns:
            系统响应DTO
        """
        if missing_slots:
            current_slot = missing_slots[0]
            response_text = f"请提供 {self._get_slot_display_name(current_slot)}"
            
            # 生成建议操作
            suggested_actions = [
                SuggestedActionDTO(
                    type=ActionType.CANCEL,
                    title="取消任务",
                    payload=f"CANCEL_DRAFT_{draft_id}"
                )
            ]
            
            return self.generate_response(
                session_id=session_id,
                response_text=response_text,
                suggested_actions=suggested_actions,
                requires_input=True,
                awaiting_slot=current_slot
            )
        
        # 如果没有缺失槽位，请求确认
        response_text = "请确认任务信息是否正确？"
        
        # 生成建议操作
        suggested_actions = [
            SuggestedActionDTO(
                type=ActionType.CONFIRM,
                title="确认执行",
                payload=f"CONFIRM_DRAFT_{draft_id}"
            ),
            SuggestedActionDTO(
                type=ActionType.CANCEL,
                title="取消任务",
                payload=f"CANCEL_DRAFT_{draft_id}"
            ),
            SuggestedActionDTO(
                type=ActionType.MODIFY,
                title="修改信息",
                payload=f"MODIFY_DRAFT_{draft_id}"
            )
        ]
        
        return self.generate_response(
            session_id=session_id,
            response_text=response_text,
            suggested_actions=suggested_actions,
            requires_input=True
        )
    
    def generate_query_response(self, session_id: str, query_result: Dict[str, Any]) -> SystemResponseDTO:
        """生成查询结果响应
        
        Args:
            session_id: 会话ID
            query_result: 查询结果
            
        Returns:
            系统响应DTO
        """
        total = query_result.get("total", 0)
        tasks = query_result.get("tasks", [])
        
        if total == 0:
            response_text = "没有找到匹配的任务"
            return self.generate_response(
                session_id=session_id,
                response_text=response_text,
                requires_input=False
            )
        
        response_text = f"找到 {total} 个任务"
        
        # 生成建议操作
        suggested_actions = [
            SuggestedActionDTO(
                type=ActionType.QUERY,
                title="查看详情",
                payload=f"QUERY_TASK_DETAIL_{tasks[0]['task_id']}"
            ) if tasks else None
        ]
        
        # 过滤掉None值
        suggested_actions = [action for action in suggested_actions if action]
        
        return self.generate_response(
            session_id=session_id,
            response_text=response_text,
            suggested_actions=suggested_actions,
            requires_input=False,
            display_data=query_result
        )
    
    def generate_error_response(self, session_id: str, error_message: str) -> SystemResponseDTO:
        """生成错误响应
        
        Args:
            session_id: 会话ID
            error_message: 错误信息
            
        Returns:
            系统响应DTO
        """
        # 生成响应文本
        response_text = f"抱歉，发生了错误：{error_message}"
        
        # 生成建议操作
        suggested_actions = [
            SuggestedActionDTO(
                type=ActionType.RETRY,
                title="重试",
                payload="RETRY_OPERATION"
            ),
            SuggestedActionDTO(
                type=ActionType.CANCEL,
                title="取消",
                payload="CANCEL_OPERATION"
            )
        ]
        
        return self.generate_response(
            session_id=session_id,
            response_text=response_text,
            suggested_actions=suggested_actions,
            requires_input=False
        )
    
    def generate_idle_response(self, session_id: str, idle_message: str) -> SystemResponseDTO:
        """生成闲聊模式响应
        
        Args:
            session_id: 会话ID
            idle_message: 闲聊消息
            
        Returns:
            系统响应DTO
        """
        return self.generate_response(
            session_id=session_id,
            response_text=idle_message,
            requires_input=True
        )
    
    def _get_slot_display_name(self, slot_name: str) -> str:
        """获取槽位的显示名称
        
        Args:
            slot_name: 槽位名称
            
        Returns:
            槽位的显示名称
        """
        # 槽位名称映射，实际应该从配置或数据库中获取
        slot_display_names = {
            "task_name": "任务名称",
            "target_url": "目标网址",
            "start_time": "开始时间",
            "end_time": "结束时间",
            "frequency": "执行频率",
            "max_runs": "最大执行次数"
        }
        
        return slot_display_names.get(slot_name, slot_name)