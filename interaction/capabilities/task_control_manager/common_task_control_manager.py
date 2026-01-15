from typing import Dict, Any, Optional
from .interface import ITaskControlManagerCapability
from common.task_execution import TaskControlResponseDTO
from common import (
    ExecutionStatus,
    IntentRecognitionResultDTO,
    UserInputDTO
)
from ..llm.interface import ILLMCapability
from external.client import TaskClient

class CommonTaskControl(ITaskControlManagerCapability):
    """任务控制管理器 - 控制任务的执行"""
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化任务控制管理器"""
        self.logger.info("=== 开始初始化任务控制管理器 ===")
        # 记录配置信息（仅记录关键配置，避免敏感信息）
        config_keys = list(config.keys())
        self.logger.debug(f"获取到配置项: {config_keys}")
        self.config = config
        
        # 初始化LLM引用
        self.logger.debug("初始化LLM引用为None")
        self._llm: Optional[ILLMCapability] = None
        
        # 初始化外部任务客户端
        self.logger.debug("开始初始化外部任务客户端")
        self.external_task_client = TaskClient()
        self.logger.info("外部任务客户端初始化完成")
        
        self.logger.info("=== 任务控制管理器初始化完成 ===")
    @property
    def llm(self) -> ILLMCapability:
        """懒加载LLM能力"""
        if self._llm is None:
            from .. import get_capability
            self._llm = get_capability("llm", expected_type=ILLMCapability)
        return self._llm
       
        
    
    def shutdown(self) -> None:
        """关闭任务控制管理器"""
        pass
    
    def get_capability_type(self) -> str:
        """返回能力类型"""
        return "task_control"
    
    # --- 辅助方法：处理外部客户端结果 ---
    def _handle_client_result(self, result: Dict[str, Any], task_id: str, operation: str) -> TaskControlResponseDTO:
        """统一处理 External TaskClient 的返回结果"""
        self.logger.debug(f"开始处理客户端结果: operation={operation}, task_id={task_id}")
        self.logger.debug(f"客户端原始返回结果: {result}")
        
        # 假设 external client 返回的是 {"success": bool, "message": str, ...}
        success = result.get("success", False)
        message = result.get("message", "操作成功" if success else "操作失败")
        
        self.logger.debug(f"处理结果 - success: {success}, message: {message}")
        
        if success:
            response = TaskControlResponseDTO.success_result(
                message=message,
                task_id=task_id,
                operation=operation,
                data=result
            )
            self.logger.debug(f"构建成功响应: {response}")
            return response
        else:
            response = TaskControlResponseDTO.error_result(
                message=message,
                task_id=task_id,
                operation=operation
            )
            self.logger.debug(f"构建失败响应: {response}")
            return response
    
    def cancel_task(self, task_id: str, user_id: str) -> TaskControlResponseDTO:
        """取消任务
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        self.logger.info(f"=== 开始处理取消任务请求 ===")
        self.logger.debug(f"取消任务参数: task_id={task_id}, user_id={user_id}")
        op = "CANCEL"
        
        # 1. 获取任务状态
        self.logger.debug(f"步骤1: 获取任务 {task_id} 的状态")
        task_status = self.external_task_client.get_task_status(task_id)
        self.logger.debug(f"获取到任务状态: {task_status}")
        
        if not task_status:
            self.logger.warning(f"任务 {task_id} 不存在，无法取消")
            return TaskControlResponseDTO.error_result(f"任务 {task_id} 不存在", task_id, op)
        
        # 2. 验证操作合法性
        self.logger.debug(f"步骤2: 验证取消操作合法性")
        current_status = task_status["execution_status"]
        self.logger.debug(f"当前任务状态: {current_status}, 可取消标记: {task_status.get('is_cancelable', True)}")
        
        if current_status in ["COMPLETED", "CANCELLED"]:
            self.logger.warning(f"任务 {task_id} 当前状态为 {current_status}，无法取消")
            return TaskControlResponseDTO.error_result(f"任务 {task_id} 已完成或已取消，无法取消", task_id, op)
        
        if not task_status.get("is_cancelable", True):
            self.logger.warning(f"任务 {task_id} 标记为不可取消")
            return TaskControlResponseDTO.error_result(f"任务 {task_id} 不允许取消", task_id, op)
        
        # 3. 执行取消操作
        self.logger.debug(f"步骤3: 执行取消操作")
        result = self.external_task_client.cancel_task(task_id)
        self.logger.debug(f"外部客户端取消任务结果: {result}")
        
        response = self._handle_client_result(result, task_id, op)
        self.logger.info(f"=== 取消任务{'成功' if response.success else '失败'} ===, task_id={task_id}, message={response.message}")
        return response
    
    def pause_task(self, task_id: str, user_id: str) -> TaskControlResponseDTO:
        """暂停任务
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        self.logger.info(f"=== 开始处理暂停任务请求 ===")
        self.logger.debug(f"暂停任务参数: task_id={task_id}, user_id={user_id}")
        op = "PAUSE"
        
        # 1. 获取任务状态
        self.logger.debug(f"步骤1: 获取任务 {task_id} 的状态")
        task_status = self.external_task_client.get_task_status(task_id)
        self.logger.debug(f"获取到任务状态: {task_status}")
        
        if not task_status:
            self.logger.warning(f"任务 {task_id} 不存在，无法暂停")
            return TaskControlResponseDTO.error_result(f"任务 {task_id} 不存在", task_id, op)
        
        # 2. 验证操作合法性
        self.logger.debug(f"步骤2: 验证暂停操作合法性")
        current_status = task_status["execution_status"]
        is_resumable = task_status["is_resumable"]
        self.logger.debug(f"当前任务状态: {current_status}, 可恢复标记: {is_resumable}")
        
        if current_status not in ["RUNNING", "AWAITING_USER_INPUT"]:
            self.logger.warning(f"任务 {task_id} 当前状态为 {current_status}，无法暂停")
            return TaskControlResponseDTO.error_result(f"任务 {task_id} 不在运行状态，无法暂停", task_id, op)
        
        if not is_resumable:
            self.logger.warning(f"任务 {task_id} 不支持暂停/恢复")
            # 使用LLM生成友好提示
            try:
                self.logger.debug(f"尝试使用LLM生成友好提示，task_type={task_status['task_type']}")
                prompt = f"""
                用户尝试暂停一个不支持暂停的任务（类型：{task_status['task_type']}，描述：{task_status['description']}）。
                请用中文生成一条不超过50字的友好提示，解释为什么不能暂停，并给出替代建议。
                """
                explanation = self.llm.generate(prompt).strip()
                self.logger.debug(f"LLM生成的友好提示: {explanation}")
                return TaskControlResponseDTO.error_result(explanation, task_id, op)
            except Exception as e:
                self.logger.exception(f"生成友好提示失败，task_id={task_id}, task_type={task_status['task_type']}")
                # 降级到默认消息
                return TaskControlResponseDTO.error_result(f"任务 {task_id} 不支持暂停/恢复", task_id, op)
        
        # 3. 执行暂停操作
        self.logger.debug(f"步骤3: 执行暂停操作")
        result = self.external_task_client.pause_task(task_id)
        self.logger.debug(f"外部客户端暂停任务结果: {result}")
        
        response = self._handle_client_result(result, task_id, op)
        self.logger.info(f"=== 暂停任务{'成功' if response.success else '失败'} ===, task_id={task_id}, message={response.message}")
        return response
    
    def resume_task(self, task_id: str, user_id: str) -> TaskControlResponseDTO:
        """恢复任务
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        self.logger.info(f"=== 开始处理恢复任务请求 ===")
        self.logger.debug(f"恢复任务参数: task_id={task_id}, user_id={user_id}")
        op = "RESUME"
        
        # 1. 获取任务状态
        self.logger.debug(f"步骤1: 获取任务 {task_id} 的状态")
        task_status = self.external_task_client.get_task_status(task_id)
        self.logger.debug(f"获取到任务状态: {task_status}")
        
        if not task_status:
            self.logger.warning(f"任务 {task_id} 不存在，无法恢复")
            return TaskControlResponseDTO.error_result(f"任务 {task_id} 不存在", task_id, op)
        
        # 2. 验证操作合法性
        self.logger.debug(f"步骤2: 验证恢复操作合法性")
        control_status = task_status["control_status"]
        self.logger.debug(f"当前任务控制状态: {control_status}")
        
        if control_status != "PAUSED":
            self.logger.warning(f"任务 {task_id} 当前控制状态为 {control_status}，未暂停，无法恢复")
            return TaskControlResponseDTO.error_result(f"任务 {task_id} 未暂停，无法恢复", task_id, op)
        
        # 3. 执行恢复操作
        self.logger.debug(f"步骤3: 执行恢复操作")
        result = self.external_task_client.resume_task(task_id)
        self.logger.debug(f"外部客户端恢复任务结果: {result}")
        
        response = self._handle_client_result(result, task_id, op)
        self.logger.info(f"=== 恢复任务{'成功' if response.success else '失败'} ===, task_id={task_id}, message={response.message}")
        return response
    
    def retry_task(self, task_id: str, user_id: str) -> TaskControlResponseDTO:
        """重试任务
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        self.logger.info(f"=== 开始处理重试任务请求 ===")
        self.logger.debug(f"重试任务参数: task_id={task_id}, user_id={user_id}")
        op = "RETRY"
        
        # 1. 获取任务状态
        self.logger.debug(f"步骤1: 获取任务 {task_id} 的状态")
        task_status = self.external_task_client.get_task_status(task_id)
        self.logger.debug(f"获取到任务状态: {task_status}")
        
        if not task_status:
            self.logger.warning(f"任务 {task_id} 不存在，无法重试")
            return TaskControlResponseDTO.error_result(f"任务 {task_id} 不存在", task_id, op)
        
        # 2. 验证操作合法性
        self.logger.debug(f"步骤2: 验证重试操作合法性")
        execution_status = task_status["execution_status"]
        self.logger.debug(f"当前任务执行状态: {execution_status}")
        
        if execution_status not in ["FAILED", "ERROR"]:
            self.logger.warning(f"任务 {task_id} 当前执行状态为 {execution_status}，未失败，无法重试")
            return TaskControlResponseDTO.error_result(f"任务 {task_id} 未失败，无法重试", task_id, op)
        
        # 3. 执行重试操作
        self.logger.debug(f"步骤3: 执行重试操作")
        result = self.external_task_client.retry_task(task_id)
        self.logger.debug(f"外部客户端重试任务结果: {result}")
        
        response = self._handle_client_result(result, task_id, op)
        self.logger.info(f"=== 重试任务{'成功' if response.success else '失败'} ===, task_id={task_id}, message={response.message}")
        return response
    
    def terminate_task(self, task_id: str, user_id: str) -> TaskControlResponseDTO:
        """强制终止任务
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        self.logger.info(f"=== 开始处理强制终止任务请求 ===")
        self.logger.debug(f"强制终止任务参数: task_id={task_id}, user_id={user_id}")
        op = "TERMINATE"
        
        # 1. 获取任务状态
        self.logger.debug(f"步骤1: 获取任务 {task_id} 的状态")
        task_status = self.external_task_client.get_task_status(task_id)
        self.logger.debug(f"获取到任务状态: {task_status}")
        
        if not task_status:
            self.logger.warning(f"任务 {task_id} 不存在，无法强制终止")
            return TaskControlResponseDTO.error_result(f"任务 {task_id} 不存在", task_id, op)
        
        # 2. 执行终止操作
        self.logger.debug(f"步骤2: 执行强制终止操作")
        result = self.external_task_client.terminate_task(task_id)
        self.logger.debug(f"外部客户端强制终止任务结果: {result}")
        
        response = self._handle_client_result(result, task_id, op)
        self.logger.info(f"=== 强制终止任务{'成功' if response.success else '失败'} ===, task_id={task_id}, message={response.message}")
        return response
    
    def pause_all_tasks(self, user_id: str) -> TaskControlResponseDTO:
        """暂停所有正在运行的任务
        
        Args:
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        self.logger.info(f"=== 开始处理暂停所有任务请求 ===")
        self.logger.debug(f"暂停所有任务参数: user_id={user_id}")
        
        # 执行暂停所有任务操作
        self.logger.debug(f"执行暂停所有任务操作")
        result = self.external_task_client.pause_all_tasks(user_id)
        self.logger.debug(f"外部客户端暂停所有任务结果: {result}")
        
        # 这里的 task_id 设为 "ALL"
        response = self._handle_client_result(result, "ALL", "PAUSE_ALL")
        self.logger.info(f"=== 暂停所有任务{'成功' if response.success else '失败'} ===, message={response.message}")
        return response
    
    def handle_task_control(self, intent_result: IntentRecognitionResultDTO, user_input: UserInputDTO, user_id: str, dialog_state: Any, last_mentioned_task_id: Optional[str] = None) -> TaskControlResponseDTO:
        """处理任务控制意图
        
        Args:
            intent_result: 意图识别结果
            user_input: 原始用户输入
            user_id: 用户ID
            dialog_state: 对话状态上下文
            last_mentioned_task_id: 上次提到的任务ID
            
        Returns:
            操作结果
        """
        self.logger.info(f"=== 开始处理任务控制意图 ===")
        self.logger.debug(f"处理任务控制意图参数: user_id={user_id}, last_mentioned_task_id={last_mentioned_task_id}")
        self.logger.debug(f"原始用户输入: {user_input.utterance}")
        self.logger.debug(f"意图识别结果: primary_intent={intent_result.primary_intent}, entities={[(e.name, e.value, e.resolved_value) for e in intent_result.entities]}")
        
        # 1. 从实体中提取任务ID
        self.logger.debug("步骤1: 从实体中提取任务ID")
        task_id = None
        for entity in intent_result.entities:
            self.logger.debug(f"检查实体: name={entity.name}, value={entity.value}, resolved_value={entity.resolved_value}")
            if entity.name == "task_id":
                task_id = entity.resolved_value or entity.value
                self.logger.debug(f"从实体中提取到任务ID: {task_id}")
                break
        
        # 2. 如果没有提取到任务ID，使用上次提到的任务ID
        if not task_id:
            self.logger.debug(f"步骤2: 从实体未提取到任务ID，尝试使用上次提到的任务ID")
            task_id = last_mentioned_task_id
            self.logger.debug(f"使用上次提到的任务ID: {task_id}")
        
        # 3. 如果仍然没有任务ID，尝试根据上下文和输入推断
        if not task_id:
            self.logger.debug(f"步骤3: 上次提到的任务ID也为空，尝试根据上下文和输入推断任务ID")
            task_id = self._infer_task_id(intent_result, user_input, user_id, dialog_state)
            self.logger.debug(f"推断出的任务ID: {task_id}")
        
        if not task_id:
            self.logger.warning(f"无法确定要操作的任务ID，user_id={user_id}")
            response = TaskControlResponseDTO.error_result(
                message="请指定要操作的任务ID",
                operation="UNKNOWN"
            )
            self.logger.info(f"=== 任务控制意图处理完成 ===, 结果: 失败, 原因: 无法确定任务ID")
            return response
        
        # 4. 根据意图类型调用相应的任务控制方法
        self.logger.debug(f"步骤4: 确定任务ID为 {task_id}，开始根据意图类型执行操作")
        intent_type = intent_result.primary_intent
        self.logger.debug(f"当前意图类型: {intent_type}")
        
        response = None
        if intent_type == "DELETE" or intent_type == "CANCEL":
            self.logger.debug(f"执行取消任务操作，task_id={task_id}")
            response = self.cancel_task(task_id, user_id)
        elif intent_type == "PAUSE":
            self.logger.debug(f"执行暂停任务操作，task_id={task_id}")
            response = self.pause_task(task_id, user_id)
        elif intent_type == "RESUME_TASK":
            self.logger.debug(f"执行恢复任务操作，task_id={task_id}")
            response = self.resume_task(task_id, user_id)
        elif intent_type == "RETRY":
            self.logger.debug(f"执行重试任务操作，task_id={task_id}")
            response = self.retry_task(task_id, user_id)
        else:
            self.logger.warning(f"不支持的任务控制意图类型: {intent_type}, task_id={task_id}")
            response = TaskControlResponseDTO.error_result(
                message=f"不支持的任务控制意图类型: {intent_type}",
                task_id=task_id,
                operation="UNKNOWN"
            )
        
        self.logger.info(f"=== 任务控制意图处理完成 ===, 结果: {'成功' if response.success else '失败'}, message={response.message}")
        return response
    
    def _infer_task_id(self, intent_result: IntentRecognitionResultDTO, user_input: UserInputDTO, user_id: str, dialog_state: Any) -> Optional[str]:
        """根据上下文、输入和任务列表推断任务ID
        
        Args:
            intent_result: 意图识别结果
            user_input: 原始用户输入
            user_id: 用户ID
            dialog_state: 对话状态上下文
            
        Returns:
            推断出的任务ID，或者None
        """
        self.logger.info(f"=== 开始推断任务ID ===")
        self.logger.debug(f"推断任务ID参数: user_id={user_id}, utterance={user_input.utterance}")
        
        try:
            # 1. 获取所有正在执行的任务
            self.logger.debug("步骤1: 获取所有正在执行的任务")
            running_tasks_result = self.external_task_client.get_running_tasks(user_id)
            self.logger.debug(f"获取运行中任务结果: {running_tasks_result}")
            running_tasks = running_tasks_result.get("tasks", [])
            self.logger.debug(f"获取到 {len(running_tasks)} 个正在执行的任务")
            for task in running_tasks:
                self.logger.debug(f"  - 任务: ID={task['task_id']}, 类型={task['task_type']}, 状态={task['execution_status']}")
            
            # 2. 从对话状态中获取最近的任务ID作为参考
            self.logger.debug("步骤2: 从对话状态中获取最近的任务ID")
            recent_task_id = None
            if hasattr(dialog_state, 'recent_tasks') and dialog_state.recent_tasks:
                recent_task_id = dialog_state.recent_tasks[-1].task_id
                self.logger.debug(f"从对话状态获取到最近的任务ID: {recent_task_id}")
            else:
                self.logger.debug("对话状态中没有最近的任务记录")
            
            # 3. 如果有正在执行的任务，使用大模型智能判断
            if running_tasks:
                self.logger.debug("步骤3: 有正在执行的任务，使用大模型智能判断")
                # 构建任务列表描述
                tasks_description = "\n".join([
                    f"任务ID: {task['task_id']}, 类型: {task['task_type']}, 描述: {task['description']}, 状态: {task['execution_status']}"
                    for task in running_tasks
                ])
                self.logger.debug(f"构建的任务列表描述: {tasks_description[:100]}...")
                
                prompt = f"""
                用户输入：{user_input.utterance}
                用户ID：{user_id}
                最近操作的任务ID：{recent_task_id if recent_task_id else '无'}
                
                以下是当前正在执行的任务列表：
                {tasks_description}
                
                请仔细分析用户的输入，判断用户想要操作的是哪个任务？
                
                要求：
                1. 只输出任务ID，如果无法判断或没有匹配的任务，请输出"NONE"
                2. 只输出结果，不要有任何解释
                3. 如果用户明确提到某个任务ID，请优先匹配
                4. 如果没有明确提到任务ID，请根据任务类型、描述和用户输入的关联性进行判断
                5. 如果用户输入是通用指令（如"暂停所有任务"），请输出"ALL"
                """
                
                self.logger.debug(f"构建的LLM提示: {prompt[:200]}...")
                llm_result = self.llm.generate(prompt).strip()
                self.logger.debug(f"LLM返回结果: {llm_result}")
                
                # 处理大模型返回结果
                if llm_result and llm_result != "NONE" and llm_result != "ALL":
                    self.logger.debug(f"LLM返回了具体的任务ID: {llm_result}，开始验证是否存在于运行中任务列表")
                    # 验证返回的任务ID是否确实在正在执行的任务列表中
                    for task in running_tasks:
                        if task["task_id"] == llm_result:
                            self.logger.debug(f"验证通过，任务ID {llm_result} 确实在运行中任务列表中")
                            result = llm_result
                            self.logger.info(f"=== 任务ID推断完成 ===, 结果: {result}")
                            return result
                    self.logger.debug(f"验证失败，任务ID {llm_result} 不在运行中任务列表中")
                elif llm_result == "ALL":
                    self.logger.debug(f"LLM返回了'ALL'，表示用户想要操作所有任务")
                    result = "ALL"
                    self.logger.info(f"=== 任务ID推断完成 ===, 结果: {result}")
                    return result
                else:
                    self.logger.debug(f"LLM返回了'NONE'或空值，表示无法判断用户想要操作的任务")
            else:
                self.logger.debug("没有正在执行的任务，无法进行任务ID推断")
            
            # 如果没有正在执行的任务或大模型无法判断，返回None
            result = None
            self.logger.info(f"=== 任务ID推断完成 ===, 结果: {result}")
            return result
        except Exception as e:
            self.logger.exception(f"推断任务ID失败")
            return None