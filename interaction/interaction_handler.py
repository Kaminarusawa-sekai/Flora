import logging
import traceback
from typing import Dict, Any, Optional
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
        is_confirm_intent = intent_result.intent in [IntentType.CONFIRM, IntentType.AFFIRM] 
        # 定义拒绝/取消意图
        is_cancel_intent = intent_result.intent in [IntentType.CANCEL, IntentType.DENY, IntentType.REJECT]
        
        # 这一步将决定是否跳过第4步的路由
        bypass_routing = False 
        
        # 默认结果容器
        result_data: Dict[str, Any] = {}

        if dialog_state.waiting_for_confirmation and dialog_state.active_task_draft:
            if is_confirm_intent:
                yield "thought", {"message": "检测到待确认状态及确认意图，直接进入执行流程"}
                
                # 1. 关掉等待开关
                dialog_state.waiting_for_confirmation = False
                
                # 2. 修改草稿状态为 SUBMITTED (这一步很关键，触发后续第5步的执行)
                dialog_state.active_task_draft.status = "SUBMITTED"
                
                # 3. 构造 result_data，模拟 TaskDraftManager 的返回
                result_data = {
                    "should_execute": True,
                    "task_draft": dialog_state.active_task_draft,
                    "response_text": "好的，正在为您执行..." # 这里的回复可能随后被执行结果覆盖
                }
                
                # 4. 标记跳过路由
                bypass_routing = True
                
            elif is_cancel_intent:
                yield "thought", {"message": "用户取消了待确认的操作"}
                
                dialog_state.waiting_for_confirmation = False
                # 这里可以选择清空 draft 或者保留但不提交
                # dialog_state.active_task_draft = None 
                
                result_data = {"response_text": "好的，已取消该操作。"}
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
                case IntentType.CREATE_TASK | IntentType.MODIFY_TASK:
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
        # 1. 用户输入管理
        try:
            user_input_manager = self.registry.get_capability("user_input", IUserInputManagerCapability)
            session_state = user_input_manager.process_input(input)
            input.utterance=session_state["enhanced_utterance"]
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
        

        # =========================================================================
        # 🔥 【新增逻辑】 状态拦截器 (State Interceptor)
        # 如果处于“待确认”状态，且用户意图是“确认/肯定”，则直接短路进执行
        # =========================================================================
        
        # 定义需要拦截的确认意图 (需要你在 IntentType 里定义 CONFIRM/POSITIVE)
        is_confirm_intent = intent_result.intent in [IntentType.CONFIRM, IntentType.AFFIRM] 
        # 定义拒绝/取消意图
        is_cancel_intent = intent_result.intent in [IntentType.CANCEL, IntentType.DENY, IntentType.REJECT]
        
        # 这一步将决定是否跳过第4步的路由
        bypass_routing = False 
        
        # 默认结果容器
        result_data: Dict[str, Any] = {}

        if dialog_state.waiting_for_confirmation and dialog_state.active_task_draft:
            if is_confirm_intent:
                yield "thought", {"message": "检测到待确认状态及确认意图，直接进入执行流程"}
                
                # 1. 关掉等待开关
                dialog_state.waiting_for_confirmation = False
                
                # 2. 修改草稿状态为 SUBMITTED (这一步很关键，触发后续第5步的执行)
                dialog_state.active_task_draft.status = "SUBMITTED"
                
                # 3. 构造 result_data，模拟 TaskDraftManager 的返回
                result_data = {
                    "should_execute": True,
                    "task_draft": dialog_state.active_task_draft,
                    "response_text": "好的，正在为您执行..." # 这里的回复可能随后被执行结果覆盖
                }
                
                # 4. 标记跳过路由
                bypass_routing = True
                
            elif is_cancel_intent:
                yield "thought", {"message": "用户取消了待确认的操作"}
                
                dialog_state.waiting_for_confirmation = False
                # 这里可以选择清空 draft 或者保留但不提交
                # dialog_state.active_task_draft = None 
                
                result_data = {"response_text": "好的，已取消该操作。"}
                bypass_routing = True
            
            else:
                # 处于等待确认状态，但用户说了别的（比如“天气怎么样”），
                # 策略A：认为这是中断，继续往下走常规路由 (waiting_for_confirmation 保持 True 或 False 看业务需求)
                # 策略B：提示用户必须回答是或否
                pass


        # 2. 意图识别（如果是确认状态直接看是不是确认意图，然后再走正式逻辑）

        # 2. 意图识别
        intent_result: IntentRecognitionResultDTO
        try:
            intent_recognition_manager = self.registry.get_capability("intent_recognition", IIntentRecognitionManagerCapability)
            intent_result = intent_recognition_manager.recognize_intent(input)
            yield "thought", {"message": "意图识别完成", "intent": intent_result.intent.value}
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
            yield "thought", {"message": "意图识别失败，使用默认意图"}
        
        # 3. 加载/更新全局对话状态
        try:
            dialog_state_manager = self.registry.get_capability("dialog_state", IDialogStateManagerCapability)
            dialog_state = dialog_state_manager.get_or_create_dialog_state(input.session_id)
            dialog_state.current_intent = intent_result.intent
            logger.info(f"更新全局对话状态: {dialog_state}")
            yield "thought", {"message": "对话状态更新完成"}
        except ValueError as e:
            # 对话状态管理能力未启用，直接返回兜底响应
            logger.error(f"Dialog state capability is disabled: {e}")
            logger.debug(f"Error traceback: {traceback.format_exc()}")
            yield "error", {"message": "DialogState capability is disabled"}
            return
        except Exception as e:
            logger.error(f"Failed to manage dialog state: {e}")
            logger.debug(f"Error traceback: {traceback.format_exc()}")
            yield "error", {"message": f"对话状态管理失败: {str(e)}"}
            return
        
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
                                task_type="default",  # 可以根据intent_result获取具体任务类型
                                session_id=dialog_state.session_id,
                                user_id="default_user"  # 可以从上下文中获取实际用户ID
                            )
                        
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


                        yield "thought", {"message": "任务草稿更新完成"}
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
                    llm_capability = self.registry.get_capability("llm", ILLMCapability)
                    
                    try:
                            from capabilities.context_manager.interface import IContextManagerCapability
                            context_manager = self.registry.get_capability("context_manager", IContextManagerCapability)
                            # 获取最近 5-10 轮对话 (根据 Token 限制调整)
                            # 注意：get_recent_turns 返回的是按时间倒序的(最近的在前面)，还是正序，取决于你的实现。
                            # 你提供的 CommonContextManager 代码中： return all_turns[-limit:][::-1] (倒序，最近的在index 0)
                            recent_turns = context_manager.get_recent_turns(limit=5)
                            
                            # 因为你的实现是倒序返回 ([最近, 次近...])，为了给 LLM 阅读，我们需要反转回正序
                            recent_turns.reverse() 
                            
                            # 3. 格式化历史记录
                            history_str = ""
                            for turn in recent_turns:
                                # 假设 turn 是字典或对象，根据 DialogRepository 的实现调整
                                # 如果是对象: role = turn.role
                                # 如果是字典: role = turn['role']
                                role = getattr(turn, 'role', turn.role)
                                content = getattr(turn, 'utterance', turn.utterance)
                                history_str += f"{role}: {content}\n"
                                
                    except Exception as e:
                        logger.warning(f"Failed to load context history: {e}")
                        history_str = "" # 降级处理：获取失败就不带历史

                        # 4. 构建带记忆的 Prompt
                        prompt = f"""
                            你是一个由 Python 驱动的智能助手。请根据下方的对话历史陪用户聊天。

                            【对话历史】
                            {history_str}

                            【用户当前输入】
                            {input.utterance}

                            请回复用户：
                            """

                        # 5. 调用 LLM
                        idle_content = llm_capability.generate(prompt)
                        context_manager.add_turn(DialogTurn(role="assistant", utterance=idle_content))
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
        
        logger.info(f"处理结果: {result_data}")
        context_manager.add_turn(DialogTurn(role="system", utterance=result_data.get("response_text", "")))
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
                yield "thought", {"message": "任务执行完成", "task_id": exec_context.task_id}
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
            
            # 流式返回响应内容
            if response.response_text:
                # 模拟流式返回，实际项目中可以根据需要调整
                for char in response.response_text:
                    yield "message", {"content": char}
                    # 模拟延迟，实际项目中可以移除
                    import asyncio
                    await asyncio.sleep(0.01)
            
            # 返回最终元数据
            yield "meta", {
                "session_id": response.session_id,
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
