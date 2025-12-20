from typing import Dict, Any, Optional
from interaction.common.task_execution import TaskExecutionContextDTO
from interaction.common.base import ExecutionStatus

class TaskClient:
    """任务执行客户端，用于与外部任务执行系统交互"""
    
    def __init__(self):
        # 初始化外部任务系统的连接配置
        self.base_url = "http://external-task-system/api/v1"
        # 实际项目中，这里应该包含认证信息、超时设置等
    
    def submit_task(self, task_id: str, task_type: str, parameters: Dict[str, Any], user_id: str) -> str:
        """提交任务到外部执行系统
        
        Args:
            task_id: 任务ID
            task_type: 任务类型
            parameters: 执行参数
            user_id: 用户ID
            
        Returns:
            外部任务ID
        """
        # 实际项目中，这里应该调用外部API提交任务
        # 例如：requests.post(f"{self.base_url}/tasks", json={"task_id": task_id, "task_type": task_type, "parameters": parameters, "user_id": user_id})
        
        # 模拟实现，返回外部任务ID
        return f"external_job_{task_id}"
    
    def get_task_status(self, task_id: str, external_job_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取任务状态
        
        Args:
            task_id: 任务ID
            external_job_id: 外部任务ID（可选）
            
        Returns:
            任务状态信息，如果任务不存在则返回None
        """
        # 实际项目中，这里应该根据是否提供external_job_id调用不同的外部API
        # 例如：
        # if external_job_id:
        #     requests.get(f"{self.base_url}/jobs/{external_job_id}/status")
        # else:
        #     requests.get(f"{self.base_url}/tasks/{task_id}")
        
        # 模拟实现，返回任务状态
        if external_job_id:
            return {
                "external_job_id": external_job_id,
                "status": "RUNNING",
                "progress": 0.5,
                "last_update": "2025-12-13T14:30:00Z"
            }
        else:
            return {
                "task_id": task_id,
                "execution_status": "RUNNING",
                "control_status": "NORMAL",
                "is_cancelable": True,
                "is_resumable": True,
                "task_type": "web_crawler",
                "description": "爬取京东商品数据"
            }
    
    def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            操作结果
        """
        # 实际项目中，这里应该调用外部API取消任务
        # 例如：requests.post(f"{self.base_url}/tasks/{task_id}/cancel")
        
        # 模拟实现，返回操作结果
        return {
            "success": True,
            "message": f"任务 {task_id} 已成功取消"
        }
    
    def stop_task(self, external_job_id: str) -> Dict[str, Any]:
        """停止任务
        
        Args:
            external_job_id: 外部任务ID
            
        Returns:
            操作结果
        """
        # 实际项目中，这里应该调用外部API停止任务
        # 例如：requests.post(f"{self.base_url}/jobs/{external_job_id}/stop")
        
        # 模拟实现，返回操作结果
        return {
            "success": True,
            "message": f"任务 {external_job_id} 已成功停止"
        }
    
    def pause_task(self, task_id: Optional[str] = None, external_job_id: Optional[str] = None) -> Dict[str, Any]:
        """暂停任务
        
        Args:
            task_id: 任务ID（可选）
            external_job_id: 外部任务ID（可选）
            
        Returns:
            操作结果
        """
        # 实际项目中，这里应该根据提供的ID类型调用不同的外部API
        # 例如：
        # if external_job_id:
        #     requests.post(f"{self.base_url}/jobs/{external_job_id}/pause")
        # else:
        #     requests.post(f"{self.base_url}/tasks/{task_id}/pause")
        
        # 模拟实现，返回操作结果
        target_id = external_job_id if external_job_id else task_id
        return {
            "success": True,
            "message": f"任务 {target_id} 已成功暂停"
        }
    
    def resume_task(self, task_id: Optional[str] = None, external_job_id: Optional[str] = None) -> Dict[str, Any]:
        """恢复任务
        
        Args:
            task_id: 任务ID（可选）
            external_job_id: 外部任务ID（可选）
            
        Returns:
            操作结果
        """
        # 实际项目中，这里应该根据提供的ID类型调用不同的外部API
        # 例如：
        # if external_job_id:
        #     requests.post(f"{self.base_url}/jobs/{external_job_id}/resume")
        # else:
        #     requests.post(f"{self.base_url}/tasks/{task_id}/resume")
        
        # 模拟实现，返回操作结果
        target_id = external_job_id if external_job_id else task_id
        return {
            "success": True,
            "message": f"任务 {target_id} 已成功恢复"
        }
    
    def terminate_task(self, task_id: Optional[str] = None, external_job_id: Optional[str] = None) -> Dict[str, Any]:
        """强制终止任务
        
        Args:
            task_id: 任务ID（可选）
            external_job_id: 外部任务ID（可选）
            
        Returns:
            操作结果
        """
        # 实际项目中，这里应该根据提供的ID类型调用不同的外部API
        # 例如：
        # if external_job_id:
        #     requests.post(f"{self.base_url}/jobs/{external_job_id}/terminate")
        # else:
        #     requests.post(f"{self.base_url}/tasks/{task_id}/terminate")
        
        # 模拟实现，返回操作结果
        target_id = external_job_id if external_job_id else task_id
        return {
            "success": True,
            "message": f"任务 {target_id} 已成功强制终止"
        }
    
    def retry_task(self, task_id: str, task_type: Optional[str] = None, parameters: Optional[Dict[str, Any]] = None, user_id: Optional[str] = None) -> Any:
        """重试任务
        
        支持两种调用方式：
        1. 仅传入task_id：返回操作结果（兼容原task_execution_client的retry_task）
        2. 传入所有参数：返回新的外部任务ID（兼容原external_executor_client的retry）
        
        Args:
            task_id: 原始任务ID
            task_type: 任务类型（可选）
            parameters: 执行参数（可选）
            user_id: 用户ID（可选）
            
        Returns:
            操作结果字典或新的外部任务ID
        """
        # 实际项目中，这里应该根据参数数量调用不同的外部API
        # 例如：
        # if all([task_type, parameters, user_id]):
        #     requests.post(f"{self.base_url}/tasks/{task_id}/retry", json={"task_type": task_type, "parameters": parameters, "user_id": user_id})
        # else:
        #     requests.post(f"{self.base_url}/tasks/{task_id}/retry")
        
        # 模拟实现，根据参数返回不同结果
        if all([task_type, parameters, user_id]):
            # 兼容原external_executor_client的retry方法
            return f"external_job_{task_id}_retry"
        else:
            # 兼容原task_execution_client的retry_task方法
            return {
                "success": True,
                "message": f"任务 {task_id} 已成功重试"
            }
    
    def pause_all_tasks(self, user_id: str) -> Dict[str, Any]:
        """暂停所有正在运行的任务
        
        Args:
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        # 实际项目中，这里应该调用外部API暂停所有任务
        # 例如：requests.post(f"{self.base_url}/tasks/pause-all", params={"user_id": user_id})
        
        # 模拟实现，返回操作结果
        return {
            "success": True,
            "message": "已成功暂停所有正在运行的任务",
            "success_count": 2,
            "failed_count": 0
        }
    
    def register_scheduled_task(self, task_id: str, schedule: Dict[str, Any]) -> Dict[str, Any]:
        """注册定时任务
        
        Args:
            task_id: 任务ID
            schedule: 调度信息，包含cron表达式、时区等
            
        Returns:
            操作结果
        """
        # 实际项目中，这里应该调用外部调度系统API注册任务
        # 例如：requests.post(f"{self.base_url}/schedules", json={"task_id": task_id, "schedule": schedule})
        
        # 模拟实现，返回操作结果
        return {
            "success": True,
            "message": f"定时任务 {task_id} 已成功注册",
            "job_id": f"schedule_{task_id}"
        }
    
    def unregister_scheduled_task(self, task_id: str) -> Dict[str, Any]:
        """取消注册定时任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            操作结果
        """
        # 实际项目中，这里应该调用外部调度系统API取消任务
        # 例如：requests.delete(f"{self.base_url}/schedules/{task_id}")
        
        # 模拟实现，返回操作结果
        return {
            "success": True,
            "message": f"定时任务 {task_id} 已成功取消"
        }
    
    def update_scheduled_task(self, task_id: str, new_schedule: Dict[str, Any]) -> Dict[str, Any]:
        """更新定时任务
        
        Args:
            task_id: 任务ID
            new_schedule: 新的调度信息
            
        Returns:
            操作结果
        """
        # 实际项目中，这里应该调用外部调度系统API更新任务
        # 例如：requests.put(f"{self.base_url}/schedules/{task_id}", json=new_schedule)
        
        # 模拟实现，返回操作结果
        return {
            "success": True,
            "message": f"定时任务 {task_id} 已成功更新"
        }
    
    def parse_schedule_expression(self, natural_language: str, timezone: str = "Asia/Shanghai") -> Dict[str, Any]:
        """解析自然语言调度表达式
        
        Args:
            natural_language: 自然语言调度指令
            timezone: 时区
            
        Returns:
            解析结果，包含调度类型、cron表达式等
        """
        # 实际项目中，这里应该调用NLP服务或专用库解析
        # 例如：requests.post(f"{self.base_url}/parse-schedule", json={"text": natural_language, "timezone": timezone})
        
        # 模拟实现，返回解析结果
        return {
            "success": True,
            "schedule": {
                "type": "RECURRING",
                "cron_expression": "0 8 * * *",
                "natural_language": natural_language,
                "timezone": timezone
            }
        }
    
    def get_running_tasks(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """获取所有正在执行的任务
        
        Args:
            user_id: 用户ID（可选），如果提供则只返回该用户的任务
            
        Returns:
            正在执行的任务列表及元数据
        """
        # 实际项目中，这里应该调用外部API获取正在执行的任务
        # 例如：requests.get(f"{self.base_url}/tasks/running", params={"user_id": user_id} if user_id else {})
        
        # 模拟实现，返回正在执行的任务列表
        return {
            "success": True,
            "tasks": [
                {
                    "task_id": "task_123",
                    "execution_status": "RUNNING",
                    "control_status": "NORMAL",
                    "is_cancelable": True,
                    "is_resumable": True,
                    "task_type": "web_crawler",
                    "description": "爬取京东商品数据",
                    "user_id": "user_001",
                    "start_time": "2025-12-18T10:00:00Z"
                },
                {
                    "task_id": "task_456",
                    "execution_status": "RUNNING",
                    "control_status": "NORMAL",
                    "is_cancelable": True,
                    "is_resumable": False,
                    "task_type": "data_analysis",
                    "description": "分析销售数据",
                    "user_id": "user_001",
                    "start_time": "2025-12-18T10:30:00Z"
                }
            ],
            "total": 2
        }
