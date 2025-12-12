from typing import Dict, Any, Optional
from dataclasses import dataclass
from .common import (
    UserInputDTO,
    SystemResponseDTO,
    IntentRecognitionResultDTO,
    DialogStateDTO,
    IntentType
)


@dataclass
class DialogueOrchestratorConfig:
    """对话编排器配置"""
    enabled_managers: Dict[str, bool]


class DialogueOrchestrator:
    """对话编排器 - 负责按顺序调用各个Manager，并传递上下文"""
    
    def __init__(self, config: DialogueOrchestratorConfig, managers: Dict[str, Any]):
        """初始化对话编排器
        
        Args:
            config: 对话编排器配置
            managers: Manager实例字典
        """
        self.config = config
        self.managers = managers
    
    def handle_user_input(self, input: UserInputDTO) -> SystemResponseDTO:
        """处理用户输入
        
        Args:
            input: 用户输入DTO
            
        Returns:
            系统响应DTO
        """
        # 1. 用户输入管理
        if not self.config.enabled_managers.get("userInput", False):
            return self.fallback_response("UserInputManager is disabled")
        
        try:
            session_state = self.managers["userInput"].process_input(input)
        except Exception as e:
            return self.fallback_response(f"用户输入处理失败: {str(e)}")
        
        # 2. 意图识别
        intent_result: IntentRecognitionResultDTO
        if self.config.enabled_managers.get("intentRecognition", False):
            try:
                intent_result = self.managers["intentRecognition"].recognize_intent(input)
            except Exception as e:
                # 默认 fallback：视为闲聊
                intent_result = IntentRecognitionResultDTO(
                    intent=IntentType.IDLE,
                    confidence=1.0,
                    entities=[],
                    raw_input=input.utterance
                )
        else:
            # 默认 fallback：视为闲聊
            intent_result = IntentRecognitionResultDTO(
                intent=IntentType.IDLE,
                confidence=1.0,
                entities=[],
                raw_input=input.utterance
            )
        
        # 3. 加载/更新全局对话状态
        if "dialogState" not in self.managers:
            return self.fallback_response("DialogStateManager is not registered")
        
        try:
            dialog_state = self.managers["dialogState"].get_or_create_dialog_state(input.session_id)
            dialog_state.current_intent = intent_result.intent
        except Exception as e:
            return self.fallback_response(f"对话状态管理失败: {str(e)}")
        
        # 4. 分发到对应业务管理器（路由）
        result_data: Dict[str, Any] = {}
        
        try:
            match intent_result.intent:
                case IntentType.CREATE | IntentType.MODIFY:
                    if self.config.enabled_managers.get("taskDraft", False):
                        result_data = self.managers["taskDraft"].update_draft_from_intent(
                            dialog_state.active_task_draft, intent_result
                        )
                    else:
                        return self.fallback_response("任务创建功能暂未开启")
                
                case IntentType.QUERY:
                    if self.config.enabled_managers.get("taskQuery", False):
                        result_data = self.managers["taskQuery"].process_query_intent(
                            intent_result, input.user_id, dialog_state.last_mentioned_task_id
                        )
                    else:
                        return self.fallback_response("任务查询功能暂未开启")
                
                case IntentType.DELETE | IntentType.CANCEL | IntentType.PAUSE | IntentType.RESUME_TASK | IntentType.RETRY:
                    if self.config.enabled_managers.get("taskControl", False):
                        result_data = self.managers["taskControl"].handle_task_control(
                            intent_result, input.user_id, dialog_state.last_mentioned_task_id
                        )
                    else:
                        return self.fallback_response("任务控制功能暂未开启")
                
                case IntentType.SET_SCHEDULE:
                    if self.config.enabled_managers.get("schedule", False):
                        if self.config.enabled_managers.get("taskDraft", False):
                            result_data = self.managers["taskDraft"].update_draft_from_intent(
                                dialog_state.active_task_draft, intent_result
                            )
                            # 这里可以添加调度逻辑
                        else:
                            return self.fallback_response("任务创建功能暂未开启")
                    else:
                        return self.fallback_response("定时任务功能暂未开启")
                
                case IntentType.IDLE:
                    result_data = {"response_text": "好的，有需要随时告诉我！"}
                
                case _:
                    result_data = {"response_text": "我还不太明白，请换种说法？"}
        except Exception as e:
            return self.fallback_response(f"业务处理失败: {str(e)}")
        
        # 5. 执行任务（如果是新建/修改且已确认）
        if (self.config.enabled_managers.get("taskExecution", False) and
            result_data.get("should_execute", False) and
            hasattr(result_data.get("task_draft", {}), "status") and
            result_data["task_draft"].status == "SUBMITTED"):
            try:
                exec_context = self.managers["taskExecution"].execute_task(
                    result_data["task_draft"].draft_id,
                    result_data["task_draft"].parameters,
                    result_data["task_draft"].task_type,
                    input.user_id
                )
                dialog_state.active_task_execution = exec_context.task_id
                result_data["execution_context"] = exec_context
            except Exception as e:
                return self.fallback_response(f"任务执行失败: {str(e)}")
        
        # 6. 生成系统响应
        if self.config.enabled_managers.get("systemResponse", False):
            try:
                response = self.managers["systemResponse"].generate_response(
                    input.session_id,
                    result_data.get("response_text", ""),
                    requires_input=result_data.get("requires_input", False),
                    awaiting_slot=result_data.get("awaiting_slot"),
                    display_data=result_data.get("display_data")
                )
                # 持久化状态
                self.managers["dialogState"].update_dialog_state(dialog_state)
                return response
            except Exception as e:
                return self.fallback_response(f"响应生成失败: {str(e)}")
        else:
            return self.fallback_response("[响应生成器已关闭]")
    
    def fallback_response(self, msg: str) -> SystemResponseDTO:
        """生成兜底响应
        
        Args:
            msg: 兜底消息
            
        Returns:
            系统响应DTO
        """
        from .common import SystemResponseDTO
        return SystemResponseDTO(
            response_text=msg,
            requires_input=False
        )
