from tkinter.filedialog import dialogstates
import logging
import traceback
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from common import (
    UserInputDTO,
    SystemResponseDTO,
    IntentRecognitionResultDTO,
    DialogStateDTO,
    IntentType,
    DialogTurn
)
from capabilities.capability_manager import capability_registry
from capabilities.user_input_manager.interface import IUserInputManagerCapability
from capabilities.intent_recognition_manager.interface import IIntentRecognitionManagerCapability
from capabilities.dialog_state_manager.interface import IDialogStateManagerCapability
from capabilities.task_draft_manager.interface import ITaskDraftManagerCapability
from capabilities.task_query_manager.interface import ITaskQueryManagerCapability
from capabilities.task_control_manager.interface import ITaskControlManagerCapability
from capabilities.schedule_manager.interface import IScheduleManagerCapability
from capabilities.task_execution_manager.interface import ITaskExecutionManagerCapability
from capabilities.system_response_manager.interface import ISystemResponseManagerCapability

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
        """处理用户输入（同步版本）
        
        Args:
            input: 用户输入DTO
            
        Returns:
            系统响应DTO
        """
        # 1. 用户输入管理
        try:
            user_input_manager = self.registry.get_capability("user_input", IUserInputManagerCapability)
            session_state = user_input_manager.process_input(input)
            input.utterance=session_state["enhanced_utterance"]
        except ValueError as e:
            # 用户输入能力未启用，直接跳过并返回兜底响应
            logger.error(f"User input capability is disabled: {e}")
            logger.debug(f"Error traceback: {traceback.format_exc()}")
            return self.fallback_response(input.session_id, "UserInput capability is disabled")
        except Exception as e:
            logger.error(f"Failed to process user input: {e}")
            logger.debug(f"Error traceback: {traceback.format_exc()}")
            return self.fallback_response(input.session_id, f"用户输入处理失败: {str(e)}")
        


        # =========================================================================
        # 🔥 【新增逻辑】 状态拦截器 (State Interceptor)
        # 如果处于“待确认”状态，且用户意图是“确认/肯定”，则直接短路进执行
        # =========================================================================
        
        # 定义需要拦截的确认意图 (需要你在 IntentType 里定义 CONFIRM/POSITIVE)
        is_confirm_intent = "is_confirm_intent"
        # 定义拒绝/取消意图
        is_cancel_intent = "is_cancel_intent"
        
        # 这一步将决定是否跳过第4步的路由
        bypass_routing = False 
        
        # 默认结果容器
        result_data: Dict[str, Any] = {}

        if dialog_state.waiting_for_confirmation:
            if is_confirm_intent:
                yield "thought", {"message": f"检测到确认意图，执行{dialog_state.confirmation_action}动作"}
                
                if dialog_state.confirmation_action == "SUBMIT_DRAFT" and dialog_state.active_task_draft:
                    # 1. 调用TaskDraftManager提交草稿
                    task_draft_manager = self.registry.get_capability("task_draft", ITaskDraftManagerCapability)
                    submitted_draft = task_draft_manager.submit_draft(dialog_state.active_task_draft)
                    
                    # 2. 调用DialogStateManager更新对话状态
                    dialog_state_manager = self.registry.get_capability("dialog_state", IDialogStateManagerCapability)
                    dialog_state = dialog_state_manager.clear_active_draft(dialog_state)
                    
                    # 3. 构造返回数据
                    result_data = {
                        "should_execute": True,
                        "task_draft": submitted_draft,
                        "response_text": "正在执行..."
                    }
                    bypass_routing = True
                elif dialog_state.confirmation_action == "DELETE_TASK":
                    # 执行删除任务逻辑
                    task_id = dialog_state.confirmation_payload.get("task_id")
                    task_control_manager = self.registry.get_capability("task_control", ITaskControlManagerCapability)
                    task_control_manager.delete_task(task_id)
                    # 更新对话状态
                    dialog_state.waiting_for_confirmation = False
                    dialog_state.confirmation_action = None
                    dialog_state.confirmation_payload = None
                    result_data = {
                        "response_text": f"任务 {task_id} 已删除"
                    }
                    bypass_routing = True
                
            elif is_cancel_intent:
                yield "thought", {"message": "用户取消了待确认的操作"}
                
                # 调用DialogStateManager清除等待确认状态
                dialog_state_manager = self.registry.get_capability("dialog_state", IDialogStateManagerCapability)
                dialog_state = dialog_state_manager.clear_waiting_for_confirmation(dialog_state)
                
                # 如果有活跃草稿，调用TaskDraftManager取消草稿
                if dialog_state.active_task_draft:
                    task_draft_manager = self.registry.get_capability("task_draft", ITaskDraftManagerCapability)
                    cancelled_draft = task_draft_manager.cancel_draft(dialog_state.active_task_draft)
                    dialog_state = dialog_state_manager.clear_active_draft(dialog_state)
                    
                # 构造返回数据
                result_data = {"response_text": "已取消操作"}
                bypass_routing = True
            
            else:
                # 处于等待确认状态，但用户说了别的（比如“天气怎么样”），
                # 策略A：认为这是中断，继续往下走常规路由 (waiting_for_confirmation 保持 True 或 False 看业务需求)
                # 策略B：提示用户必须回答是或否
                pass


        # 2. 意图识别（如果是确认状态直接看是不是确认意图，然后再走正式逻辑）
        intent_result: IntentRecognitionResultDTO
        try:
            intent_recognition_manager = self.registry.get_capability("intent_recognition", IIntentRecognitionManagerCapability)
            intent_result = intent_recognition_manager.recognize_intent(input)
        except ValueError as e:
            # 意图识别能力未启用，使用默认 fallback：视为闲聊
            logger.error(f"Intent recognition capability is disabled: {e}")
            logger.debug(f"Error traceback: {traceback.format_exc()}")
            intent_result = IntentRecognitionResultDTO(
                primary_intent=IntentType.IDLE_CHAT,
                confidence=1.0,
                entities=[],
                raw_nlu_output={"original_utterance": input.utterance}
            )
        except Exception as e:
            # 能力存在但执行失败，使用默认 fallback：视为闲聊
            logger.error(f"Failed to recognize intent: {e}")
            logger.debug(f"Error traceback: {traceback.format_exc()}")
            intent_result = IntentRecognitionResultDTO(
                primary_intent=IntentType.IDLE_CHAT,
                confidence=1.0,
                entities=[],
                raw_nlu_output={"original_utterance": input.utterance}
            )
        
        # 3. 补全 user_id（如果为空）
        if not input.user_id:
            # 生成临时 user_id
            input.user_id = f"temp_{input.session_id}"
        
        # 4. 加载/更新全局对话状态
        try:
            dialog_state_manager = self.registry.get_capability("dialog_state", IDialogStateManagerCapability)
            dialog_state = dialog_state_manager.get_or_create_dialog_state(input.session_id, input.user_id)
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
                case IntentType.CREATE_TASK | IntentType.MODIFY_TASK:
                    try:
                        task_draft_manager = self.registry.get_capability("task_draft", ITaskDraftManagerCapability)
                        
                        # 如果是CREATE意图且没有活动草稿，先创建新草稿
                        if intent_result.intent == IntentType.CREATE_TASK and not dialog_state.active_task_draft:
                            dialog_state.active_task_draft = task_draft_manager.create_draft(
                                task_type="default",
                                session_id=dialog_state.session_id,
                                user_id=input.user_id
                            )
                        
                        result_data = task_draft_manager.update_draft_from_intent(
                            dialog_state.active_task_draft, intent_result
                        )
                        
                        # 获取 Manager 评估的结果
                        should_execute = result_data.get("should_execute", False)
                        
                        # 关键点：同步状态给 DialogState
                        if should_execute:
                            # 如果 LLM 觉得可以了，开启“待确认”开关
                            dialog_state.waiting_for_confirmation = True
                            dialog_state.confirmation_action = "SUBMIT_DRAFT"
                            
                            # 可以在这里把 LLM 生成的确认摘要存一下
                            draft = result_data.get("task_draft")
                            dialog_state.confirmation_payload = draft.model_dump() if draft else None
                            
                            # 🔥【关键修改点】🔥
                            # 拦截执行：强制将本次结果设为不执行，因为需要等待下一轮用户确认
                            result_data["should_execute"] = False
                    except ValueError as e:
                        # 任务创建能力未启用，跳过并返回兜底响应
                        logger.error(f"Task draft capability is disabled: {e}")
                        logger.debug(f"Error traceback: {traceback.format_exc()}")
                        return self.fallback_response(input.session_id, "任务创建功能暂未开启")
                    except Exception as e:
                        logger.error(f"Failed to update draft from intent: {e}")
                        logger.debug(f"Error traceback: {traceback.format_exc()}")
                        return self.fallback_response(input.session_id, f"任务创建功能执行失败: {str(e)}")
                
                case IntentType.QUERY_TASK:
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
                
                case IntentType.DELETE_TASK | IntentType.CANCEL_TASK | IntentType.PAUSE_TASK | IntentType.RESUME_TASK | IntentType.RETRY_TASK:
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
                
                case IntentType.IDLE_CHAT:
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
    
    async def stream_handle_user_input(self, input: UserInputDTO):
        """处理用户输入（异步流式版本）
        
        Args:
            input: 用户输入DTO
            
        Yields:
            Tuple[str, Any]: (event_type, data) 事件类型和数据
        """
        # === 1. 用户输入管理 ===
        original_input = input.copy()
        try:
            user_input_manager = self.registry.get_capability("user_input", IUserInputManagerCapability)
            session_state = user_input_manager.process_input(input)
            input.utterance = session_state["enhanced_utterance"]
            yield "thought", {"message": "用户输入处理完成"}
        except ValueError as e:
            # 用户输入能力未启用，直接跳过并返回兜底响应
            logger.error(f"User input capability is disabled: {e}")
            logger.debug(f"Error traceback: {traceback.format_exc()}")
            yield "error", {"message": "UserInput capability is disabled"}
            return
        except Exception as e:
            logger.error(f"Failed to process user input: {e}")
            logger.debug(f"Error traceback: {traceback.format_exc()}")
            yield "error", {"message": f"用户输入处理失败: {str(e)}"}
            return
        
        # === 2. 补全 user_id（如果为空）===
        if not input.user_id:
            # 生成临时 user_id
            input.user_id = f"temp_{input.session_id}"
            yield "thought", {"message": "生成临时 user_id"}
        
        # === 3. 加载全局对话状态（必须先获取！）===
        try:
            dialog_state_manager = self.registry.get_capability("dialog_state", IDialogStateManagerCapability)
            dialog_state = dialog_state_manager.get_or_create_dialog_state(input.session_id, input.user_id)
        
            # 检查会话名称和描述，如果为空则生成
            if not dialog_state.name or not dialog_state.description:
                session_info = dialog_state_manager.generate_session_name(input.session_id, input.utterance)
                dialog_state = dialog_state_manager.update_dialog_state_fields(
                    dialog_state, 
                    name=session_info["name"], 
                    description=session_info["description"]
                )
                yield "thought", {"message": "生成会话名称和描述", "name": dialog_state.name, "description": dialog_state.description}
        
            yield "thought", {"message": "对话状态加载完成"}
            
        except Exception as e:
            logger.error(f"Failed to manage dialog state: {e}")
            logger.debug(f"Error traceback: {traceback.format_exc()}")
            yield "error", {"message": f"对话状态管理失败: {str(e)}"}
            return
        # =========================================================================
        # 🔥 【新增逻辑】 状态拦截器 (State Interceptor)
        # 如果处于“待确认”状态，且用户意图是“确认/肯定”，则直接短路进执行
        # =========================================================================
        
        intent_result: IntentRecognitionResultDTO
        # === 3. 智能意图识别：根据对话状态决定识别策略 ===
        intent_result = None
        special_intent = ""
        try:
            intent_recognition_manager = self.registry.get_capability("intent_recognition", IIntentRecognitionManagerCapability)

            if dialog_state.waiting_for_confirmation:
                # 【特殊状态】只先判断是否为特殊意图（CONFIRM/CANCEL/MODIFY）
                special_intent = intent_recognition_manager.judge_special_intent(original_input.utterance, dialog_state)
                
                yield "thought", {
                    "message": "处于等待确认状态，仅检查特殊意图",
                    "special_intent": special_intent
                }

                # 如果不是特殊意图（即用户说了无关内容，如“今天天气如何”）
                if special_intent not in ("CONFIRM", "CANCEL", "MODIFY"):
                    # 才 fallback 到完整意图识别
                    intent_result = intent_recognition_manager.recognize_intent(input)
                    dialog_state.current_intent = intent_result.primary_intent
                    yield "thought", {
                        "message": "非特殊意图，执行完整意图识别",
                        "primary_intent": intent_result.primary_intent.value
                    }
                else:
                    # 是特殊意图，不调用 recognize_intent，intent_result 保持 None
                    # 后续路由会因 bypass_routing 而跳过，所以安全
                    intent_result = IntentRecognitionResultDTO(
                        primary_intent=IntentType.IDLE_CHAT,  # 或 IDLE_CHAT，但实际不会用到
                        confidence=0.0,
                        entities=[],
                        raw_nlu_output={}
                    )
                    dialog_state.current_intent = IntentType.IDLE_CHAT  # 可选，或保留原值

            else:
                # 【正常状态】直接完整意图识别
                intent_result = intent_recognition_manager.recognize_intent(input)
                dialog_state.current_intent = intent_result.primary_intent

                
                yield "thought", {
                    "message": "正常状态，执行完整意图识别",
                    "primary_intent": intent_result.primary_intent.value,
                    "special_intent": special_intent  # 即使不在 waiting 状态，也可能识别出（但通常忽略）
                }

        except ValueError as e:
            # 意图识别能力未启用，使用默认 fallback：视为闲聊
            logger.error(f"Intent recognition capability is disabled: {e}")
            logger.debug(f"Error traceback: {traceback.format_exc()}")
            # fallback to idle chat
            intent_result = IntentRecognitionResultDTO(
                primary_intent=IntentType.IDLE_CHAT,
                confidence=1.0,
                entities=[],
                raw_nlu_output={"original_utterance": input.utterance}
            )
            dialog_state.current_intent = IntentType.IDLE_CHAT
            special_intent = ""
            yield "thought", {"message": "意图识别能力未启用，使用默认意图"}

        except Exception as e:
             # 能力存在但执行失败，使用默认 fallback：视为闲聊
            logger.error(f"Failed to recognize intent: {e}")
            logger.debug(f"Error traceback: {traceback.format_exc()}")
            intent_result = IntentRecognitionResultDTO(
                primary_intent=IntentType.IDLE_CHAT,
                confidence=1.0,
                entities=[],
                raw_nlu_output={"original_utterance": input.utterance}
            )
            dialog_state.current_intent = IntentType.IDLE_CHAT
            special_intent = ""
            yield "thought", {"message": "意图识别失败，使用默认意图"}

        # === 4. 【状态拦截器】处理特殊意图（CONFIRM / CANCEL / MODIFY）===
        bypass_routing = False
        result_data: Dict[str, Any] = {}

        if dialog_state.waiting_for_confirmation:
            is_confirm = (special_intent == "CONFIRM")
            is_cancel = (special_intent == "CANCEL")
            is_modify = (special_intent == "MODIFY")

            if is_confirm:
                yield "thought", {"message": f"检测到确认意图，执行 {dialog_state.confirmation_action} 动作"}

                if dialog_state.confirmation_action == "SUBMIT_DRAFT" and dialog_state.active_task_draft:
                    # 提交草稿（此处假设 submit_draft 返回的是已标记为 SUBMITTED 的草稿）
                    task_draft_manager = self.registry.get_capability("task_draft", ITaskDraftManagerCapability)
                    submitted_draft = task_draft_manager.submit_draft(dialog_state.active_task_draft)

                    # 【关键修改】将草稿状态设为“待执行”（或根据你的系统定义）
                    # 注意：submit_draft 内部应已设置 status = "SUBMITTED"
                    # 如果你需要额外状态如 "PENDING_EXECUTION"，可在 submit 后手动设置
                    # submitted_draft.status = "PENDING_EXECUTION"  # 如果需要

                    # 清除对话状态中的草稿和确认标志
                    dialog_state = dialog_state_manager.clear_active_draft(dialog_state)
                    
                    # 3. 构造返回数据
                    dialog_state.waiting_for_confirmation = False
                    dialog_state.confirmation_action = None
                    dialog_state.confirmation_payload = None

                    result_data = {
                        "should_execute": True,
                        "task_draft": submitted_draft,
                        "response_text": "正在执行任务..."
                    }
                    bypass_routing = True

                elif dialog_state.confirmation_action == "DELETE_TASK":
                     # 执行删除任务逻辑
                    task_id = dialog_state.confirmation_payload.get("task_id")
                    task_control_manager = self.registry.get_capability("task_control", ITaskControlManagerCapability)
                    task_control_manager.delete_task(task_id)
                    # 更新对话状态
                    dialog_state.waiting_for_confirmation = False
                    dialog_state.confirmation_action = None
                    dialog_state.confirmation_payload = None

                    result_data = {"response_text": f"任务 {task_id} 已删除"}
                    bypass_routing = True

            elif is_cancel:
                yield "thought", {"message": "用户取消了待确认的操作"}
                # 取消草稿（如果存在）
                if dialog_state.active_task_draft:
                    task_draft_manager = self.registry.get_capability("task_draft", ITaskDraftManagerCapability)
                    task_draft_manager.cancel_draft(dialog_state.active_task_draft)
                    dialog_state = dialog_state_manager.clear_active_draft(dialog_state)
                # 构造返回数据
                dialog_state.waiting_for_confirmation = False
                dialog_state.confirmation_action = None
                dialog_state.confirmation_payload = None
                result_data = {"response_text": "已取消操作"}
                bypass_routing = True

            elif is_modify:
                # 【可选】进入修改模式：不清除草稿，但退出 waiting_for_confirmation
                yield "thought", {"message": "用户要求修改草稿，返回编辑模式"}
                dialog_state.waiting_for_confirmation = False
                dialog_state.confirmation_action = None
                dialog_state.confirmation_payload = None
                # 不 bypass_routing，让后续 CREATE/MODIFY 逻辑继续处理
                # 所以 bypass_routing 保持 False

            else:
                # 用户在等待确认时说了无关内容（如“今天天气如何”）
                # 策略：视为中断，不清除状态，但继续走正常路由（可配置）
                # 这里选择不清除状态，让后续逻辑处理（比如闲聊）
                pass

        # === 5. 【条件跳过】如果已处理特殊意图，则跳过常规路由 ===
        if not bypass_routing:
            # === 5.1 常规意图路由 ===
            try:
                match intent_result.primary_intent:
                    case IntentType.CREATE_TASK | IntentType.MODIFY_TASK:
                        try:
                            task_draft_manager = self.registry.get_capability("task_draft", ITaskDraftManagerCapability)
                            
                            # 如果是CREATE意图且没有活动草稿，先创建新草稿
                            if intent_result.primary_intent == IntentType.CREATE_TASK and not dialog_state.active_task_draft:
                                dialog_state.active_task_draft = task_draft_manager.create_draft(
                                    task_type="default",  # 可以根据intent_result获取具体任务类型
                                    session_id=dialog_state.session_id,
                                    user_id=input.user_id  # 使用实际用户ID
                                )
                            
                            # 调用修改后的 Manager
                            result_data = task_draft_manager.update_draft_from_intent(
                                dialog_state.active_task_draft, intent_result
                            )

                            # --- 新增防御逻辑 ---
                            if not result_data.get("response_text"):
                                # 如果管理器没有返回回复文本（可能是因为配置缺失），给一个默认回复
                                result_data["response_text"] = (
                                    f"已识别任务类型为 {intent_result.entities[0].value if intent_result.entities else '未知'}，"
                                    "但系统缺少该任务的配置模板，无法继续引导。"
                                )
                                logger.warning("Empty response text from task_draft_manager. Check task configuration.")
                            # -------------------

                            # 获取 Manager 评估的结果
                            should_execute = result_data.get("should_execute", False)
                            
                            # 关键点：同步状态给 DialogState
                            if should_execute:
                                # 如果 LLM 觉得可以了，开启“待确认”开关
                                dialog_state.waiting_for_confirmation = True
                                dialog_state.confirmation_action = "SUBMIT_DRAFT"
                                
                                # 可以在这里把 LLM 生成的确认摘要存一下
                                draft = result_data.get("task_draft")
                                dialog_state.confirmation_payload = draft.model_dump() if draft else None
                                
                                # 🔥【关键修改点】🔥
                                # 拦截执行：强制将本次结果设为不执行，因为需要等待下一轮用户确认
                                result_data["should_execute"] = False
                                
                                yield "thought", {"message": "草稿已就绪，进入待确认状态，暂停执行"}
                            else:
                                yield "thought", {"message": "任务草稿更新完成，等待更多信息"}
                        except ValueError as e:
                            # 任务创建能力未启用，跳过并返回兜底响应
                            logger.error(f"Task draft capability is disabled: {e}")
                            logger.debug(f"Error traceback: {traceback.format_exc()}")
                            yield "error", {"message": "任务创建功能暂未开启"}
                            return
                        except Exception as e:
                            logger.error(f"Failed to update draft from intent: {e}")
                            logger.debug(f"Error traceback: {traceback.format_exc()}")
                            yield "error", {"message": f"任务创建功能执行失败: {str(e)}"}
                            return
                    
                    case IntentType.QUERY_TASK:
                        try:
                            task_query_manager = self.registry.get_capability("task_query", ITaskQueryManagerCapability)
                            result_data = task_query_manager.process_query_intent(
                                intent_result, input.user_id, dialog_state.last_mentioned_task_id
                            )
                            yield "thought", {"message": "任务查询完成"}
                        except ValueError as e:
                            # 任务查询能力未启用，跳过并返回兜底响应
                            logger.error(f"Task query capability is disabled: {e}")
                            logger.debug(f"Error traceback: {traceback.format_exc()}")
                            yield "error", {"message": "任务查询功能暂未开启"}
                            return
                        except Exception as e:
                            logger.error(f"Failed to process query intent: {e}")
                            logger.debug(f"Error traceback: {traceback.format_exc()}")
                            yield "error", {"message": f"任务查询功能执行失败: {str(e)}"}
                            return
                    
                    case IntentType.DELETE_TASK | IntentType.CANCEL_TASK | IntentType.PAUSE_TASK | IntentType.RESUME_TASK | IntentType.RETRY_TASK:
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
                            yield "thought", {"message": "任务控制操作完成"}
                        except ValueError as e:
                            # 任务控制能力未启用，跳过并返回兜底响应
                            logger.error(f"Task control capability is disabled: {e}")
                            logger.debug(f"Error traceback: {traceback.format_exc()}")
                            yield "error", {"message": "任务控制功能暂未开启"}
                            return
                        except Exception as e:
                            logger.error(f"Failed to handle task control: {e}")
                            logger.debug(f"Error traceback: {traceback.format_exc()}")
                            yield "error", {"message": f"任务控制功能执行失败: {str(e)}"}
                            return
                    
                    case IntentType.SET_SCHEDULE:
                        try:
                            schedule_manager = self.registry.get_capability("schedule", IScheduleManagerCapability)
                            task_draft_manager = self.registry.get_capability("task_draft", ITaskDraftManagerCapability)
                            result_data = task_draft_manager.update_draft_from_intent(
                                dialog_state.active_task_draft, intent_result
                            )
                            # 这里可以添加调度逻辑
                            yield "thought", {"message": "任务调度设置完成"}
                        except ValueError as e:
                            # 定时任务或任务创建能力未启用，跳过并返回兜底响应
                            logger.error(f"Schedule or task draft capability is disabled: {e}")
                            logger.debug(f"Error traceback: {traceback.format_exc()}")
                            yield "error", {"message": "定时任务或任务创建功能暂未开启"}
                            return
                        except Exception as e:
                            logger.error(f"Failed to process schedule intent: {e}")
                            logger.debug(f"Error traceback: {traceback.format_exc()}")
                            yield "error", {"message": f"定时任务或任务创建功能执行失败: {str(e)}"}
                            return
                    
                    case IntentType.IDLE_CHAT:
                        from capabilities.llm.interface import ILLMCapability
                        from capabilities.context_manager.interface import IContextManagerCapability
                        
                        llm_capability = self.registry.get_capability("llm", ILLMCapability)
                        
                        try:
                            context_manager = self.registry.get_capability("context_manager", IContextManagerCapability)
                            # 获取最近 5-10 轮对话 (根据 Token 限制调整)
                            recent_turns = context_manager.get_recent_turns(limit=5, session_id=dialog_state.session_id)
                            
                            # 因为实现是倒序返回 ([最近, 次近...])，为了给 LLM 阅读，我们需要反转回正序
                            recent_turns.reverse() 
                            
                            # 格式化历史记录
                            history_str = ""
                            for turn in recent_turns:
                                role = getattr(turn, 'role', turn.role)
                                content = getattr(turn, 'utterance', turn.utterance)
                                history_str += f"{role}: {content}\n"
                                
                        except Exception as e:
                            logger.warning(f"Failed to load context history: {e}")
                            history_str = "" # 降级处理：获取失败就不带历史

                        # 构建带记忆的 Prompt
                        prompt = f"""
                            你是一个由 Python 驱动的智能助手。请根据下方的对话历史陪用户聊天。

                            【对话历史】
                            {history_str}

                            【用户当前输入】
                            {input.utterance}

                            请回复用户：
                            """

                        # 调用 LLM
                        idle_content = llm_capability.generate(prompt)
                        result_data = {"response_text": idle_content}
                        yield "thought", {"message": "闲聊意图处理完成(已携带历史记忆)"}
                    
                    case _:
                        result_data = {"response_text": "我还不太明白，请换种说法？"}
                        yield "thought", {"message": "未知意图处理完成"}
            except Exception as e:
                logger.error(f"Failed to process business logic: {e}")
                logger.debug(f"Error traceback: {traceback.format_exc()}")
                yield "error", {"message": f"业务处理失败: {str(e)}"}
                return

        # === 6. 执行任务（如果 should_execute）===
        if result_data.get("should_execute", False):
            try:
                # 生成并设置 request_id
                request_id = str(uuid.uuid4())
                dialog_state = dialog_state_manager.update_dialog_state_fields(
                    dialog_state,
                    current_request_id=request_id
                )
                dialog_state_manager.update_dialog_state(dialog_state)
                
                task_execution_manager = self.registry.get_capability("task_execution", ITaskExecutionManagerCapability)
                exec_context = task_execution_manager.execute_task(
                    request_id,
                    result_data["task_draft"].draft_id,
                     {
                        name: slot.resolved
                        for name, slot in result_data["task_draft"].slots.items()
                    },
                    result_data["task_draft"].task_type,
                    input.user_id
                )
                dialog_state.active_task_execution = exec_context.request_id
                result_data["execution_context"] = exec_context
                yield "thought", {"message": "任务提交执行", "request_id": exec_context.request_id}
            except ValueError as e:
                # 任务执行能力未启用，跳过并返回兜底响应
                logger.error(f"Task execution capability is disabled: {e}")
                logger.debug(f"Error traceback: {traceback.format_exc()}")
                yield "error", {"message": "任务执行功能暂未开启"}
                return
            except Exception as e:
                logger.error(f"Failed to execute task: {e}")
                logger.debug(f"Error traceback: {traceback.format_exc()}")
                yield "error", {"message": f"任务执行失败: {str(e)}"}
                return

        # === 7. 生成响应 & 持久化状态 ===
        try:
            system_response_manager = self.registry.get_capability("system_response", ISystemResponseManagerCapability)
            response = system_response_manager.generate_response(
                input.session_id,
                result_data.get("response_text", ""),
                requires_input=result_data.get("requires_input", False),
                awaiting_slot=result_data.get("awaiting_slot"),
                display_data=result_data.get("display_data")
            )

            # 【关键】持久化更新后的 dialog_state（无论是否 bypass）
            dialog_state_manager.update_dialog_state(dialog_state)

            # 流式返回
            if response.response_text:
                for char in response.response_text:
                    yield "message", {"content": char}
                    # 模拟延迟，实际项目中可以移除
                    import asyncio
                    await asyncio.sleep(0.01)  # 可选

            # 保存用户输入和系统响应到对话历史
            from capabilities.context_manager.interface import IContextManagerCapability
            try:
                context_manager = self.registry.get_capability("context_manager", IContextManagerCapability)
                # # 保存用户输入
                # user_turn = DialogTurn(
                #     session_id=input.session_id,
                #     user_id=input.user_id,
                #     role="user",
                #     utterance=input.utterance
                # )
                # context_manager.add_turn(user_turn)
                # 保存系统响应
                system_turn = DialogTurn(
                    session_id=input.session_id,
                    user_id=input.user_id,
                    role="system",
                    utterance=response.response_text
                )
                context_manager.add_turn(system_turn)
            except Exception as e:
                logger.warning(f"Failed to save dialog turns: {e}")
            
            yield "meta", {
                "session_id": response.session_id,
                "user_id": input.user_id,
                "requires_input": response.requires_input,
                "awaiting_slot": response.awaiting_slot,
                "display_data": response.display_data
            }

        except ValueError as e:
            # 系统响应生成能力未启用，直接返回兜底响应
            logger.error(f"System response capability is disabled: {e}")
            logger.debug(f"Error traceback: {traceback.format_exc()}")
            yield "error", {"message": "系统响应生成功能暂未开启"}
            return
        except Exception as e:
            logger.error(f"Failed to generate system response: {e}")
            logger.debug(f"Error traceback: {traceback.format_exc()}")
            yield "error", {"message": f"响应生成失败: {str(e)}"}
            return
    
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
