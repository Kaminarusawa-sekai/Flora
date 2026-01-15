from typing import Dict, Any, Optional
import re
from .interface import IScheduleManagerCapability
from common import (
    ScheduleDTO,
    TaskDraftDTO
)
from ..llm.interface import ILLMCapability
from external.client.task_client import TaskClient

class CommonScheduleManager(IScheduleManagerCapability):
    """调度管理器 - 处理任务的调度"""
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化调度管理器"""
        self.logger.info("初始化调度管理器")
        self.config = config
        self._llm = None
        # 初始化外部任务执行客户端
        self.external_task_client = TaskClient()
        self.logger.info("调度管理器初始化完成")
    
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
        self.logger.info(f"解析自然语言调度表达式，natural_language={natural_language}, user_timezone={user_timezone}")
        if not natural_language:
            self.logger.debug("自然语言调度表达式为空，返回None")
            return None
        text = natural_language.strip()
        if not text:
            self.logger.debug("自然语言调度表达式为空，返回None")
            return None
        if not self._looks_like_schedule(text):
            self.logger.debug(f"文本不像是调度表达式，返回None，text={text}")
            return None
        try:
            # 1. 快速解析 cron 文本
            cron_match = self._extract_cron_expression(text)
            if cron_match:
                schedule = ScheduleDTO(
                    type="RECURRING",
                    cron_expression=cron_match,
                    natural_language=natural_language,
                    timezone=user_timezone,
                    next_trigger_time=None,
                    max_runs=None,
                    end_time=None
                )
                self.logger.info(f"快速解析cron表达式成功，cron_expression={cron_match}")
                return schedule

            # 2. 解析周期/延迟
            interval_seconds = self._extract_interval_seconds(text)
            if interval_seconds:
                schedule = ScheduleDTO(
                    type="RECURRING",
                    cron_expression=None,
                    natural_language=natural_language,
                    timezone=user_timezone,
                    next_trigger_time=None,
                    max_runs=None,
                    end_time=None,
                    interval_seconds=interval_seconds
                )
                self.logger.info(f"解析周期成功，interval_seconds={interval_seconds}")
                return schedule

            delay_seconds = self._extract_delay_seconds(text)
            if delay_seconds:
                schedule = ScheduleDTO(
                    type="ONCE",
                    cron_expression=None,
                    natural_language=natural_language,
                    timezone=user_timezone,
                    next_trigger_time=None,
                    max_runs=None,
                    end_time=None,
                    delay_seconds=delay_seconds
                )
                self.logger.info(f"解析延迟成功，delay_seconds={delay_seconds}")
                return schedule

            # 3. 解析周/月/工作日
            derived_cron = self._derive_cron_expression(text)
            if derived_cron:
                schedule = ScheduleDTO(
                    type="RECURRING",
                    cron_expression=derived_cron,
                    natural_language=natural_language,
                    timezone=user_timezone,
                    next_trigger_time=None,
                    max_runs=None,
                    end_time=None
                )
                self.logger.info(f"解析周/月/工作日成功，cron_expression={derived_cron}")
                return schedule

            # 4. 尝试外部解析（如果客户端支持）
            if hasattr(self.external_task_client, "parse_schedule_expression"):
                parse_result = self.external_task_client.parse_schedule_expression(natural_language, user_timezone)
                if parse_result and parse_result.get("success"):
                    schedule_data = parse_result["schedule"]
                    schedule = ScheduleDTO(
                        type=schedule_data.get("type"),
                        cron_expression=schedule_data.get("cron_expression"),
                        natural_language=schedule_data.get("natural_language"),
                        timezone=schedule_data.get("timezone", user_timezone),
                        next_trigger_time=None,
                        max_runs=None,
                        end_time=None
                    )
                    self.logger.info(f"外部解析成功，schedule_type={schedule.type}, cron_expression={schedule.cron_expression}")
                    return schedule
            
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
            
            schedule = ScheduleDTO(
                type=schedule_type,
                cron_expression=cron_expression,
                natural_language=natural_language,
                next_trigger_time=None,
                timezone=user_timezone,
                max_runs=None,
                end_time=None
            )
            self.logger.info(f"LLM解析成功，schedule_type={schedule.type}, cron_expression={schedule.cron_expression}")
            return schedule
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
            
            schedule = ScheduleDTO(
                type=schedule_type,
                cron_expression=cron_expression,
                natural_language=natural_language,
                next_trigger_time=None,
                timezone=user_timezone,
                max_runs=None,
                end_time=None
            )
            self.logger.info(f"降级解析成功，schedule_type={schedule.type}, cron_expression={schedule.cron_expression}")
            return schedule

    def _looks_like_schedule(self, text: str) -> bool:
        pattern = r"(?:定时|每隔|每天|每周|每月|每小时|延迟|稍后|\bcron\b|\d+\s*(秒|分钟|小时|天)(?:后|之后)?)"
        return re.search(pattern, text) is not None

    def _extract_cron_expression(self, text: str) -> Optional[str]:
        match = re.search(
            r"cron\s*[:：]?\s*([\d*/,-]+\s+[\d*/,-]+\s+[\d*/,-]+\s+[\d*/,-]+\s+[\d*/,-]+)",
            text,
            re.IGNORECASE
        )
        if match:
            return match.group(1)
        return None

    def _extract_interval_seconds(self, text: str) -> Optional[int]:
        match = re.search(r"(?:每隔|每)\s*(\d+)\s*(秒|分钟|小时|天)", text)
        if not match:
            return None
        value = int(match.group(1))
        unit = match.group(2)
        if unit == "秒":
            return value
        if unit == "分钟":
            return value * 60
        if unit == "小时":
            return value * 3600
        if unit == "天":
            return value * 86400
        return None

    def _extract_delay_seconds(self, text: str) -> Optional[int]:
        match = re.search(r"(?:延迟|推迟|等|过)?\s*(\d+)\s*(秒|分钟|小时|天)(?:后|之后)?", text)
        if not match:
            return None
        value = int(match.group(1))
        unit = match.group(2)
        if unit == "秒":
            return value
        if unit == "分钟":
            return value * 60
        if unit == "小时":
            return value * 3600
        if unit == "天":
            return value * 86400
        return None

    def _derive_cron_expression(self, text: str) -> Optional[str]:
        def parse_time() -> tuple[int, int]:
            hour = None
            minute = 0
            match = re.search(r"(\d{1,2})点(?:(\d{1,2})分)?", text)
            if match:
                hour = int(match.group(1))
                if match.group(2):
                    minute = int(match.group(2))
                elif "半" in text:
                    minute = 30
            if hour is None:
                if any(tag in text for tag in ("早上", "上午")):
                    hour = 9
                elif any(tag in text for tag in ("下午", "晚上", "傍晚")):
                    hour = 18
                elif "中午" in text:
                    hour = 12
                else:
                    hour = 0
            if any(tag in text for tag in ("下午", "晚上", "傍晚")) and hour < 12:
                hour += 12
            return hour, minute

        hour, minute = parse_time()
        weekday_map = {"一": "1", "二": "2", "三": "3", "四": "4", "五": "5", "六": "6", "日": "0", "天": "0"}

        weekly = re.search(r"每周([一二三四五六日天])", text)
        if weekly:
            weekday = weekday_map.get(weekly.group(1))
            if weekday is not None:
                return f"{minute} {hour} * * {weekday}"

        if "工作日" in text or "周一到周五" in text or "周一至周五" in text or "周一-周五" in text:
            return f"{minute} {hour} * * 1-5"

        monthly = re.search(r"每月\s*(\d{1,2})\s*号", text)
        if monthly:
            day = int(monthly.group(1))
            if 1 <= day <= 31:
                return f"{minute} {hour} {day} * *"

        return None
    
    def validate_cron_expression(self, cron_expression: str) -> bool:
        """验证cron表达式是否合法
        
        Args:
            cron_expression: 标准cron表达式
            
        Returns:
            是否合法
        """
        self.logger.info(f"验证cron表达式，cron_expression={cron_expression}")
        if not cron_expression:
            self.logger.debug("cron表达式为空，返回False")
            return False
        
        parts = cron_expression.split()
        if len(parts) != 5:
            self.logger.debug(f"cron表达式格式不正确，parts_count={len(parts)}, 返回False")
            return False
        
        # 这里可以添加更详细的cron验证逻辑
        
        self.logger.info(f"cron表达式验证通过，cron_expression={cron_expression}")
        return True
    
    def register_scheduled_task(self, task_id: str, schedule: ScheduleDTO) -> bool:
        """向调度引擎注册定时任务
        
        Args:
            task_id: 任务ID
            schedule: 调度信息DTO
            
        Returns:
            是否注册成功
        """
        self.logger.info(f"向调度引擎注册定时任务，task_id={task_id}, schedule={schedule}")
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
            
            success = result["success"]
            self.logger.info(f"定时任务注册{'成功' if success else '失败'}，task_id={task_id}")
            return success
        except Exception as e:
            # 记录错误日志
            self.logger.exception(f"注册定时任务失败，task_id={task_id}")
            return False
    
    def unregister_scheduled_task(self, task_id: str) -> bool:
        """取消注册定时任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否取消成功
        """
        self.logger.info(f"取消注册定时任务，task_id={task_id}")
        try:
            # 调用外部客户端取消注册任务
            result = self.external_task_client.unregister_scheduled_task(task_id)
            
            # 取消成功后，更新任务元数据（如果需要）
            # 例如：self.task_storage.update_task_metadata(task_id, {"schedule": None})
            
            success = result["success"]
            self.logger.info(f"取消注册定时任务{'成功' if success else '失败'}，task_id={task_id}")
            return success
        except Exception as e:
            # 记录错误日志
            self.logger.exception(f"取消注册定时任务失败，task_id={task_id}")
            return False
    
    def update_scheduled_task(self, task_id: str, new_schedule: ScheduleDTO) -> bool:
        """更新已注册的定时任务
        
        Args:
            task_id: 任务ID
            new_schedule: 新的调度信息DTO
            
        Returns:
            是否更新成功
        """
        self.logger.info(f"更新已注册的定时任务，task_id={task_id}, new_schedule={new_schedule}")
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
            
            success = result["success"]
            self.logger.info(f"更新定时任务{'成功' if success else '失败'}，task_id={task_id}")
            return success
        except Exception as e:
            # 记录错误日志
            self.logger.exception(f"更新定时任务失败，task_id={task_id}")
            return False
    
    def calculate_next_trigger_time(self, schedule: ScheduleDTO) -> Optional[float]:
        """计算下次触发时间
        
        Args:
            schedule: 调度信息DTO
            
        Returns:
            下次触发时间戳，计算失败返回None
        """
        self.logger.info(f"计算下次触发时间，schedule={schedule}")
        # 这里可以调用外部服务计算下次触发时间
        # 例如：self.external_task_client.calculate_next_trigger_time(schedule.cron_expression, schedule.timezone)
        
        # 简化实现，返回None表示需要进一步计算
        result = schedule.next_trigger_time
        self.logger.debug(f"计算下次触发时间完成，result={result}")
        return result
