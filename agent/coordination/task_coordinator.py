# coordination/task_coordinator.py
from typing import List, Dict, Any,Tuple, Optional,Callable
import dashscope
from http import HTTPStatus
import networkx as nx
from change_orchestrator.decision_engine import IntelligentChangeEngine
from llm import QwenLLM


import logging
import heapq

# 配置日志
logger = logging.getLogger(__name__)

class TaskCoordinator:
    def __init__(self, registry):
        self.registry = registry
        self.change_engine = IntelligentChangeEngine() 


    from typing import List, Dict, Any, Optional

    def _select_best_actor(self, agent_id,context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        基于子节点的能力和当前上下文，调用 Qwen 选择最合适的子节点。
        
        Args:
            context (Dict[str, Any]): 当前任务上下文，用于辅助决策。
            
        Returns:
            Optional[Dict]: 被选中的子节点信息（包含 name、capability 等），若无可选节点则返回 None。
        """
        # 1. 获取子节点列表
        children_actors = self.registry.get_children_actors(agent_id)
        
        if not children_actors:
            return None

        # return "fission_activity"
        # 2. 构建子节点描述列表（仅保留 name 和 capability）
        actor_descriptions = []
        for actor in children_actors:
            meta = self.registry.get_agent_meta(actor)
            name = meta.get("name", "Unknown")
            capability = meta.get("capability", {})
            datascope = meta.get("datascope", {})
            actor_descriptions.append({
                "code": actor,
                "name": name,
                "capability": capability,
                "datascope": datascope
            })
            children_actors[actor]={
                "name": name, 
                "capability": capability,
                "datascope": datascope
            }

        # 3. 构造提示词（Prompt）给 Qwen
        prompt = self._build_selection_prompt(actor_descriptions, context)

        # 4. 调用 Qwen（假设你有一个 _llm 属性，支持 .chat(messages) 接口）
        response = self.call_qwen([
            {"role": "system", "content": "你是一个任务调度专家，负责根据子节点能力和当前任务上下文选择最合适的执行节点。"},
            {"role": "user", "content": prompt}
        ])

        selected_code = self._parse_selected_actor_name(response)

        # 5. 根据返回的 name 找到原始 actor
        for actor in children_actors:
            # if children_actors[actor].get("name") == selected_name:
            if actor == selected_code:
                return actor

        # 如果没匹配到，可选：返回第一个作为 fallback
        return children_actors[0] if children_actors else None


    def _build_selection_prompt(self, actors: List[Dict], context: Dict[str, Any]) -> str:
        """构建用于节点选择的提示词"""
        context_str = "\n".join(f"- {k}: {v}" for k, v in context.items())
        
        actors_str = "\n".join(
            f"节点代码：{a['code']}\n节点名称: {a['name']}\n能力描述: {a['capability']}\n数据描述: {a['datascope']}\n"
            for a in actors
        )
        
        prompt = (
            "当前任务上下文如下：\n"
            f"{context_str}\n\n"
            "以下是可用的子节点及其能力：\n"
            f"{actors_str}\n\n"
            "请根据任务上下文，从上述节点中选择最合适的一个节点来执行任务。\n"
            "仅返回节点代码，不要包含任何其他文字、解释或标点符号。"
        )
        return prompt


    def _parse_selected_actor_name(self, llm_output: str) -> str:
        """从大模型输出中提取节点名称（简单清洗）"""
        return llm_output.strip().split('\n')[0].strip()



    def plan_subtasks(self, parent_agent_id: str, context: Dict[str, Any]) -> List[Dict]:
        """
        使用 Neo4j 间接影响传播 + IntelligentChangeEngine 生成执行计划。
        parent_agent_id 实际对应节点的 'code' 字段（根据你的数据结构）
        """
        root_code = parent_agent_id  # 假设传入的是 code，如 "rules_system_create_active"

        # 可配置阈值（可从 config 或 context 读取）
        threshold = context.get("influence_threshold", 0.3)

        # 1. 构建影响子图（含间接影响，权重为乘积）使用Neo4j查询
        graph: nx.DiGraph = self._fetch_influenced_subgraph_from_neo4j(
            root_code=root_code,
            threshold=threshold,
            max_hops=5
        )

        if not graph.nodes:
            return [{"node_id": root_code, "intent_params": {}}]

        # 2. 主意图
        main_intent = context.get("main_intent", "执行任务")

        # 3. 调用决策引擎
        change_request = {
            "graph": graph,
            "main_node": root_code,
            "main_intent": main_intent
        }

        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(self.change_engine.run(change_request))
        finally:
            loop.close()

        strategy = result["strategy"]
        execution_order = strategy["dag_structure"]["execution_order"]
        intent_propagation = strategy.get("intent_propagation", {})

        # 4. 构建返回计划
        plan = []
        for node_code in execution_order:
            intent_params = intent_propagation.get(node_code, {})
            if not isinstance(intent_params, dict):
                intent_params = {"derived_intent": str(intent_params)}
            plan.append({
                "node_id": node_code,  # 注意：这里 node_id 实际是 code
                "intent_params": intent_params
            })

        return plan

    def _fetch_influenced_subgraph_from_neo4j(
        self,
        root_code: str,
        threshold: float = 0.3,
        max_hops: int = 5
    ) -> nx.DiGraph:
        query = """
        MATCH (start {code: $rootCode})
        CALL apoc.path.expandConfig(start, {
        relationshipFilter: 'SAME_LEVEL_DEMO1>',
        minLevel: 1,
        maxLevel: $maxHops,
        uniqueness: 'NODE_GLOBAL'
        }) YIELD path
        WITH path,
            reduce(acc = 1.0, r IN relationships(path) | acc * coalesce(r.weight, 0.0)) AS totalStrength
        WHERE totalStrength >= $threshold
        WITH nodes(path)[-1] AS target, totalStrength, path
        ORDER BY totalStrength DESC
        WITH target, head(collect({strength: totalStrength, path: path})) AS best
        RETURN
        best.path AS bestPath,
        best.strength AS totalStrength
        """
        graph = nx.DiGraph()

        # 先加入根节点
        root_node = self._fetch_node_by_code(root_code)
        if not root_node:
            raise ValueError(f"Root node {root_code} not found")
        graph.add_node(root_code, **root_node["properties"])

        with self.registry.driver.session() as session:
            results = session.run(query, 
                                rootCode=root_code, 
                                threshold=threshold, 
                                maxHops=max_hops)
            for record in results:
                path = record["bestPath"]          # 类型: neo4j.Path
                total_strength = record["totalStrength"]

                # 提取路径中的所有节点
                nodes = list(path.nodes)
                rels = list(path.relationships)

                # 添加路径上所有节点（避免重复）
                for node in nodes:
                    code = node.get("code")
                    if code and code not in graph:
                        graph.add_node(code, **dict(node))

                # 添加路径上所有边
                for rel in rels:
                    start_code = rel.start_node.get("code")
                    end_code = rel.end_node.get("code")
                    strength = rel.get("strength", 1.0)
                    if start_code and end_code:
                        graph.add_edge(start_code, end_code,
                                    weight=strength,
                                    raw_strength=strength)

        return graph
    

    def _query_dependency_graph(self, root_agent_id: str) -> nx.DiGraph:
        """
        从 Neo4j 查询依赖图（有向图，可能含环）
        假设节点 label 为 'Agent'，关系为 'DEPENDS_ON' 或 'AFFECTS'
        """
        graph = nx.DiGraph()
        
        # 示例 Cypher 查询：获取两跳内的依赖关系
        query = """
        MATCH (root:Agent {agent_id: $root_id})
        OPTIONAL MATCH path = (root)-[:DEPENDS_ON|AFFECTS*0..2]->(n:Agent)
        WITH collect(DISTINCT nodes(path)) AS all_nodes, collect(DISTINCT relationships(path)) AS all_rels
        UNWIND all_nodes AS node
        WITH DISTINCT node, all_rels
        UNWIND all_rels AS rel
        RETURN DISTINCT
            node.agent_id AS node_id,
            node.description AS description,
            startNode(rel).agent_id AS from_id,
            endNode(rel).agent_id AS to_id,
            type(rel) AS rel_type
        """
        
        with self.registry.driver.session() as session:
            records = session.run(query, root_id=root_agent_id)
            nodes_added = set()
            for record in records:
                # 添加节点
                node_id = record["node_id"]
                if node_id and node_id not in nodes_added:
                    graph.add_node(node_id, description=record.get("description", ""))
                    nodes_added.add(node_id)
                
                # 添加边
                from_id = record.get("from_id")
                to_id = record.get("to_id")
                if from_id and to_id and from_id != to_id:
                    graph.add_edge(from_id, to_id, type=record.get("rel_type", "AFFECTS"))

        # 确保根节点一定在图中
        if root_agent_id not in graph:
            graph.add_node(root_agent_id)

        return graph


    


    def _compute_influenced_subgraph(
        self,
        root_code: str,
        strength_threshold: float = 0.3,
        max_hops: int = 5,
        aggregate_fn: Callable[[float, float], float] = None
    ) -> nx.DiGraph:
        """
        计算受 root_code 影响的子图，支持自定义路径权重聚合方式。

        Args:
            root_code: 根节点 code
            strength_threshold: 影响阈值
            max_hops: 最大传播跳数
            aggregate_fn: 路径聚合函数，默认为乘积 (lambda cum, w: cum * w)
            可以加法: additive_fn = lambda cum, w: cum + w
            最小值：min_fn = lambda cum, w: min(cum, w)
            最大值：max_fn = lambda cum, w: max(cum, w)
            带衰减的乘积：decay_fn = lambda cum, w: cum * (w ** 0.5)
        Returns:
            nx.DiGraph: 影响子图
        """
        if aggregate_fn is None:
            # 默认：乘积模型（适用于概率/强度衰减）
            aggregate_fn = lambda cum, w: cum * w

        graph = nx.DiGraph()

        # 获取并添加根节点
        root_node = self._fetch_node_by_code(root_code)
        if not root_node:
            raise ValueError(f"Root node with code '{root_code}' not found")
        graph.add_node(root_code, **root_node["properties"])

        # 传播状态：node_code -> 最大累积影响强度（用于剪枝）
        best_strength: Dict[str, float] = {root_code: 1.0}

        # BFS 队列：(current_code, cumulative_strength, hop)
        from collections import deque
        queue = deque()
        queue.append((root_code, 1.0, 0))

        while queue:
            current_code, current_strength, hop = queue.popleft()

            if hop >= max_hops:
                continue

            # 获取直接下游影响
            direct_impacts = self._fetch_direct_impacts(current_code)

            for target_code, edge_strength in direct_impacts:
                # 使用传入的聚合函数计算新强度
                new_strength = aggregate_fn(current_strength, edge_strength)

                # 剪枝：低于阈值 或 已有更强路径
                if new_strength < strength_threshold:
                    continue

                # 只有当新路径更强时才更新（贪心保留最大影响）
                if target_code not in best_strength or new_strength > best_strength[target_code]:
                    best_strength[target_code] = new_strength

                    # 添加节点（若未存在）
                    if target_code not in graph:
                        target_node = self._fetch_node_by_code(target_code)
                        if target_node:
                            graph.add_node(target_code, **target_node["properties"])
                        else:
                            # 若节点不存在，仍可占位（或跳过）
                            graph.add_node(target_code)

                    # 更新边权重为当前累积强度（注意：这是从 root 到 target 的总影响）
                    graph.add_edge(current_code, target_code, weight=new_strength)

                    queue.append((target_code, new_strength, hop + 1))

        return graph


    def _fetch_node_by_code(self, code: str) -> Dict | None:
        query = """
        MATCH (n {code: $code})
        RETURN n
        LIMIT 1
        """
        with self.registry.driver.session() as session:
            result = session.run(query, code=code)
            record = result.single()
            if record:
                node = record["n"]
                return {
                    "identity": node.id,
                    "labels": list(node.labels),
                    "properties": dict(node),
                    "elementId": node.element_id
                }
        return None
    
    def _fetch_direct_impacts(self, source_code: str) -> List[Tuple[str, float]]:
        """
        返回 [(target_code, strength), ...]
        假设关系为 (source)-[:IMPACTS {strength: Float}]->(target)
        """
        query = """
        MATCH (src {code: $source_code})-[r:IMPACTS]->(tgt)
        WHERE r.strength IS NOT NULL
        RETURN tgt.code AS target_code, r.strength AS strength
        """
        impacts = []
        with self.registry.diver.session() as session:
            results = session.run(query, source_code=source_code)
            for record in results:
                tgt_code = record["target_code"]
                strength = record["strength"]
                if tgt_code and isinstance(strength, (int, float)) and 0 <= strength <= 1:
                    impacts.append((tgt_code, float(strength)))
        return impacts

    def resolve_context(self, ctx: Dict[str, str],agent_id) -> Dict[str, Any]:
        registry = self.registry
        current_agent_id = agent_id

        result = {}

        for key, value_desc in ctx.items():
            query = f"变量名: '{key}', 值描述: '{value_desc}'"
            leaf_meta = self._resolve_kv_via_layered_search(current_agent_id, query, key)
            if leaf_meta and key in leaf_meta.get("data_scope", {}):
                result[key] = leaf_meta["data_scope"][key]
            else:
                logger.warning(f"无法解析变量 '{key}' (描述: {value_desc})")
                result[key] = value_desc  # 或 None

        return result


    def _resolve_kv_via_layered_search(
        self,
        start_agent_id: str,
        query: str,
        key: str
    ) -> Optional[Dict]:
        """
        严格按以下规则：
        - 从 start_agent 所在层开始；
        - 每次只检查当前层；
        - 如果当前层有匹配节点：
            - 如果该节点是叶子 → 返回；
            - 否则 → 移动到它的 direct children 层（向下一层）；
        - 如果当前层无匹配：
            - 移动到父层（向上一层）；
        - 重复，直到：
            - 找到叶子 → 成功；
            - 向上超出根 → 失败；
        """
        # 初始化：当前层 = start_agent 的兄弟层（含自己）
        current_agent = start_agent_id
        visited_layers = set()  # 防止循环（理论上不会，但安全）

        while True:
            parent = self.registry.get_parent(current_agent)
            if parent is None:
                current_layer = [current_agent]  # 根层
            else:
                current_layer = self.registry.get_children(parent)  # 当前层所有节点

            layer_key = tuple(sorted(current_layer))
            if layer_key in visited_layers:
                break  # 防死循环
            visited_layers.add(layer_key)

            # 检查当前层是否有语义匹配的节点
            matched_node_id = None
            node_desc={}
            for node_id in current_layer:
                meta = self.registry.get_agent_meta(node_id)
                if not meta:
                    continue
                ds = meta.get("datascope", {})
                caps = meta.get("capability", [])
                # ds_text = "; ".join(f"'{k}': {v}" for k, v in ds.items()) or "无数据字段"
                ds_text = ds or "无数据字段"
                # cap_text = ", ".join(caps) if caps else "无能力声明"
                cap_text = caps if caps else "无能力声明"
                node_desc [node_id]= f"[节点 {node_id}] 数据: {ds_text}。能力: {cap_text}"
            
            if self._qwen_semantic_match_for_layer(query, node_desc):
                matched_node_id = node_id
                break  # 找到第一个匹配即可（或可选最佳）

            if matched_node_id is not None:
                # 有匹配！检查是否是叶子
                matched_meta = self.registry.get_agent_meta(matched_node_id)
                if matched_meta.get("is_leaf"):
                    # 叶子：检查是否包含 key（可选）
                    if key in matched_meta.get("data_scope", {}):
                        return matched_meta
                    else:
                        # 语义匹配但无该字段？视为不匹配，继续？按你说的：匹配即持有
                        # 这里保守处理：返回
                        return matched_meta

                else:
                    # 非叶子：向下一层（进入它的 direct children）
                    children = self.registry.get_children(matched_node_id)
                    if not children:
                        # 无子节点但又不是叶子？异常，退出
                        break
                    # 下一次循环检查它的子层
                    current_agent = children[0]  # 任选一个子节点来定位层
                    continue

            else:
                # 当前层无匹配：向上一层
                if parent is None:
                    # 已是根层，再向上就没了
                    break
                else:
                    # 移动到父层：让 current_agent = parent，下轮检查 parent 的兄弟层
                    current_agent = parent
                    continue

        return None


    def _find_matching_leaf_in_subtree(
        self,
        root_id: str,
        query: str,
        key: str
    ) -> Optional[Dict]:
        """
        从 root_id 开始 DFS，找 is_leaf=True 且 data_scope 包含 key 的节点。
        可再次用 Qwen 精筛，但为效率，优先检查 key 存在性。
        """
        stack = [root_id]
        visited = set()

        while stack:
            node_id = stack.pop()
            if node_id in visited:
                continue
            visited.add(node_id)

            meta = self.registry.get_agent_meta(node_id)
            if not meta:
                continue

            if meta.get("is_leaf"):
                ds = meta.get("data_scope", {})
                if key in ds:
                    # 可选：再用 Qwen 确认语义是否真的匹配（更严谨）
                    ds_desc = ds[key]
                    field_desc = f"字段 '{key}': {ds_desc}"
                    if self._qwen_semantic_match(query, field_desc):
                        return meta
                    # 否则继续找其他叶子（但通常一个 key 只在一个叶子定义）
            
            # 继续向下
            children = self.registry.get_children(node_id)
            stack.extend(children)

        return None


    def _qwen_semantic_match_for_layer(
        self,
        query: str,
        layer_nodes: List[Dict]
    ) -> Optional[str]:
        """
        使用 DashScope Qwen 判断当前层中哪个节点匹配 query。
        
        Args:
            query: 自然语言查询，如 "变量名: 'user_id', 值描述: '当前登录用户'"
            layer_nodes: 当前层节点列表，每个元素为 dict，包含:
                - "node_id": str
                - "data_scope": Dict[str, str]
                - "capabilities": List[str]
        
        Returns:
            匹配的 node_id (str)，若无匹配返回 None
        """
        if not layer_nodes:
            return None

        # 构造候选描述
        candidates_text = []
        node_id_list = []
        for meta in layer_nodes:
            # node_id = meta["code"]
            # ds = meta.get("data_scope", {})
            # caps = meta.get("capabilities", [])
            
            # ds_items = [f"'{k}': {v}" for k, v in ds.items()]
            # ds_str = "; ".join(ds_items) if ds_items else "无数据字段"
            # cap_str = ", ".join(caps) if caps else "无能力声明"
            
            # desc = f"候选 {node_id}: 数据范围 — {ds_str}；能力 — {cap_str}"
            desc = layer_nodes[meta]
            candidates_text.append(desc)
            node_id_list.append(meta)

        candidates_block = "\n".join(candidates_text)

        prompt = f"""你是一个数据路由语义匹配引擎。请根据以下数据需求，从候选数据节点中选择**最匹配的一个**。

    数据需求:
    {query}

    候选节点:
    {candidates_block}

    请严格按照以下规则回答：
    - 如果有匹配项，请只输出对应的 node_id（例如：C1）；
    - 如果没有一个候选能合理满足该需求，请只输出 "none"。
    - 不要解释，不要加标点，不要多余文字。
    """

        try:
            # response = dashscope.Generation.call(
            #     model="qwen-max",  # 或 qwen-plus / qwen-turbo（按需调整）
            #     messages=[{"role": "user", "content": prompt}],
            #     temperature=0.1,   # 降低随机性
            #     max_tokens=20,
            #     top_p=0.8
            # )
            response=self.call_qwen(prompt)
            # if response.status_code != 200:
            #     logger.error(f"DashScope API error: {response.code} - {response.message}")
            #     return None

            # answer = response.output.choices[0].message.content.strip()
            answer = response
            logger.debug(f"Qwen response for query '{query}': '{answer}'")

            if answer.lower() == "none":
                return None

            # 检查返回的是否是合法 node_id
            if answer in node_id_list:
                return answer
            else:
                # 可能模型返回了带引号或空格，尝试清理
                cleaned = answer.strip().strip('"').strip("'")
                if cleaned in node_id_list:
                    return cleaned
                else:
                    logger.warning(f"Qwen returned invalid node_id: '{answer}', not in {node_id_list}")
                    return None

        except Exception as e:
            logger.error(f"Exception calling DashScope: {e}")
            # 可选：降级到关键词匹配
            return self._fallback_keyword_match(query, layer_nodes)


    def _fallback_keyword_match(
        self,
        query: str,
        layer_nodes: List[Dict]
    ) -> Optional[str]:
        """简单关键词回退（仅用于 API 失败时）"""
        query_lower = query.lower()
        for meta in layer_nodes:
            ds = " ".join(meta.get("data_scope", {}).values()).lower()
            caps = " ".join(meta.get("capabilities", [])).lower()
            if any(kw in ds or kw in caps for kw in ["用户", "user", "id", "current"] if kw in query_lower):
                return meta["node_id"]
        return None

    def call_qwen(self,prompt: str) -> str:
        llm=QwenLLM()
        res=llm.generate(prompt)
        return res
        response = dashscope.Generation.call(
            model='qwen-max',
            messages=[{'role': 'user', 'content': prompt}],
            result_format='message',
            temperature=0.1,
            top_p=0.5,
            enable_json_output=False
        )
        if response.status_code == HTTPStatus.OK:
            return response.output.choices[0].message.content
        else:
            return ""
