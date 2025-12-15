from thespian.actors import Actor
import logging
import json
from typing import Any, Dict
from ..capabilities import get_capability
from ..capabilities.registry import capability_registry
from ..capabilities.llm.interface import ILLMCapability



from ..common.messages.task_messages import TaskCompletedMessage, MCPTaskRequestMessage as MCPTaskMessage
from ..common.messages.types import MessageType



class MCPCapabilityActor(Actor):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.agent_id = "agent_001"

    def receiveMessage(self, msg: Any, sender: str) -> None:
        if isinstance(msg, MCPTaskMessage):
            self._handle_new_task(msg, sender)

    def _handle_new_task(self, msg: MCPTaskMessage, sender: str):
        task_id = str(msg.step)
        description = msg.description
        params = msg.params or {}

        self.logger.info(f"[{task_id}] Received task: {description}")

        # Step 1: 判断是否为查询任务
        is_query = self._judge_is_query_with_llm(description, params)

        if is_query:
            # Step 2: 直接通过 context_resolver 获取真实数据结果
            result = self._execute_data_query_via_context_resolver(description)
            self._send_task_completed(sender, task_id, result)
        else:
            # Step 3: 非查询任务，走 MCP LLM
            result = self._execute_via_mcp_llm(description, params)
            self._send_task_completed(sender, task_id, result)

    def _judge_is_query_with_llm(self, description: str, params: Dict) -> bool:
        # from tasks.capabilities.registry import capability_registry
        llm = get_capability("llm", expected_type=ILLMCapability)
        prompt = (
            f"任务描述: {description}\n参数: {json.dumps(params, ensure_ascii=False)}\n\n"
            "该任务是否仅为读取或查询系统(这里的系统指的是企业内部系统的)内数据（不包含创建、修改、删除、发送等操作）？\n"
            "请严格返回 JSON: {\"is_query\": true} 或 {\"is_query\": false}"
        )
        try:
            res = llm.generate(prompt, parse_json=True, max_tokens=100)
            return bool(res.get("is_query", False))
        except Exception as e:
            self.logger.warning(f"LLM query judgment failed: {e}. Defaulting to non-query.")
            return False

    def _execute_data_query_via_context_resolver(self, description: str) -> Any:
        """
        使用 context_resolver 直接执行数据查询并返回结果
        """
        try:
            from ..capabilities.context_resolver.interface import IContextResolverCapbility
            context_resolver: IContextResolverCapbility = get_capability(
                "context_resolver", IContextResolverCapbility
            )

            # 将整个任务描述包装为一个上下文需求项
            context_req = {
                "query_result": description  # key 名任意，只要一致即可
            }

            resolved_dict = context_resolver.resolve_context(context_req, self.agent_id)

            # 提取结果
            result = resolved_dict.get("query_result")
            if result:
                # 获取图表绘制能力
                from ..capabilities.draw_charts.interface import IChartDrawer
                chart_drawer: IChartDrawer = get_capability(
                    "chart_drawer", IChartDrawer
                )
                if chart_drawer:
                    result = chart_drawer.enhance_with_charts(result)

            if result is None:
                return "未查询到相关数据"
            return result

        except Exception as e:
            self.logger.error(f"Context resolver query failed: {e}", exc_info=True)
            return f"查询执行异常: {str(e)}"

    def _execute_via_mcp_llm(self, description: str, params: Dict) -> str:
        llm = get_capability("llm", expected_type=ILLMCapability)
        prompt = (
            f"你是一个智能代理，请完成以下任务：\n"
            f"任务: {description}\n"
            f"参数: {json.dumps(params, ensure_ascii=False)}\n\n"
            "请直接输出任务结果，不要解释。"
        )
        try:
            return llm.generate(prompt, parse_json=False, max_tokens=500)
        except Exception as e:
            return f"任务执行失败: {str(e)}"

    def _send_task_completed(self, destination: str, task_id: str, result: Any):
        self.send(destination, TaskCompletedMessage(
            message_type=MessageType.TASK_COMPLETED,
            source="MCP_Actor",
            destination=destination,
            task_id=task_id,
            trace_id=task_id,  # 使用 task_id 作为 trace_id
            task_path="/",  # 根任务路径
            result=result,
            status="SUCCESS",
            agent_id=self.agent_id
        ))