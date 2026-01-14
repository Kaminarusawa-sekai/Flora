from typing import Dict, Any, Optional
import uuid
import requests
from common.task_execution import TaskExecutionContextDTO
from common.base import ExecutionStatus

class TaskClient:
    """任务执行客户端，用于与外部任务执行系统交互"""
    
    def __init__(self, base_url: str = "http://localhost:8001/api/v1", events_base_url: str = "http://localhost:8004/api/v1"):
        self.base_url = base_url.rstrip('/')
        self.events_base_url = events_base_url.rstrip('/')
         # 实际项目中，这里应该包含认证信息、超时设置等
        # 实际项目中，这里建议初始化 requests.Session() 以复用 TCP 连接
        self.session = requests.Session()
    
    def _request(self, method: str, endpoint: str, json: Optional[Dict] = None, params: Optional[Dict] = None, use_events_url: bool = False) -> Dict[str, Any]:
        """通用的 HTTP 请求封装"""
        base_url = self.events_base_url if use_events_url else self.base_url
        url = f"{base_url}{endpoint}"
        try:
            response = self.session.request(method, url, json=json, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            # 生产环境建议使用 logger 记录详细报错
            raise Exception(f"API Request Failed [{method} {endpoint}]: {str(e)}")
    
    def _resolve_trace_id(self, trace_id: Optional[str], request_id: Optional[str]) -> str:
        """
        核心逻辑：ID 自动解析器
        
        1. 如果有 trace_id，直接使用（最高效）。
        2. 如果只有 request_id，调用接口换取 trace_id。
        3. 如果都没有，抛出异常。
        """
        if trace_id:
            return trace_id
        
        if request_id:
            # 调用 Server 端定义的 /request-id-to-trace/{request_id} 接口
            endpoint = f"/request-id-to-trace/{request_id}"
            resp = self._request("GET", endpoint)
            
            if resp.get("success") and resp.get("trace_id"):
                return resp["trace_id"]
            else:
                raise ValueError(f"无法通过 request_id [{request_id}] 找到对应的 trace_id，任务可能尚未创建或已过期。")
        
        raise ValueError("必须提供 trace_id 或 request_id 其中之一")
    
    def submit_task(
        self,
        task_name: str,           # 新增：任务要有名字
        task_content: Dict[str, Any], # 新增：必须告诉后端执行什么逻辑
        parameters: Dict[str, Any],
        user_id: str,
        request_id: Optional[str] = None  # 新增：允许外部传入 request_id
    ) -> str:
        """
        提交一次性任务
        注意：trace_id 不再由外部传入，而是由后端生成并返回
        
        Args:
            task_name: 任务名称
            task_content: 任务内容，包含具体执行定义
            parameters: 执行参数
            user_id: 用户ID
            request_id: 业务侧/幂等控制ID（可选）
            
        Returns:
            后端生成的trace_id
        """
        # 1. 如果外部没有传入 request_id，客户端自动生成一个 UUID
        #    这样既保证了幂等性，也方便后续客户端直接用这个 ID 查询
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # 将 user_id 放入 input_params
        parameters["_user_id"] = user_id

        payload = {
            "task_name": task_name,
            "task_content": task_content,
            "input_params": parameters,
            "loop_config": None,      # 关键：没有循环配置 = 单次运行
            "is_temporary": True,
            "request_id": request_id,  # 传递给 Server
            "user_id": user_id  # 传递给 Server
        }

        resp_data = self._request("POST", "/ad-hoc-tasks", json=payload)
        
        # 返回后端生成的 trace_id
        return resp_data["trace_id"]
    
    def register_scheduled_task(
        self,
        task_name: str,
        task_content: Dict[str, Any],
        schedule: Dict[str, Any],
        parameters: Dict[str, Any],
        user_id: str,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        注册定时任务（支持 CRON 表达式）
        
        Args:
            task_name: 任务名称
            task_content: 任务内容，包含具体执行定义
            schedule: 调度配置，包含 cron_expression 等字段
            parameters: 执行参数
            user_id: 用户ID
            request_id: 业务侧/幂等控制ID（可选）
            
        Returns:
            操作结果，包含后端生成的trace_id
        """
        # 如果外部没有传入 request_id，客户端自动生成一个 UUID
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # 将 user_id 放入 input_params
        parameters["_user_id"] = user_id

        # 根据调度类型构造 payload
        payload = {
            "task_name": task_name,
            "task_content": task_content,
            "input_params": parameters,
            "loop_config": None,
            "is_temporary": True,
            "schedule_type": "CRON",
            "schedule_config": schedule,  # 包含 cron_expression 字段
            "request_id": request_id
        }

        resp_data = self._request("POST", "/ad-hoc-tasks", json=payload)

        return {
            "success": True,
            "message": resp_data["message"],
            "trace_id": resp_data["trace_id"],
            "request_id": request_id,
            "schedule_type": "CRON",
            "schedule_config": schedule
        }
    

    def register_delayed_task(
        self,
        task_name: str,
        task_content: Dict[str, Any],
        delay_seconds: int,
        parameters: Dict[str, Any],
        user_id: str,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        if not request_id:
            request_id = str(uuid.uuid4())

        parameters["_user_id"] = user_id

        payload = {
            "task_name": task_name,
            "task_content": task_content,
            "input_params": parameters,
            "loop_config": None,
            "is_temporary": True,
            "schedule_type": "DELAYED",
            "schedule_config": {"delay_seconds": delay_seconds},
            "request_id": request_id
        }

        resp_data = self._request("POST", "/ad-hoc-tasks", json=payload)

        return {
            "success": True,
            "message": resp_data["message"],
            "trace_id": resp_data["trace_id"],
            "request_id": request_id,
            "schedule_type": "DELAYED",
            "schedule_config": {"delay_seconds": delay_seconds}
        }


    def unregister_scheduled_task(self, trace_id: Optional[str] = None, request_id: Optional[str] = None) -> Dict[str, Any]:
        """取消注册定时任务
        
        Args:
            trace_id: 跟踪ID，由后端传入（可选）
            request_id: 业务侧/幂等控制ID（可选）
            
        Returns:
            操作结果
        """
        # 自动解析 ID
        actual_trace_id = self._resolve_trace_id(trace_id, request_id)
        
        # 调用外部调度系统API取消任务
        # 使用 /traces/{trace_id}/cancel 端点来取消任务
        endpoint = f"/traces/{actual_trace_id}/cancel"
        return self._request("POST", endpoint)
    
    def update_scheduled_task(self, trace_id: Optional[str] = None, new_schedule: Dict[str, Any] = None, request_id: Optional[str] = None) -> Dict[str, Any]:
        """更新定时任务
        
        Args:
            trace_id: 跟踪ID，由后端传入（可选）
            new_schedule: 新的调度信息（可选）
            request_id: 业务侧/幂等控制ID（可选）
            
        Returns:
            操作结果
        """
        # 自动解析 ID
        actual_trace_id = self._resolve_trace_id(trace_id, request_id)
        
        # 构建请求体
        payload = {}
        
        # 添加调度配置（如果提供）
        if new_schedule is not None:
            payload["schedule_config"] = new_schedule
        
        # 调用外部调度系统API更新任务
        # 使用 /traces/{trace_id}/modify 端点来更新任务
        endpoint = f"/traces/{actual_trace_id}/modify"
        return self._request("PATCH", endpoint, json=payload)
    
    def cancel_task(self, trace_id: Optional[str] = None, request_id: Optional[str] = None) -> Dict[str, Any]:
        """取消任务
        
        Args:
            trace_id: 跟踪ID，由后端传入（可选）
            request_id: 业务侧/幂等控制ID（可选）
            
        Returns:
            操作结果
        """
        actual_trace_id = self._resolve_trace_id(trace_id, request_id)
        
        # 对应 Server: @router.post("/traces/{trace_id}/cancel")
        endpoint = f"/traces/{actual_trace_id}/cancel"
        return self._request("POST", endpoint)
    
    def pause_task(self, trace_id: Optional[str] = None, request_id: Optional[str] = None) -> Dict[str, Any]:
        """暂停任务
        
        Args:
            trace_id: 跟踪ID，由后端传入（可选）
            request_id: 业务侧/幂等控制ID（可选）
            
        Returns:
            操作结果
        """
        actual_trace_id = self._resolve_trace_id(trace_id, request_id)
        
        # 对应 Server: @router.post("/traces/{trace_id}/pause")
        # 使用 /traces/{trace_id}/pause 端点来暂停指定trace下的所有任务实例
        endpoint = f"/traces/{actual_trace_id}/pause"
        return self._request("POST", endpoint)
    
    def resume_task(self, trace_id: Optional[str] = None, request_id: Optional[str] = None) -> Dict[str, Any]:
        """恢复任务
        
        Args:
            trace_id: 跟踪ID，由后端传入（可选）
            request_id: 业务侧/幂等控制ID（可选）
            
        Returns:
            操作结果
        """
        actual_trace_id = self._resolve_trace_id(trace_id, request_id)
        
        # 对应 Server: @router.post("/traces/{trace_id}/resume")
        # 使用 /traces/{trace_id}/resume 端点来恢复指定trace下的所有任务实例
        endpoint = f"/traces/{actual_trace_id}/resume"
        return self._request("POST", endpoint)
    
    def modify_task(self, new_params: Dict[str, Any], trace_id: Optional[str] = None, request_id: Optional[str] = None) -> Dict[str, Any]:
        """修改任务参数
        
        Args:
            new_params: 新的任务参数
            trace_id: 跟踪ID，由后端传入（可选）
            request_id: 业务侧/幂等控制ID（可选）
            
        Returns:
            操作结果
        """
        target_id = self._resolve_trace_id(trace_id, request_id)
        
        payload = {
            "input_params": new_params,
            "schedule_config": None
        }
        # 对应 Server: @router.patch("/instances/{instance_id}/modify")
        return self._request("PATCH", f"/traces/{target_id}/modify", json=payload)
    
    

    
    def register_recurring_task(
        self,
        task_name: str,
        task_content: Dict[str, Any],
        parameters: Dict[str, Any],
        user_id: str,
        interval_seconds: int,
        max_runs: Optional[int] = None,
        request_id: Optional[str] = None
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
            request_id: 业务侧/幂等控制ID（可选）
            
        Returns:
            操作结果，包含后端生成的trace_id
        """
        if not request_id:
            request_id = str(uuid.uuid4())
        
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
            "is_temporary": True,
            "schedule_type": "LOOP", # 显式指定
            "request_id": request_id
        }

        resp_data = self._request("POST", "/ad-hoc-tasks", json=payload)

        return {
            "success": True,
            "message": resp_data["message"],
            "trace_id": resp_data["trace_id"], # 返回后端生成的 ID
            "request_id": request_id, # 返回给调用者方便后续控制
            "interval_seconds": interval_seconds,
            "max_runs": max_runs
        }
        
    def cancel_recurring_task(self, trace_id: Optional[str] = None, request_id: Optional[str] = None) -> Dict[str, Any]:
        """取消周期任务
        
        Args:
            trace_id: 跟踪ID，由后端传入（可选）
            request_id: 业务侧/幂等控制ID（可选）
            
        Returns:
            操作结果
        """
        # 自动解析 ID
        actual_trace_id = self._resolve_trace_id(trace_id, request_id)
        
        # 调用外部调度系统API取消周期任务
        # 使用 /traces/{trace_id}/cancel 端点来取消任务
        endpoint = f"/traces/{actual_trace_id}/cancel"
        return self._request("POST", endpoint)
    
    def update_recurring_task(self, trace_id: Optional[str] = None, interval_seconds: Optional[int] = None, max_runs: Optional[int] = None, parameters: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None) -> Dict[str, Any]:
        """更新周期任务
        
        Args:
            trace_id: 跟踪ID，由后端传入（可选）
            interval_seconds: 新的执行间隔（秒，可选）
            max_runs: 新的最大执行次数（可选，None表示无限次）
            parameters: 新的执行参数（可选）
            request_id: 业务侧/幂等控制ID（可选）
            
        Returns:
            操作结果
        """
        # 自动解析 ID
        actual_trace_id = self._resolve_trace_id(trace_id, request_id)
        
        # 构建请求体
        payload = {}
        
        # 添加执行参数（如果提供）
        if parameters is not None:
            payload["input_params"] = parameters
        
        # 构建调度配置（如果提供了相关参数）
        schedule_config = {}
        has_schedule_update = False
        
        if interval_seconds is not None:
            schedule_config["interval_sec"] = interval_seconds
            has_schedule_update = True
        
        if max_runs is not None:
            schedule_config["max_rounds"] = max_runs
            has_schedule_update = True
        
        if has_schedule_update:
            payload["schedule_config"] = schedule_config
        
        # 调用外部调度系统API更新任务
        # 使用 /traces/{trace_id}/modify 端点来更新任务
        endpoint = f"/traces/{actual_trace_id}/modify"
        return self._request("PATCH", endpoint, json=payload)
        
    

    def get_task_status(self, trace_id: Optional[str] = None, request_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取任务状态
        
        Args:
            trace_id: 跟踪ID，由后端传入（可选）
            request_id: 业务侧/幂等控制ID（可选）
            
        Returns:
            任务状态信息，如果任务不存在则返回None
        """
        # 自动解析 ID
        actual_trace_id = self._resolve_trace_id(trace_id, request_id)
        
        try:
            # 使用事件系统的 API 端点 /traces/{trace_id}/trace-details
            return self._request("GET", f"/traces/{actual_trace_id}/trace-details", use_events_url=True) 
        except Exception:
            # Fallback 模拟返回
            return {
                "trace_id": actual_trace_id,
                "status": "UNKNOWN",
                "note": "接口调用失败"
            }
    
    def get_tasks_status_by_user(
        self,
        user_id: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """根据用户ID查询所有任务状态，支持时间范围过滤和分页
        
        Args:
            user_id: 用户ID
            start_time: 开始时间（可选，格式：YYYY-MM-DD HH:MM:SS）
            end_time: 结束时间（可选，格式：YYYY-MM-DD HH:MM:SS）
            limit: 每页数量，默认100，最大1000
            offset: 偏移量，默认0
            
        Returns:
            任务状态列表，包含用户ID、任务总数和任务详情
        """
        # 构造查询参数
        params = {
            "limit": limit,
            "offset": offset
        }
        
        # 添加可选的时间范围参数
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        
        # 调用事件系统的 API 端点 /by-user/{user_id}
        return self._request("GET", f"/by-user/{user_id}", params=params, use_events_url=True)

   
    