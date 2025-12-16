"""上下文解析器实现"""
from typing import Dict, Any, List, Optional, Tuple
from ..capability_base import CapabilityBase
import logging
import json
import re
from .interface import IContextResolverCapbility 
import logging
logger = logging.getLogger(__name__)

class TreeContextResolver(IContextResolverCapbility):
    """
    具体的实现类：
    与 TreeManager 集成，利用树形结构进行语义化的层级搜索。
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = {}
        
        # 依赖项：现在使用 tree_manager
        self.tree_manager = None 
        self.llm_client = None
        
        self.variable_pattern = re.compile(r'\$\{([^}]+)\}')
        self.context_templates = {}

    def get_capability_type(self) -> str:
        return 'tree_context_resolver'

    def initialize(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.logger.info("TreeContextResolver initialized with config.")

    def shutdown(self) -> None:
        self.context_templates.clear()
        self.tree_manager = None
        self.logger.info("TreeContextResolver shutdown.")

    def set_dependencies(self, tree_manager: Any=None, llm_client: Any = None) -> None:
        """
        注入 TreeManager 单例和 LLM 客户端
        """
        if tree_manager:
            self.tree_manager = tree_manager
        else:
            from ...agents.tree.tree_manager import treeManager
            self.tree_manager=treeManager
        if llm_client:
            self.llm_client = llm_client
        else:
            from ..llm.interface import ILLMCapability
            from .. import get_capability
            self.llm_client:ILLMCapability = get_capability("llm",ILLMCapability)
        
        self.logger.info("Dependencies (TreeManager, LLM) injected.")

    # ----------------------------------------------------------
    # 核心逻辑：基于 TreeManager 的寻址
    # ----------------------------------------------------------

    def resolve_context(self, context_requirements: Dict[str, str], agent_id: str) -> Dict[str, Any]:
        """
        解析上下文需求：
        1. 先通过 _resolve_kv_via_layered_search 定位数据所在位置（库/表/列）；
        2. 若定位成功，则使用 VannaTextToSQL 执行真实查询，返回实际数据。
        """
        if not self.tree_manager or not self.llm_client:
            self.set_dependencies()

        result = {}
        try:
            path = self.tree_manager.get_full_path(agent_id)
            path_str = " -> ".join(path)
        except:
            path_str = agent_id

        self.logger.info(f"Start resolving context for agent: {agent_id} (Path: {path_str})")

        # 获取当前 Agent 的基础元信息（用于 fallback 或日志）
        base_agent_meta = {}
        try:
            base_agent_meta = self.tree_manager.get_agent_meta(agent_id) or {}
        except Exception as e:
            self.logger.warning(f"Could not retrieve base agent meta for {agent_id}: {e}")

        for key, value_desc in context_requirements.items():
            try:
                query = f"需查找数据: '{key}', 业务描述: '{value_desc}'"
                
                # Step 1: 定位数据位置（库、表、列等）
                leaf_meta = self._resolve_kv_via_layered_search(agent_id, query, key)
                
                if not leaf_meta:
                    self.logger.warning(f"❌ Unresolved '{key}' (Desc: {value_desc}) – no location found")
                    result[key] = None
                    continue

                # Step 2: 如果定位成功，尝试用 Vanna 查询真实数据
                self.logger.info(f"📍 Located '{key}' at: {leaf_meta}")
                
                # 构造 Vanna 所需的 agent_meta 格式：database = "db.table"
                db_name = leaf_meta.get("database") or leaf_meta.get("db")
                table_name = leaf_meta.get("table") or leaf_meta.get("tbl")
                
                if not db_name or not table_name:
                    self.logger.warning(f"⚠️ Incomplete location info for '{key}': {leaf_meta}, skip Vanna query")
                    result[key] = leaf_meta  # 或设为 None，按需
                    continue

                vanna_agent_meta = {
                    "database": f"{db_name}.{table_name}",
                    "database_type": leaf_meta.get("database_type", base_agent_meta.get("database_type", "mysql"))
                }

                # 初始化 Vanna 能力
                from ..registry import capability_registry
                from ..text_to_sql.text_to_sql import ITextToSQLCapability
                text_to_sql_cap: ITextToSQLCapability = capability_registry.get_capability(
                    "text_to_sql", expected_type=ITextToSQLCapability
                )

                text_to_sql_cap.initialize({
                    "agent_id": agent_id,
                    "agent_meta": vanna_agent_meta
                })

                try:
                    # 使用原始业务描述作为查询语句
                    response = text_to_sql_cap.execute_query(user_query=value_desc, context=None)
                    records = response.get("result", [])
                    
                    if records:
                        # 假设返回的是单值或单行，可按需调整
                        resolved_value = records[0] if len(records) == 1 else records
                        result[key] = resolved_value
                        self.logger.info(f"✅ Resolved '{key}' with real data (rows: {len(records)})")
                    else:
                        self.logger.warning(f"🔍 Located but no data returned for '{key}'")
                        result[key] = None  # 或保留 leaf_meta，视业务而定
                        
                finally:
                    # 确保释放资源
                    text_to_sql_cap.shutdown()

            except Exception as e:
                self.logger.error(f"Error resolving key '{key}': {str(e)}", exc_info=True)
                result[key] = None

        return result

    def _resolve_kv_via_layered_search(self, start_agent_id: str, query: str, key: str) -> Optional[Dict]:
        """
        适配 TreeManager 的层级搜索算法
        """
        # 1. 初始定位：获取 start_agent 的父节点，以确定初始的"兄弟层"
        parent_id = self.tree_manager.get_parent(start_agent_id)
        
        # 用于防止死循环（虽然 TreeManager 内部有防环，但搜索逻辑层也保留一份保险）
        visited_layers = set()
        
        # 记录当前视角的节点，用于向上回溯时定位
        current_focus_node = start_agent_id

        while True:
            # --- 1. 确定当前搜索层 (Layer) ---
            if parent_id is None:
                # 核心变更：利用 TreeManager.get_root_agents() 获取根层
                self.logger.debug(f"Searching Root Layer for: {key}")
                current_layer = self.tree_manager.get_root_agents()
                
                # 如果当前聚焦的节点本身就是根节点，且在根层也找不到，循环通常会在后面 Break
            else:
                # 获取父节点的所有子节点（即当前层）
                current_layer = self.tree_manager.get_children(parent_id)

            # --- 防死循环检查 ---
            layer_sig = tuple(sorted(current_layer))
            if layer_sig in visited_layers:
                self.logger.warning("Cycle detected in search layer. Stopping.")
                break
            visited_layers.add(layer_sig)

            # --- 2. 在当前层进行语义匹配 ---
            matched_node_id = self._semantic_match_for_layer(query, current_layer)

            # --- 3. 匹配结果处理 ---
            if matched_node_id:
                # >> 命中分支 >>
                # 使用 TreeManager 获取元数据
                node_meta = self.tree_manager.get_agent_meta(matched_node_id)
                
                # 使用 TreeManager 判断是否叶子
                is_leaf = self.tree_manager.is_leaf_agent(matched_node_id)
                
                self.logger.debug(f"Match found: {matched_node_id} (Is Leaf: {is_leaf})")

                if is_leaf:
                    # 情况 A: 找到叶子节点 -> 成功
                    return node_meta
                else:
                    # 情况 B: 中间节点 -> 向下钻取 (Drill Down)
                    children = self.tree_manager.get_children(matched_node_id)
                    if not children:
                        break # 死胡同
                    
                    # 视角下沉：新的父节点是刚才匹配到的节点
                    parent_id = matched_node_id
                    # (current_focus_node 在向下钻取时其实不重要，因为下一轮直接取 parent 的 children)
                    continue
            else:
                # >> 未命中分支 >>
                # 情况 C: 当前层无匹配 -> 向上回溯 (Bubble Up)
                if parent_id is None:
                    # 已经在根层且未命中 -> 搜索全面失败
                    self.logger.debug("Reached root layer with no match.")
                    break
                
                # 移动视角向上：
                # 我们要找 parent 的兄弟，所以将视角聚焦到 parent
                current_focus_node = parent_id
                # 获取 parent 的 parent
                parent_id = self.tree_manager.get_parent(current_focus_node)
                continue
        
        return None

    def _semantic_match_for_layer(self, query: str, node_ids: List[str]) -> Optional[str]:
        """
        [重构后] 使用 DashScope Qwen 判断当前层中哪个节点匹配 query。
        
        Args:
            query: 自然语言查询，如 "需查找数据: 'user_id', 业务描述: '当前登录用户'"
            node_ids: 当前层的节点ID列表 (List[str])
        
        Returns:
            匹配的 node_id (str)，若无匹配返回 None
        """
        if not node_ids:
            return None

        # 1. 准备候选节点数据
        candidates_text = []
        valid_node_ids = [] # 用于后续校验 LLM 返回的 ID 是否合法

        for nid in node_ids:
            # 从 TreeManager 获取元数据
            meta = self.tree_manager.get_agent_meta(nid)
            if not meta:
                continue

            # 提取关键信息，构建语义描述
            # 优先取 datascope，其次是 capability，最后是 description
            ds = meta.get("datascope") or meta.get("data_scope") or "无数据域定义"
            caps = meta.get("capability") or meta.get("capabilities") or []
            desc_text = meta.get("description", "")

            # 格式化各个字段
            ds_str = str(ds) if isinstance(ds, (dict, list)) else str(ds)
            cap_str = ", ".join(caps) if isinstance(caps, list) else str(caps)

            # 组合成一段利于 LLM 理解的文本
            # 格式: [ID] 数据: ...; 能力: ...; 描述: ...
            node_desc = (
                f"候选节点ID: {nid}\n"
                f"  - 数据范围: {ds_str}\n"
                f"  - 能力声明: {cap_str}\n"
                f"  - 节点描述: {desc_text}"
            )
            
            candidates_text.append(node_desc)
            valid_node_ids.append(nid)

        if not candidates_text:
            return None

        candidates_block = "\n\n".join(candidates_text)

        # 2. 构造 Prompt
        prompt = f"""你是一个分布式系统的数据路由语义匹配引擎。请根据以下数据需求，从候选节点列表中选择**最匹配的一个**。

