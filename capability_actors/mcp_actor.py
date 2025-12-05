from thespian.actors import Actor
import logging
import json
from typing import Any, Dict
from capabilities import get_capability # 假设有获取所有工具描述的方法
from common.messages import TaskMessage,DataQueryResponse,DataQueryRequest,InitDataQueryActor
from common.messages.task_messages import TaskCompleted,MCPTaskMessage
import datetime
import uuid



# 模拟 LLM 调用的辅助函数 (实际项目中请替换为您的 LLM Client)
def call_llm_json(prompt: str) -> Dict:
    """调用 LLM 并期望返回 JSON"""
    # 这里应该连接您的 GPT-4 / Claude / DeepSeek
    # 模拟返回...
    return {} 

class MCPCapabilityActor(Actor):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.data_actor_addr = "DataActor" # 实际场景中可能需要动态查找
        self.agent_id = "agent_001"
        self.origin = None
        
        # === 关键状态管理 ===
        # 用于存储发出了 DataRequest 但还没收到 Response 的任务上下文
        # Key: request_id (DataQueryRequest 的 ID)
        # Value: { "original_sender": str, "task_id": str, "step": int }
        self.pending_tasks: Dict[str, Dict] = {}

    def receiveMessage(self, msg: Any, sender: str) -> None:
        try:
            # 1. 处理新进来的 MCP 任务
            if self._is_mcp_task(msg):
                self._handle_new_task(msg, sender)
            
            # 2. 处理从 DataActor 回来的异步响应
            elif isinstance(msg, DataQueryResponse):
                self._handle_data_response(msg, sender)
                
            # 3. 其他消息忽略或报错
            else:
                pass 

        except Exception as e:
            self.logger.error(f"Actor Error: {e}", exc_info=True)
            # 如果能找到 task_id，最好发一个包含 error 的 TaskCompleted
    # ================= 核心逻辑方法 =================

    def _handle_new_task(self, msg: 'MCPTaskMessage', sender: str):
        """
        处理新进来的 MCP 任务消息（类型已确定为 MCPTaskMessage）
        """
        step = msg.step
        description = msg.description
        params = msg.params or {}
        executor = msg.executor  # 可能为 None，表示需自动选择
        task_id = str(step)  # 使用 step 作为任务 ID

        self.logger.info(f"[{task_id}] 接收任务: {description} (Executor: {executor or 'AUTO'})")
        self.origin = sender  # 可选：记录原始调用方
        # === A. 意图判断 (LLM) ===
        # 模拟：如果描述里有 "查询" 或 "Search"，走 DataActor 流程
        is_query_intent = self._judge_is_query(description,params)

        if is_query_intent:
            self.logger.info(f"[{task_id}] 判定为数据查询，转发至 DataActor")
            self._start_data_query_flow(sender, task_id, description)
        else:
            self.logger.info(f"[{task_id}] 判定为动作执行，本地处理")
            self._execute_action_flow(sender, task_id, description, params)

    def _start_data_query_flow(self, original_sender: str, task_id: str, query_text: str):
        """
        开启数据查询流程 (Async)
        流程: Init -> Request -> (挂起) -> Receive Response
        """
        # 1. 发送初始化消息 (告诉 DataActor 准备好上下文)
        init_msg = InitDataQueryActor(
            agent_id=self.agent_id,
            source="MCP_Actor",
            destination=self.data_actor_addr
        )
        self.send(self.data_actor_addr, init_msg)

        # 2. 生成 Request ID 并发送正式请求
        req_id = f"req_{uuid.uuid4()}"
        req_msg = DataQueryRequest(
            request_id=req_id,
            query=query_text,
            source="MCP_Actor",
            destination=self.data_actor_addr
        )
        self.send(self.data_actor_addr, req_msg)

        # 3. [关键] 挂起任务状态
        # 我们必须记住这个 req_id 对应哪个原始任务，否则 DataActor 回复时我们就忘了要发给谁了
        self.pending_tasks[req_id] = {
            "original_sender": original_sender,
            "task_id": task_id,
            "description": query_text,
            "start_time": datetime.now()
        }
        self.logger.debug(f"任务 {task_id} 已挂起，等待请求 {req_id} 返回")

    def _handle_data_response(self, msg: DataQueryResponse, sender: str):
        """
        处理 DataActor 返回的结果，并完成原始任务
        """
        req_id = msg.request_id
        
        # 1. 查找上下文
        context = self.pending_tasks.pop(req_id, None)
        if not context:
            self.logger.warning(f"收到未知的 DataResponse: {req_id}，可能已超时或丢弃")
            return

        original_sender = self.origin
        task_id = context["task_id"]

        # 2. 构造最终结果
        if msg.error:
            final_result = f"查询失败: {msg.error}"
            # 甚至可以在这里再次调用 LLM 兜底："数据查询失败，但我根据常识推断..."
        else:
            final_result = msg.result

        # 3. 发送 TaskCompleted 给最外层的调用方
        complete_msg = TaskCompleted(
            source="MCP_Actor",
            destination=original_sender, # 回复给最初的发起人
            task_id=task_id,
            result=final_result
        )
        self.send(original_sender, complete_msg)
        self.logger.info(f"[{task_id}] 数据查询任务闭环完成")

    def _execute_action_flow(self, sender: str, task_id: str, description: str, params: Dict):
        """
        动作执行流程 (同步/混合执行)
        逻辑: 尝试真实工具 -> 失败则 LLM 模拟 -> 返回 TaskCompleted
        """
        # ... 这里复用之前的 _try_real_execution 和 _fallback_to_llm 逻辑 ...
        
        # 模拟执行结果
        success = True # 假设执行成功
        if success:
            result_data = f"动作 '{description}' 执行成功 (Real Tool)"
        else:
            result_data = f"动作 '{description}' 已模拟完成 (LLM Fallback)"

        # 直接发送完成消息
        complete_msg = TaskCompleted(
            source="MCP_Actor",
            destination=sender,
            task_id=task_id,
            result=result_data
        )
        self.send(sender, complete_msg)

    def _is_mcp_task(self, msg) -> bool:
        # 简单的类型判断辅助函数
        if isinstance(msg, dict) and msg.get('type') == 'MCP':
            return True
        # 如果您有专门的 MCPTaskMessage 类
        # if isinstance(msg, MCPTaskMessage): return True
        return False



    def _judge_is_query(self, description: str, params: Dict) -> bool:
        """
        使用 LLM 判断这是否是一个纯读取/查询数据的任务
        """
        prompt = (
            f"任务描述: {description}\n"
            f"参数: {params}\n"
            "判断该任务是 '数据查询(Query)' 还是 '动作执行(Action)'？\n"
            "如果是获取信息、查询状态、读取文件而不产生副作用，返回 true。\n"
            "如果是上传、修改、删除、发送消息，返回 false。\n"
            "请仅返回 JSON: {\"is_query\": true/false}"
        )
        # 模拟 LLM 调用
        # result = call_llm_json(prompt)
        # return result.get("is_query", False)
        
        # 简单模拟：如果描述包含 "查询" 或 "获取"
        return "查询" in description or "获取" in description

    def _handle_data_query(self, original_sender) -> Any:
        """
        向 DataActor 发送初始化消息并获取结果
        注意：在 Actor 模型中，request/response 通常是异步的。
        这里假设我们使用 system.ask() 或者同步等待的方式（视您的 Thespian 配置而定）。
        """
        # 1. 构建消息对象
        query_msg = InitDataQueryActor(
            agent_id=self.agent_id,
            source="MCP_Actor",
            destination="Data_Actor"
        )
        
        # 2. 发送给 DataActor 并等待回复
        # 这里的 self.send 是异步的，如果要拿返回值，通常用 self.system.ask() 
        # 或者在此处逻辑需要改成异步回调模式。
        # 为了代码逻辑连贯，这里假设有一个同步获取的 helper wrapper
        response = self.ask(self.data_actor_addr, query_msg, timeout=5)
        
        if response:
            return response
        else:
            return "DataActor 未返回数据"

    def _enrich_params_from_data_actor(self, params: Dict) -> Dict:
        """
        检查 params 是否需要从 DataActor 补充数据
        """
        # 如果参数里包含形如 "$variable" 的占位符，或者 LLM 认为需要补充上下文
        # 这里简化为：先发一个 InitDataQueryActor 拿回所有上下文，然后替换
        
        # 1. 拿数据
        context_data = self._handle_data_query(None) # 复用上面的查询逻辑
        
        # 2. 简单的参数替换逻辑 (示例)
        new_params = params.copy()
        if isinstance(context_data, dict):
            for k, v in new_params.items():
                if isinstance(v, str) and v.startswith("$") and v[1:] in context_data:
                    new_params[k] = context_data[v[1:]]
                    self.logger.info(f"参数替换: {k} -> {new_params[k]}")
                    
        return new_params

    def _select_best_executor(self, description: str, params: Dict) -> str:
        """
        从可用工具列表中选择最合适的 Executor
        """
        # 假设有一个函数能返回所有工具的 {name: desc}
        # all_tools = get_all_capabilities_description() 
        all_tools = [
            {"name": "nas_file_manager", "desc": "管理NAS文件，上传下载"},
            {"name": "email_sender", "desc": "发送电子邮件"},
            {"name": "report_generator", "desc": "生成PDF报告"}
        ]
        
        prompt = (
            f"任务: {description}\n"
            f"可用工具: {json.dumps(all_tools, ensure_ascii=False)}\n"
            "请根据任务描述，从可用工具中选择最合适的一个 executor name。\n"
            "返回 JSON: {\"executor\": \"name\"}"
        )
        
        # llm_resp = call_llm_json(prompt)
        # return llm_resp.get("executor")
        
        # 模拟返回
        return "nas_file_manager"

    def _execute_with_fallback(self, sender, step_id, executor_name, description, params):
        """
        复用之前的逻辑：硬执行 -> 失败 -> 软模拟
        """
        # 1. 尝试硬执行
        real_result = self._try_real_execution(executor_name, params)
        
        if real_result["success"]:
            self.send(sender, {
                "status": "success",
                "step": step_id,
                "result": real_result["data"],
                "mode": "real_tool",
                "executor": executor_name
            })
        else:
            # 2. 失败则 LLM 兜底
            self.logger.warning(f"真实工具 {executor_name} 执行失败，转 LLM 模拟")
            sim_result = self._fallback_to_llm(description, executor_name, params, real_result["error"])
            
            self.send(sender, {
                "status": "success",
                "step": step_id,
                "result": sim_result,
                "mode": "llm_simulation",
                "executor": executor_name,
                "original_error": real_result["error"]
            })

    def _try_real_execution(self, executor_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        尝试获取真实工具并执行
        """
        try:
            # 动态获取能力 (这里假设 get_capability 能根据名字返回具体的对象)
            # 例如: nas_file_manager = get_capability("nas_file_manager")
           ## TODO: 获取能力
           return "正在执行"

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _fallback_to_llm(self, description: str, executor: str, params: Dict, error_msg: str) -> str:
        """
        兜底逻辑：让大模型生成一段“执行结果”
        """
        try:
            # 构建 Prompt
            prompt = (
                f"任务描述: {description}\n"
                f"原定执行器: {executor}\n"
                f"参数详情: {json.dumps(params, ensure_ascii=False)}\n"
                f"失败原因: {error_msg}\n\n"
                "现在发生了上述技术错误。"
                "请尽可能的生成一些内容来解决用户的问题"
                "并想办法平息用户的怒火。"
            )
            
            # 调用您的大模型接口
            # ai_response = call_llm_generation(prompt)
            
            # 模拟 LLM 返回
            ai_response = f"[模拟执行] 已成功通过备用通道完成 '{description}'。文件已归档至 {params.get('destination')}，操作ID: sim-998877。"
            
            return ai_response
            
        except Exception as e:
            # 如果连兜底都挂了
            return f"任务执行失败，且模拟生成也失败: {e}"