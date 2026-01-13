from thespian.actors import Actor
import logging
import json
from typing import Any, Dict, Optional
from capabilities import get_capability
from capabilities.registry import capability_registry
from capabilities.llm.interface import ILLMCapability
from capabilities.llm_memory.interface import IMemoryCapability

try:
    ##TODO:怎么装这个
    from skills_for_all_agent.skill_tool import skill_tool, DEFAULT_SKILLS_ROOT
except Exception:  # pragma: no cover - optional dependency
    skill_tool = None
    DEFAULT_SKILLS_ROOT = None


from common.messages.task_messages import TaskCompletedMessage, MCPTaskRequestMessage as MCPTaskMessage
from common.messages.types import MessageType



class MCPCapabilityActor(Actor):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.agent_id = "agent_001"
        self.skill_tool = skill_tool
        self.skills_root = DEFAULT_SKILLS_ROOT
        self.skill_index = []
        self._init_skills()


    def receiveMessage(self, msg: Any, sender: str) -> None:
        if isinstance(msg, MCPTaskMessage):
            self._handle_new_task(msg, sender)

    def _handle_new_task(self, msg: MCPTaskMessage, sender: str):
        task_id = str(msg.step)
        description = msg.description
        params = msg.params or {}
        agent_id = self._extract_agent_id_from_path(getattr(msg, "task_path", "") or "")
        if agent_id:
            self.agent_id = agent_id

        description = self._rewrite_with_memory(
            user_id=getattr(msg, "user_id", None),
            task_path=getattr(msg, "task_path", None),
            text=description,
        )

        self.logger.info(f"[{task_id}] Received task: {description}")


         # Step 0: 尝试匹配并执行技能
        skill_name = self._match_skill(description, params)
        if skill_name:
            try:
                result = self._execute_via_skill(skill_name, description, params)
                self._send_task_completed(sender, task_id, result)
                return
            except Exception as e:
                self.logger.warning(f"Skill execution failed ({skill_name}): {e}. Falling back to default flow.")


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


    def _rewrite_with_memory(self, user_id: Optional[str], task_path: Optional[str], text: str) -> str:
        if not text:
            return text
        try:
            memory_cap = get_capability("llm_memory", expected_type=IMemoryCapability)
        except Exception:
            return text
        scope = self._build_memory_scope(user_id, task_path)
        if not scope:
            return text
        try:
            memory_context = memory_cap.build_execution_context(scope, text)
        except Exception as e:
            self.logger.info(f"Memory read skipped: {e}")
            return text
        if not memory_context or memory_context.strip() == "无相关记忆可用。":
            return text
        try:
            llm = get_capability("llm", expected_type=ILLMCapability)
            prompt = (
                "你是任务语句补全器。根据记忆，将用户语句补全为可执行的明确指令。\n"
                "[记忆]\n"
                f"{memory_context}\n"
                "[原始语句]\n"
                f"{text}\n"
                "要求：\n"
                "1. 只输出补全后的语句\n"
                "2. 若无需补全，原样输出\n"
                "3. 不要解释\n"
            )
            rewritten = llm.generate(prompt, max_tokens=200, temperature=0.2)
            rewritten = rewritten.strip()
            if rewritten:
                self.logger.info(f"Rewritten MCP task: {text} -> {rewritten}")
                return rewritten
        except Exception as e:
            self.logger.info(f"Rewrite skipped: {e}")
        return text
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
            destination=str(destination),
            task_id=task_id,
            trace_id=task_id,  # 使用 task_id 作为 trace_id
            task_path="/",  # 根任务路径
            result=result,
            status="SUCCESS",
            agent_id=self.agent_id
        ))

    def _init_skills(self) -> None:
        if not self.skill_tool:
            self.logger.info("skills-for-all-agent not available. Skipping skill initialization.")
            return
        self._load_skills()
        self.skill_index = self._list_skills()
        if self.skill_index:
            self.logger.info(f"Loaded {len(self.skill_index)} skills from {self.skills_root}")
        else:
            self.logger.info("No skills loaded.")

    def _load_skills(self) -> None:
        tool = self.skill_tool
        if not tool:
            return
        for method_name in ("load_skills", "load", "init", "initialize"):
            method = getattr(tool, method_name, None)
            if callable(method):
                try:
                    method(self.skills_root)
                    return
                except TypeError:
                    try:
                        method()
                        return
                    except Exception:
                        continue
                except Exception:
                    continue

    def _list_skills(self) -> list:
        tool = self.skill_tool
        if not tool:
            return []
        for method_name in ("list_skills", "get_skills", "list", "available_skills"):
            method = getattr(tool, method_name, None)
            if callable(method):
                try:
                    skills = method()
                    return self._normalize_skill_list(skills)
                except Exception:
                    continue
        if isinstance(tool, (list, tuple)):
            return self._normalize_skill_list(tool)
        return []

    @staticmethod
    def _normalize_skill_list(skills: Any) -> list:
        if not skills:
            return []
        normalized = []
        for item in skills:
            if isinstance(item, str):
                normalized.append({"name": item, "description": ""})
            elif isinstance(item, dict):
                normalized.append({
                    "name": item.get("name") or item.get("id") or "",
                    "description": item.get("description") or item.get("desc") or "",
                })
        return [s for s in normalized if s.get("name")]

    def _match_skill(self, description: str, params: Dict) -> str:
        explicit = params.get("skill") or params.get("skill_name") or params.get("tool")
        if explicit:
            return str(explicit)
        if not self.skill_index:
            return ""
        desc_lower = description.lower()
        for skill in self.skill_index:
            name = skill.get("name", "")
            if name and name.lower() in desc_lower:
                return name
        return ""

    def _execute_via_skill(self, skill_name: str, description: str, params: Dict) -> Any:
        tool = self.skill_tool
        if not tool:
            raise RuntimeError("Skill tool not initialized")
        payload = dict(params)
        payload.setdefault("query", description)
        payload.setdefault("description", description)
        for method_name in ("run_skill", "run", "execute", "invoke", "call"):
            method = getattr(tool, method_name, None)
            if callable(method):
                try:
                    return method(skill_name, payload)
                except TypeError:
                    try:
                        return method(skill_name, payload, self.skills_root)
                    except Exception:
                        continue
                except Exception:
                    continue
        if callable(tool):
            try:
                return tool(skill_name=skill_name, params=payload, skills_root=self.skills_root)
            except TypeError:
                return tool(skill_name, payload)
        raise RuntimeError("Skill execution failed: no compatible runner found")

    @staticmethod
    def _extract_agent_id_from_path(task_path: str) -> str:
        if not task_path:
            return ""
        parts = [part for part in task_path.split("/") if part]
        return parts[0] if parts else ""

    @staticmethod
    def _build_memory_scope(user_id: Optional[str], task_path: Optional[str]) -> str:
        if not user_id:
            return ""
        root_agent_id = ""
        if task_path:
            parts = [part for part in task_path.split("/") if part]
            root_agent_id = parts[0] if parts else ""
        if root_agent_id:
            return f"{user_id}:{root_agent_id}"
        return user_id
