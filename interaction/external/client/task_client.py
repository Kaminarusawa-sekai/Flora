from typing import Dict, Any, Optional
import requests
from interaction.common.task_execution import TaskExecutionContextDTO
from interaction.common.base import ExecutionStatus

class TaskClient:
    """任务执行客户端，用于与外部任务执行系统交互"""
    
    def __init__(self, base_url: str = "http://external-task-system/api/v1"):
        self.base_url = base_url.rstrip('/')
        # 实际项目中，这里应该包含认证信息、超时设置等
    
    def _call_ad_hoc_api(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """统一的内部调用方法"""
        url = f"{self.base_url}/ad-hoc-tasks"
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            # 这里可以根据需要处理异常
            raise Exception(f"Failed to submit task: {str(e)}")
    
    def submit_task(
        self,
        task_name: str,           # 新增：任务要有名字
        task_content: Dict[str, Any], # 新增：必须告诉后端执行什么逻辑
        parameters: Dict[str, Any],
        user_id: str
    ) -> str:
        """
        提交一次性任务
        注意：trace_id 不再由外部传入，而是由后端生成并返回
        
        Args:
            task_name: 任务名称
            task_content: 任务内容，包含具体执行定义
            parameters: 执行参数
            user_id: 用户ID
            
        Returns:
            后端生成的trace_id
        """
        # 将 user_id 放入 input_params
        parameters["_user_id"] = user_id

        payload = {
            "task_name": task_name,
            "task_content": task_content,
            "input_params": parameters,
            "loop_config": None,      # 关键：没有循环配置 = 单次运行
            "is_temporary": True
        }

        resp_data = self._call_ad_hoc_api(payload)
        
        # 返回后端生成的 trace_id
        return resp_data["trace_id"]
    
    def register_scheduled_task(self, task_name: str, task_content: Dict[str, Any], schedule: Dict[str, Any]):
        """
        警告：目前的后端 /ad-hoc-tasks 接口逻辑中，submit_ad_hoc_task
        似乎只处理了 loop_config (Loop) 和 默认的 (Once)。
        
        如果后端逻辑中没有处理 'cron_config' 或类似的字段，
        这个方法目前无法通过 submit_ad_hoc_task 实现 CRON 调度。
        
        你可能需要：
        1. 修改后端 AdHocTaskRequest，增加 cron_expression 字段。
        2. 或者，如果你是指"延迟执行一次"，可以用带间隔的 Loop 且 max_runs=1 实现（变通方法）。
        """
        raise NotImplementedError("后端 /ad-hoc-tasks 接口暂未支持纯 Cron 表达式参数，请扩展后端 Request 模型。")
    
    def unregister_scheduled_task(self, trace_id: str) -> Dict[str, Any]:
        """取消注册定时任务
        
        Args:
            trace_id: 跟踪ID，由后端传入
            
        Returns:
            操作结果
        """
        # 实际项目中，这里应该调用外部调度系统API取消任务
        # 例如：requests.delete(f"{self.base_url}/schedules/{trace_id}")
        
        # 模拟实现，返回操作结果
        return {
            "success": True,
            "message": f"定时任务 {trace_id} 已成功取消"
        }
    
    def update_scheduled_task(self, trace_id: str, new_schedule: Dict[str, Any]) -> Dict[str, Any]:
        """更新定时任务
        
        Args:
            trace_id: 跟踪ID，由后端传入
            new_schedule: 新的调度信息
            
        Returns:
            操作结果
        """
        # 实际项目中，这里应该调用外部调度系统API更新任务
        # 例如：requests.put(f"{self.base_url}/schedules/{trace_id}", json=new_schedule)
        
        # 模拟实现，返回操作结果
        return {
            "success": True,
            "message": f"定时任务 {trace_id} 已成功更新"
        }
    
    def cancel_task(self, trace_id: str) -> Dict[str, Any]:
        """取消任务
        
        Args:
            trace_id: 跟踪ID，由后端传入
            
        Returns:
            操作结果
        """
        # 实际项目中，这里应该调用外部API取消任务
        # 例如：requests.post(f"{self.base_url}/tasks/{trace_id}/cancel")
        
        # 模拟实现，返回操作结果
        return {
            "success": True,
            "message": f"任务 {trace_id} 已成功取消"
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
    
    def pause_task(self, trace_id: Optional[str] = None, external_job_id: Optional[str] = None) -> Dict[str, Any]:
        """暂停任务
        
        Args:
            trace_id: 跟踪ID，由后端传入（可选）
            external_job_id: 外部任务ID（可选）
            
        Returns:
            操作结果
        """
        # 实际项目中，这里应该根据提供的ID类型调用不同的外部API
        # 例如：
        # if external_job_id:
        #     requests.post(f"{self.base_url}/jobs/{external_job_id}/pause")
        # else:
        #     requests.post(f"{self.base_url}/tasks/{trace_id}/pause")
        
        # 模拟实现，返回操作结果
        target_id = external_job_id if external_job_id else trace_id
        return {
            "success": True,
            "message": f"任务 {target_id} 已成功暂停"
        }
    
    def resume_task(self, trace_id: Optional[str] = None, external_job_id: Optional[str] = None) -> Dict[str, Any]:
        """恢复任务
        
        Args:
            trace_id: 跟踪ID，由后端传入（可选）
            external_job_id: 外部任务ID（可选）
            
        Returns:
            操作结果
        """
        # 实际项目中，这里应该根据提供的ID类型调用不同的外部API
        # 例如：
        # if external_job_id:
        #     requests.post(f"{self.base_url}/jobs/{external_job_id}/resume")
        # else:
        #     requests.post(f"{self.base_url}/tasks/{trace_id}/resume")
        
        # 模拟实现，返回操作结果
        target_id = external_job_id if external_job_id else trace_id
        return {
            "success": True,
            "message": f"任务 {target_id} 已成功恢复"
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
    
    def register_recurring_task(
        self,
        task_name: str,
        task_content: Dict[str, Any],
        parameters: Dict[str, Any],
        user_id: str,
        interval_seconds: int,
        max_runs: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        注册周期任务 (Interval Loop)
        
        Args:
            task_name: 任务名称
            task_content: 任务内容，包含具体执行定义
            parameters: 执行参数
            user_id: 用户ID
            interval_seconds: 执行间隔（秒）
            max_runs: 最大执行次数（可选，None表示无限次）
            
        Returns:
            操作结果，包含后端生成的trace_id
        """
        parameters["_user_id"] = user_id

        payload = {
            "task_name": task_name,
            "task_content": task_content,
            "input_params": parameters,
            # 关键：构造 loop_config
            "loop_config": {
                "interval_sec": interval_seconds,
                "max_rounds": max_runs if max_runs else 0 # 假设后端 0 代表无限
            },
            "is_temporary": True
        }

        resp_data = self._call_ad_hoc_api(payload)

        return {
            "success": True,
            "message": resp_data["message"],
            "trace_id": resp_data["trace_id"], # 返回后端生成的 ID
            "interval_seconds": interval_seconds,
            "max_runs": max_runs
        }
        
    def cancel_recurring_task(self, trace_id: str) -> Dict[str, Any]:
        """取消周期任务
        
        Args:
            trace_id: 跟踪ID，由后端传入
            
        Returns:
            操作结果
        """
        # 实际项目中，这里应该调用外部调度系统API取消周期任务
        # 例如：requests.delete(f"{self.base_url}/recurring-tasks/{trace_id}")
        
        # 模拟实现，返回操作结果
        return {
            "success": True,
            "message": f"周期任务 {trace_id} 已成功取消"
        }
    
    def update_recurring_task(self, trace_id: str, interval_seconds: Optional[int] = None, max_runs: Optional[int] = None, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """更新周期任务
        
        Args:
            trace_id: 跟踪ID，由后端传入
            interval_seconds: 新的执行间隔（秒，可选）
            max_runs: 新的最大执行次数（可选，None表示无限次）
            parameters: 新的执行参数（可选）
            
        Returns:
            操作结果
        """
        # 实际项目中，这里应该调用外部调度系统API更新周期任务
        # 例如：requests.put(f"{self.base_url}/recurring-tasks/{trace_id}", json={k: v for k, v in {"interval_seconds": interval_seconds, "max_runs": max_runs, "parameters": parameters}.items() if v is not None})
        
        # 模拟实现，返回操作结果
        update_info = []
        if interval_seconds is not None:
            update_info.append(f"执行间隔为 {interval_seconds} 秒")
        if max_runs is not None:
            update_info.append(f"最大执行次数为 {max_runs}")
        if parameters is not None:
            update_info.append("执行参数")
        
        update_desc = "，".join(update_info) if update_info else "无更新内容"
        return {
            "success": True,
            "message": f"周期任务 {trace_id} 已成功更新，更新内容：{update_desc}"
        }
        
    









    def get_task_status(self, trace_id: str, external_job_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取任务状态
        
        Args:
            trace_id: 跟踪ID，由后端传入
            external_job_id: 外部任务ID（可选）
            
        Returns:
            任务状态信息，如果任务不存在则返回None
        """
        # 实际项目中，这里应该根据是否提供external_job_id调用不同的外部API
        # 例如：
        # if external_job_id:
        #     requests.get(f"{self.base_url}/jobs/{external_job_id}/status")
        # else:
        #     requests.get(f"{self.base_url}/tasks/{trace_id}")
        
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
                "trace_id": trace_id,
                "execution_status": "RUNNING",
                "control_status": "NORMAL",
                "is_cancelable": True,
                "is_resumable": True,
                "task_type": "web_crawler",
                "description": "爬取京东商品数据"
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
                    "trace_id": "trace_123",
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
                    "trace_id": "trace_456",
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
    
    