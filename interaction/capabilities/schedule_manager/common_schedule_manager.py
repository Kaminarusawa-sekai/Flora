from typing import Dict, Any, Optional
from .interface import IScheduleManagerCapability
from common import (
    ScheduleDTO,
    TaskDraftDTO
)
from ..llm.interface import ILLMCapability
from external.client.task_client import TaskClient

class CommonSchedule(IScheduleManagerCapability):
    """调度管理器 - 处理任务的调度"""
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化调度管理器"""
        self.config = config
        self._llm = None
        # 初始化外部任务执行客户端
        self.external_task_client = TaskClient()
    
    @property
    def llm(self):
        """懒加载LLM能力"""
        if self._llm is None:
            from .. import get_capability
            self._llm = get_capability("llm", expected_type=ILLMCapability)
        return self._llm
    
    def shutdown(self) -> None:
        """关闭调度管理器"""
        pass
    
    def get_capability_type(self) -> str:
        """返回能力类型"""
        return "schedule"
    
    def parse_schedule_expression(self, natural_language: str, user_timezone: str = "Asia/Shanghai") -> Optional[ScheduleDTO]:
        """解析自然语言调度表达式
        
        Args:
            natural_language: 用户原始说法，如 "每天早上8点"
            user_timezone: 用户时区
            
        Returns:
            调度信息DTO，解析失败返回None
        """
        try:
            # 1. 先尝试使用外部客户端解析
            parse_result = self.external_task_client.parse_schedule_expression(natural_language, user_timezone)
            if parse_result and parse_result["success"]:
                schedule_data = parse_result["schedule"]
                return ScheduleDTO(
                    type=schedule_data["type"],
                    cron_expression=schedule_data["cron_expression"],
                    natural_language=schedule_data["natural_language"],
                    timezone=schedule_data["timezone"],
                    next_trigger_time=None,
                    max_runs=None,
                    end_time=None
                )
            
            # 2. 如果外部解析失败，尝试使用LLM解析
            prompt = f"""
            将以下中文调度指令转换为标准5位cron表达式（分钟 小时 日 月 星期）和调度类型。
            时区：{user_timezone}
            指令："{natural_language}"
            输出格式：
            type: 调度类型（ONCE或RECURRING）
            cron_expression: cron表达式（如果是ONCE则为None）
            只输出上述格式，不要解释。
            """
            llm_result = self.llm.generate(prompt).strip()
            
            # 解析LLM输出
            schedule_type = "ONCE"
            cron_expression = None
            
            for line in llm_result.splitlines():
                if "type:" in line:
                    schedule_type = line.split(":")[1].strip().upper()
                elif "cron_expression:" in line:
                    cron_expression = line.split(":")[1].strip()
                    if cron_expression.lower() == "none":
                        cron_expression = None
            
            # 验证cron表达式
            if cron_expression and not self.validate_cron_expression(cron_expression):
                cron_expression = None
            
            return ScheduleDTO(
                type=schedule_type,
                cron_expression=cron_expression,
                natural_language=natural_language,
                next_trigger_time=None,
                timezone=user_timezone,
                max_runs=None,
                end_time=None
            )
        except Exception as e:
            # 降级到基础的硬编码解析
            schedule_type = "ONCE"
            cron_expression = None
            
            if any(keyword in natural_language for keyword in ["每天", "每周", "每月", "每小时", "每隔"]):
                schedule_type = "RECURRING"
            
            if "每天早上8点" in natural_language:
                cron_expression = "0 8 * * *"
            elif "每周一" in natural_language:
                cron_expression = "0 0 * * 1"
            elif "每小时" in natural_language:
                cron_expression = "0 * * * *"
            
            return ScheduleDTO(
                type=schedule_type,
                cron_expression=cron_expression,
                natural_language=natural_language,
                next_trigger_time=None,
                timezone=user_timezone,
                max_runs=None,
                end_time=None
            )
    
    def validate_cron_expression(self, cron_expression: str) -> bool:
        """验证cron表达式是否合法
        
        Args:
            cron_expression: 标准cron表达式
            
        Returns:
            是否合法
        """
        if not cron_expression:
            return False
        
        parts = cron_expression.split()
        if len(parts) != 5:
            return False
        
        # 这里可以添加更详细的cron验证逻辑
        
        return True
    
    def register_scheduled_task(self, task_id: str, schedule: ScheduleDTO) -> bool:
        """向调度引擎注册定时任务
        
        Args:
            task_id: 任务ID
            schedule: 调度信息DTO
            
        Returns:
            是否注册成功
        """
        try:
            # 1. 将ScheduleDTO转换为字典格式
            schedule_dict = {
                "type": schedule.type,
                "cron_expression": schedule.cron_expression,
                "natural_language": schedule.natural_language,
                "timezone": schedule.timezone,
                "max_runs": schedule.max_runs,
                "end_time": schedule.end_time
            }
            
            # 2. 调用外部客户端注册任务
            result = self.external_task_client.register_scheduled_task(task_id, schedule_dict)
            
            # 3. 注册成功后，将调度规则持久化到任务元数据（如果需要）
            # 这里可以添加调用task_storage更新任务元数据的逻辑
            # 例如：self.task_storage.update_task_metadata(task_id, {"schedule": schedule_dict})
            
            return result["success"]
        except Exception as e:
            # 记录错误日志
            print(f"注册定时任务失败: {e}")
            return False
    
    def unregister_scheduled_task(self, task_id: str) -> bool:
        """取消注册定时任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否取消成功
        """
        try:
            # 调用外部客户端取消注册任务
            result = self.external_task_client.unregister_scheduled_task(task_id)
            
            # 取消成功后，更新任务元数据（如果需要）
            # 例如：self.task_storage.update_task_metadata(task_id, {"schedule": None})
            
            return result["success"]
        except Exception as e:
            # 记录错误日志
            print(f"取消注册定时任务失败: {e}")
            return False
    
    def update_scheduled_task(self, task_id: str, new_schedule: ScheduleDTO) -> bool:
        """更新已注册的定时任务
        
        Args:
            task_id: 任务ID
            new_schedule: 新的调度信息DTO
            
        Returns:
            是否更新成功
        """
        try:
            # 1. 将ScheduleDTO转换为字典格式
            new_schedule_dict = {
                "type": new_schedule.type,
                "cron_expression": new_schedule.cron_expression,
                "natural_language": new_schedule.natural_language,
                "timezone": new_schedule.timezone,
                "max_runs": new_schedule.max_runs,
                "end_time": new_schedule.end_time
            }
            
            # 2. 调用外部客户端更新任务
            result = self.external_task_client.update_scheduled_task(task_id, new_schedule_dict)
            
            # 3. 更新成功后，将新的调度规则持久化到任务元数据（如果需要）
            # 例如：self.task_storage.update_task_metadata(task_id, {"schedule": new_schedule_dict})
            
            return result["success"]
        except Exception as e:
            # 记录错误日志
            print(f"更新定时任务失败: {e}")
            return False
    
    def calculate_next_trigger_time(self, schedule: ScheduleDTO) -> Optional[float]:
        """计算下次触发时间
        
        Args:
            schedule: 调度信息DTO
            
        Returns:
            下次触发时间戳，计算失败返回None
        """
        # 这里可以调用外部服务计算下次触发时间
        # 例如：self.external_task_client.calculate_next_trigger_time(schedule.cron_expression, schedule.timezone)
        
        # 简化实现，返回None表示需要进一步计算
        return schedule.next_trigger_time