数据需求:
{query}

候选节点列表:
---
{candidates_block}
---

请严格按照以下规则回答：
1. 分析哪个节点的"数据范围"或"节点描述"能覆盖上述数据需求。
2. 如果有匹配项，请只输出对应的 **节点ID** (例如: user_agent_01)。
3. 如果没有一个候选能合理满足该需求，或者相关性极低，请只输出 "none"。
4. 不要解释，不要加标点，不要包含任何多余文字。
"""

        # 3. 调用 LLM
        try:
            # 假设 self.llm_client 已经初始化并注入
            # 如果你用的是 requests 或特定的 SDK，在这里替换即可
            if not self.llm_client:
                self.logger.warning("LLM client missing, falling back to keyword match.")
                return self._fallback_keyword_match(query, valid_node_ids)

            # 调用大模型 (这里模拟你的 call_qwen 逻辑)
            # answer = self.call_qwen(prompt) 
            answer = self.llm_client.generate(prompt) 
            
            # 清理结果
            answer = answer.strip().replace("'", "").replace('"', "").replace("`", "")
            
            self.logger.info(f"Qwen semantic match result: '{answer}' for query: '{query}'")

            # 4. 结果校验
            if answer.lower() == "none":
                return None

            if answer in valid_node_ids:
                return answer
            else:
                self.logger.warning(f"Qwen returned invalid node_id: '{answer}'. Expected one of: {valid_node_ids}")
                return None

        except Exception as e:
            self.logger.error(f"Exception calling LLM/DashScope: {e}", exc_info=True)
            # 降级策略
            return self._fallback_keyword_match(query, valid_node_ids)

    def _fallback_keyword_match(self, query: str, node_ids: List[str]) -> Optional[str]:
        """
        简单的关键词匹配兜底策略
        """
        import re
        # 提取查询中的关键词（忽略标点）
        keywords = set(re.findall(r'[\w\u4e00-\u9fa5]+', query))
        best_node = None
        max_score = 0

        for nid in node_ids:
            meta = self.tree_manager.get_agent_meta(nid) or {}
            # 将所有元数据转为字符串进行搜索
            content = (
                str(meta.get("datascope", "")) + 
                str(meta.get("description", "")) + 
                str(meta.get("capability", ""))
            ).lower()
            
            score = sum(1 for kw in keywords if kw.lower() in content)
            
            if score > max_score:
                max_score = score
                best_node = nid
        
        return best_node if max_score > 0 else None





    def enhance_param_descriptions_with_context(
        self,
        base_param_descriptions: dict,
        current_inputs: dict
        ) -> dict:
        """
        使用 LLM 将基础参数描述增强为“带上下文”的描述。
        
        Args:
            base_param_descriptions: dict, e.g. {"template_id": "海报模板ID"}
            current_inputs: dict, e.g. {"tenant_id": "t_abc", "activity_id": "act_123"}
        
        Returns:
            dict: {"template_id": "海报模板ID，属于租户 t_abc 和活动 act_123"}
        """
        if not base_param_descriptions:
            return {}
        
        if not self.tree_manager or not self.llm_client:
            self.set_dependencies()

        # 构建上下文字符串（只保留非空、非敏感字段，可扩展过滤逻辑）
        context_items = []
        for k, v in current_inputs.items():
                
            # 2. 类型安全检查
            if not v or not isinstance(v, (str, int, float, bool)):
                continue
                
            v_str = str(v)
            
            # 3. 放宽长度限制：建议从 100 提升到 500 或 1000
            # 这样既能防住几万字的超大文本，又能容纳 URL 和 业务描述
            if len(v_str) < 1000:  
                context_items.append(f"{k}: {v_str}")
            else:
                # 可选：对于超长文本，截取前 100 个字符作为“摘要”放进去
                # 这样 LLM 至少知道有这个字段存在
                context_items.append(f"{k}: {v_str[:100]}... (content too long)")
        
        context_str = "\n".join(context_items) if context_items else "无可用上下文"

        # 构建参数列表字符串
        params_list = "\n".join([
            f"- {name}: {desc}" 
            for name, desc in base_param_descriptions.items()
        ])

        # === 构建 LLM Prompt ===
        prompt = f"""你是一个智能参数描述增强器。请根据以下信息，为每个参数生成增强版的中文描述。

    要求：
    - 输出必须是严格的 JSON 格式：{{ "参数名": "增强后的描述" }}
    - 在原始描述基础上，**自然融入所有可用的上下文信息**（如 tenant_id、activity_id 等）
    - 上下文信息用于帮助后续系统精准查询该参数值，请明确写出归属（例如：“属于租户xxxx 的活动 xxxx”）
    - 如果某个上下文与参数明显无关，可不强行加入
    - 描述要简洁、专业、可被自动化系统理解
    - **不要编造不存在的上下文**
    - **不要改变参数名**
    - 只输出 JSON，不要任何其他文字

    【可用上下文】
    {context_str}

    【待增强的参数及基础描述】
    {params_list}
    """

        # === 调用 LLM ===
        try:
            response = self.llm_client.generate(
                prompt=prompt,
                parse_json=True,
            )
            result = response


            # 保证输出 key 与输入一致（防止 LLM 改名）
            aligned_result = {}
            for param_name in base_param_descriptions:
                if param_name in result:
                    aligned_result[param_name] = str(result[param_name]).strip()
                else:
                    # 回退：用原始描述 + 上下文拼接（保守策略）
                    fallback_desc = base_param_descriptions[param_name]
                    if context_items:
                        fallback_desc += "，上下文：" + "；".join(context_items)
                    aligned_result[param_name] = fallback_desc

            return aligned_result

        except Exception as e:
            print(f"[WARN] LLM 增强失败，使用回退策略: {e}")
            # 全部回退到基础描述 + 上下文拼接
            fallback = {}
            context_suffix = "（上下文：" + "；".join(context_items) + "）" if context_items else ""
            for name, desc in base_param_descriptions.items():
                fallback[name] = desc + context_suffix
            return fallback



    def pre_fill_known_params_with_llm(
        self,
        base_param_descriptions: dict,
        current_context_str: str
    ) -> tuple[dict, dict]:
        """
        使用 LLM 从自由文本上下文中提取可识别的参数值。
        
        Args:
            base_param_descriptions: {"user_id": "用户ID", "tenant_id": "租户ID", ...}
            current_context_str: 任意上下文，如 "当前用户是 test_admin_001，属于租户 test_tenant_001"
        
        Returns:
            (filled_values, remaining_params)
        """
        if not base_param_descriptions:
            return {}, {}
        
        if not self.tree_manager or not self.llm_client:
            self.set_dependencies()

        # 构建参数说明
        params_info = "\n".join([
            f"- {name}: {desc}"
            for name, desc in base_param_descriptions.items()
        ])

        prompt = f"""你是一个参数值提取器。请从以下上下文中，尽可能提取出与目标参数匹配的具体值。

    要求：
    - 只提取明确提及或可合理推断的值；
    - 如果某个参数无法确定，不要猜测，直接跳过；
    - 输出必须是严格 JSON 格式：{{ "参数名": "提取的值" }}
    - 值必须是字符串；
    - 不要输出任何其他文字，包括解释、markdown、前缀。

    【目标参数定义】
    {params_info}

    【当前上下文】
    {current_context_str}
    """

        try:
            response = self.llm_client.generate(
                prompt=prompt,
                parse_json=True,
            )
            # text = response.output.text.strip()

            # 提取 JSON
            # json_match = re.search(r"\{.*\}", text, re.DOTALL)
            json_match = response
            if json_match:
                # extracted = json.loads(json_match.group(0))
                extracted = json_match  
                # 只保留合法参数名 + 字符串值
                filled = {}
                for k, v in extracted.items():
                    if k in base_param_descriptions and isinstance(v, str) and v.strip():
                        filled[k] = v.strip()
            else:
                filled = {}
        except Exception as e:
            print(f"[WARN] LLM 预填充失败，跳过: {e}")
            filled = {}

        # 分离已填充和剩余参数
        remaining = {
            k: v for k, v in base_param_descriptions.items()
            if k not in filled
        }

        return filled, remaining
    



    # ----------------------------------------------------------
    # 辅助功能
    # ----------------------------------------------------------

    def extract_context(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """保留原有基础提取逻辑"""
        base_ctx = {}
        fields = ['task_id', 'task_type', 'user_id', 'content', 'query', 'payload']
        for f in fields:
            if f in task_data:
                base_ctx[f] = task_data[f]
        return base_ctx

    def register_context_template(self, name: str, template: Dict) -> None:
        self.context_templates[name] = template

    def enrich_context_from_result(
        self, 
        msg: 'TaskMessage', 
        result: Any, 
        task_name: str = ""
    ) -> None:
        """
        从任务执行结果中富集上下文
        
        Args:
            msg: TaskMessage 对象，包含上下文信息
            result: 任务执行结果
            task_name: 任务名称（可选）
        """
        # 示例：从 result 中提取结构化字段
        if isinstance(result, dict):
            for key, value in result.items():
                # 自定义过滤逻辑：只保留基本类型和非空值
                if value is not None and isinstance(value, (str, int, float, bool, list, dict)):
                    # 生成安全键名，包含任务路径前缀
                    safe_key = f"{msg.task_path.replace('/', '_')}.{key}"
                    msg.enriched_context[safe_key] = value
        elif isinstance(result, (list, tuple)):
            # 处理列表结果，添加索引
            for i, item in enumerate(result[:10]):  # 最多取前10个元素
                if isinstance(item, dict):
                    for key, value in item.items():
                        if value is not None and isinstance(value, (str, int, float, bool)):
                            safe_key = f"{msg.task_path.replace('/', '_')}.item_{i}.{key}"
                            msg.enriched_context[safe_key] = value
        elif isinstance(result, (str, int, float, bool)):
            # 处理单个基本类型结果
            safe_key = f"{msg.task_path.replace('/', '_')}.result"
            msg.enriched_context[safe_key] = result

    def extract_params_for_capability(
        self, 
        capability: str, 
        enriched_context: Dict[str, Any], 
        global_context: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        为特定能力智能提取参数
        
        Args:
            capability: 能力名称
            enriched_context: 富上下文
            global_context: 全局上下文
            
        Returns:
            (可用参数, 缺失参数列表)
        """
        # 这里需要根据实际的 CAPABILITY_SPECS 进行实现
        # 示例实现：基于简单的参数映射
        spec = self._get_capability_spec(capability)
        if not spec:
            return {}, []
            
        params = {}
        missing = []

        for param_name, config in spec["parameters"].items():
            found = False

            # 1. 优先从 enriched_context 匹配（支持别名）
            for alias in [param_name] + config.get("aliases", []):
                if alias in enriched_context:
                    params[param_name] = enriched_context[alias]
                    found = True
                    break

            # 2. 尝试从 global_context 获取（如 user_id）
            if not found and param_name in global_context:
                params[param_name] = global_context[param_name]
                found = True

            # 3. 仍缺失？
            if not found:
                missing.append(param_name)

        return params, missing
    
    def _get_capability_spec(self, capability: str) -> Optional[Dict[str, Any]]:
        """
        获取能力的参数规格
        
        Args:
            capability: 能力名称
            
        Returns:
            能力规格字典，包含 parameters 字段
        """
        # 这里需要根据实际系统中的能力规格进行实现
        # 示例：返回一个简单的默认规格
        return {
            "parameters": {
                # 默认参数规格，实际系统中应该从配置或注册中心获取
                "query": {"aliases": ["q", "question", "prompt"]},
                "user_id": {"aliases": ["uid", "user"]},
                "tenant_id": {"aliases": ["tid", "tenant"]}
            }
        }