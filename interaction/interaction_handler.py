import logging
import traceback
from typing import Dict, Any, Optional
from .common import (
    UserInputDTO,
    SystemResponseDTO,
    IntentRecognitionResultDTO,
    DialogStateDTO,
    IntentType
)
from .capabilities.capability_manager import capability_registry
from .capabilities.user_input_manager.interface import IUserInputManagerCapability
from .capabilities.intent_recognition_manager.interface import IIntentRecognitionManagerCapability
from .capabilities.dialog_state_manager.interface import IDialogStateManagerCapability
from .capabilities.task_draft_manager.interface import ITaskDraftManagerCapability
from .capabilities.task_query_manager.interface import ITaskQueryManagerCapability
from .capabilities.task_control_manager.interface import ITaskControlManagerCapability
from .capabilities.schedule_manager.interface import IScheduleManagerCapability
from .capabilities.task_execution_manager.interface import ITaskExecutionManagerCapability
from .capabilities.system_response_manager.interface import ISystemResponseManagerCapability

# 初始化logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class InteractionHandler:
    """交互处理器 - 负责按顺序调用各个能力，并传递上下文"""
    
    def __init__(self):
        """初始化交互处理器
        """
        self.registry = capability_registry
    
    def handle_user_input(self, input: UserInputDTO) -> SystemResponseDTO:
        """处理用户输入
        
        Args:
            input: 用户输入DTO
            
        Returns:
            系统响应DTO
        """
        # 1. 用户输入管理
        try:
            user_input_manager = self.registry.get_capability("user_input", IUserInputManagerCapability)
            session_state = user_input_manager.process_input(input)
        except ValueError as e:
            # 用户输入能力未启用，直接跳过并返回兜底响应
            logger.error(f"User input capability is disabled: {e}")
            logger.debug(f"Error traceback: {traceback.format_exc()}")
            return self.fallback_response(input.session_id, "UserInput capability is disabled")
        except Exception as e:
            logger.error(f"Failed to process user input: {e}")
            logger.debug(f"Error traceback: {traceback.format_exc()}")
            return self.fallback_response(input.session_id, f"用户输入处理失败: {str(e)}")
        
        # 2. 意图识别
        intent_result: IntentRecognitionResultDTO
        try:
            intent_recognition_manager = self.registry.get_capability("intent_recognition", IIntentRecognitionManagerCapability)
            intent_result = intent_recognition_manager.recognize_intent(input)
        except ValueError as e:
            # 意图识别能力未启用，使用默认 fallback：视为闲聊
            logger.error(f"Intent recognition capability is disabled: {e}")
            logger.debug(f"Error traceback: {traceback.format_exc()}")
            intent_result = IntentRecognitionResultDTO(
                primary_intent=IntentType.IDLE,
                confidence=1.0,
                entities=[],
                raw_nlu_output={"original_utterance": input.utterance}
            )
        except Exception as e:
            # 能力存在但执行失败，使用默认 fallback：视为闲聊
            logger.error(f"Failed to recognize intent: {e}")
            logger.debug(f"Error traceback: {traceback.format_exc()}")
            intent_result = IntentRecognitionResultDTO(
                primary_intent=IntentType.IDLE,
                confidence=1.0,
                entities=[],
                raw_nlu_output={"original_utterance": input.utterance}
            )
        
        # 3. 加载/更新全局对话状态
        try:
            dialog_state_manager = self.registry.get_capability("dialog_state", IDialogStateManagerCapability)
            dialog_state = dialog_state_manager.get_or_create_dialog_state(input.session_id)
            dialog_state.current_intent = intent_result.intent
        except ValueError as e:
            # 对话状态管理能力未启用，直接返回兜底响应
            logger.error(f"Dialog state capability is disabled: {e}")
            logger.debug(f"Error traceback: {traceback.format_exc()}")
            return self.fallback_response(input.session_id, "DialogState capability is disabled")
        except Exception as e:
            logger.error(f"Failed to manage dialog state: {e}")
            logger.debug(f"Error traceback: {traceback.format_exc()}")
            return self.fallback_response(input.session_id, f"对话状态管理失败: {str(e)}")
        
        # 4. 分发到对应业务管理器（路由）
        result_data: Dict[str, Any] = {}
        
        try:
            match intent_result.intent:
                case IntentType.CREATE | IntentType.MODIFY:
                    try:
                        task_draft_manager = self.registry.get_capability("task_draft", ITaskDraftManagerCapability)
                        result_data = task_draft_manager.update_draft_from_intent(
                            dialog_state.active_task_draft, intent_result
                        )
                    except ValueError as e:
                        # 任务创建能力未启用，跳过并返回兜底响应
                        logger.error(f"Task draft capability is disabled: {e}")
                        logger.debug(f"Error traceback: {traceback.format_exc()}")
                        return self.fallback_response(input.session_id, "任务创建功能暂未开启")
                    except Exception as e:
                        logger.error(f"Failed to update draft from intent: {e}")
                        logger.debug(f"Error traceback: {traceback.format_exc()}")
                        return self.fallback_response(input.session_id, f"任务创建功能执行失败: {str(e)}")
                
                case IntentType.QUERY:
                    try:
                        task_query_manager = self.registry.get_capability("task_query", ITaskQueryManagerCapability)
                        result_data = task_query_manager.process_query_intent(
                            intent_result, input.user_id, dialog_state.last_mentioned_task_id
                        )
                    except ValueError as e:
                        # 任务查询能力未启用，跳过并返回兜底响应
                        logger.error(f"Task query capability is disabled: {e}")
                        logger.debug(f"Error traceback: {traceback.format_exc()}")
                        return self.fallback_response(input.session_id, "任务查询功能暂未开启")
                    except Exception as e:
                        logger.error(f"Failed to process query intent: {e}")
                        logger.debug(f"Error traceback: {traceback.format_exc()}")
                        return self.fallback_response(input.session_id, f"任务查询功能执行失败: {str(e)}")
                
                case IntentType.DELETE | IntentType.CANCEL | IntentType.PAUSE | IntentType.RESUME_TASK | IntentType.RETRY:
                    try:
                        task_control_manager = self.registry.get_capability("task_control", ITaskControlManagerCapability)
                        task_control_response = task_control_manager.handle_task_control(
                            intent_result, input, input.user_id, dialog_state, dialog_state.last_mentioned_task_id
                        )
                        # 将TaskControlResponseDTO对象转换为适合后续处理的字典格式
                        result_data = {
                            "response_text": task_control_response.message,
                            "success": task_control_response.success,
                            "task_id": task_control_response.task_id,
                            "operation": task_control_response.operation,
                            "data": task_control_response.data
                        }
                    except ValueError as e:
                        # 任务控制能力未启用，跳过并返回兜底响应
                        logger.error(f"Task control capability is disabled: {e}")
                        logger.debug(f"Error traceback: {traceback.format_exc()}")
                        return self.fallback_response(input.session_id, "任务控制功能暂未开启")
                    except Exception as e:
                        logger.error(f"Failed to handle task control: {e}")
                        logger.debug(f"Error traceback: {traceback.format_exc()}")
                        return self.fallback_response(input.session_id, f"任务控制功能执行失败: {str(e)}")
                
                case IntentType.SET_SCHEDULE:
                    try:
                        schedule_manager = self.registry.get_capability("schedule", IScheduleManagerCapability)
                        task_draft_manager = self.registry.get_capability("task_draft", ITaskDraftManagerCapability)
                        result_data = task_draft_manager.update_draft_from_intent(
                            dialog_state.active_task_draft, intent_result
                        )
                        # 这里可以添加调度逻辑
                    except ValueError as e:
                        # 定时任务或任务创建能力未启用，跳过并返回兜底响应
                        logger.error(f"Schedule or task draft capability is disabled: {e}")
                        logger.debug(f"Error traceback: {traceback.format_exc()}")
                        return self.fallback_response(input.session_id, "定时任务或任务创建功能暂未开启")
                    except Exception as e:
                        logger.error(f"Failed to process schedule intent: {e}")
                        logger.debug(f"Error traceback: {traceback.format_exc()}")
                        return self.fallback_response(input.session_id, f"定时任务或任务创建功能执行失败: {str(e)}")
                
                case IntentType.IDLE:
                    result_data = {"response_text": "好的，有需要随时告诉我！"}
                
                case _:
                    result_data = {"response_text": "我还不太明白，请换种说法？"}
        except Exception as e:
            logger.error(f"Failed to process business logic: {e}")
            logger.debug(f"Error traceback: {traceback.format_exc()}")
            return self.fallback_response(input.session_id, f"业务处理失败: {str(e)}")
        
        logger.info(f"处理结果: {result_data}")
        # 5. 执行任务（如果是新建/修改且已确认）
        if (result_data.get("should_execute", False) and
            hasattr(result_data.get("task_draft", {}), "status") and
            result_data["task_draft"].status == "SUBMITTED"):
            try:
                task_execution_manager = self.registry.get_capability("task_execution", ITaskExecutionManagerCapability)
                exec_context = task_execution_manager.execute_task(
                    result_data["task_draft"].draft_id,
                    result_data["task_draft"].parameters,
                    result_data["task_draft"].task_type,
                    input.user_id
                )
                dialog_state.active_task_execution = exec_context.task_id
                result_data["execution_context"] = exec_context
            except ValueError as e:
                # 任务执行能力未启用，跳过并返回兜底响应
                logger.error(f"Task execution capability is disabled: {e}")
                logger.debug(f"Error traceback: {traceback.format_exc()}")
                return self.fallback_response(input.session_id, "任务执行功能暂未开启")
            except Exception as e:
                logger.error(f"Failed to execute task: {e}")
                logger.debug(f"Error traceback: {traceback.format_exc()}")
                return self.fallback_response(input.session_id, f"任务执行失败: {str(e)}")
        
        # 6. 生成系统响应
        try:
            system_response_manager = self.registry.get_capability("system_response", ISystemResponseManagerCapability)
            response = system_response_manager.generate_response(
                input.session_id,
                result_data.get("response_text", ""),
                requires_input=result_data.get("requires_input", False),
                awaiting_slot=result_data.get("awaiting_slot"),
                display_data=result_data.get("display_data")
            )
            # 持久化状态
            dialog_state_manager.update_dialog_state(dialog_state)
            return response
        except ValueError as e:
            # 系统响应生成能力未启用，直接返回兜底响应
            logger.error(f"System response capability is disabled: {e}")
            logger.debug(f"Error traceback: {traceback.format_exc()}")
            return self.fallback_response(input.session_id, "系统响应生成功能暂未开启")
        except Exception as e:
            logger.error(f"Failed to generate system response: {e}")
            logger.debug(f"Error traceback: {traceback.format_exc()}")
            return self.fallback_response(input.session_id, f"响应生成失败: {str(e)}")
    
    def fallback_response(self, session_id: str, msg: str) -> SystemResponseDTO:
        """生成兜底响应
        
        Args:
            msg: 兜底消息
            
        Returns:
            系统响应DTO
        """
        from .common import SystemResponseDTO
        return SystemResponseDTO(
            session_id=session_id,
            response_text=msg,
            requires_input=False
        )
