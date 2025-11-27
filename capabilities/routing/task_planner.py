"""任务规划器实现"""
from typing import Dict, Any, List, Optional, Tuple
import networkx as nx
from ..capability_base import CapabilityBase
import logging
import uuid

import json


import logging
import json
import networkx as nx
from typing import Dict, Any, List, Tuple
from external.agent_structure.structure_interface import AgentStructureInterface


class TaskPlanner(CapabilityBase):
    """
    任务规划器
    负责将复杂任务分解为子任务序列，支持强耦合任务的协同规划。
    从TaskCoordinator.plan_subtasks迁移而来，并集成 Neo4j + SCC + Qwen 协同规划能力。
    """

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.registry = None
        self.graph = None
        self.change_engine = None
        self.qwen_client = None  # 需在 initialize 中设置
        self.task_templates = {
            'data_analysis': {
                'steps': [
                    {'name': '数据收集', 'task_type': 'data_collection'},
                    {'name': '数据清洗', 'task_type': 'data_cleaning'},
                    {'name': '数据分析', 'task_type': 'analysis'},
                    {'name': '结果生成', 'task_type': 'result_generation'}
                ]
            },
            'research': {
                'steps': [
                    {'name': '信息收集', 'task_type': 'information_gathering'},
                    {'name': '信息分析', 'task_type': 'analysis'},
                    {'name': '结论生成', 'task_type': 'conclusion'}
                ]
            }
        }

    def get_capability_type(self) -> str:
        return 'planning'

    def initialize(self, registry=None, graph=None, change_engine=None, qwen_client=None) -> bool:
        if not super().initialize():
            return False

        self.registry = registry
        self.graph = graph
        self.change_engine = change_engine
        self.qwen_client = qwen_client  # 新增 Qwen 客户端

        if not self.qwen_client:
            self.logger.warning("Qwen client not provided; will fallback to non-AI planning.")

        return True

    # ================================
    # 🔹 核心规划入口
    # ================================

    def plan_subtasks(self, parent_agent_id: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        规划子任务序列（主入口）
        若 Qwen 可用且上下文含 main_intent，则使用协同规划；
        否则回退到模板或简单分解。
        """
        if self.qwen_client and context.get("main_intent"):
            return self._plan_with_qwen_coordinated_scc(parent_agent_id, context)
        else:
            return self._fallback_plan_by_template_or_default(parent_agent_id, context)

    # ================================
    # 🔹 协同规划实现（SCC-based）
    # ================================

    def _fetch_subgraph_with_scc_from_neo4j(
        self,
        root_code: str,
        threshold: float = 0.3,
        max_hops: int = 5
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        从 AgentStructure 获取带 scc_id 的子图数据。
        要求底层实现（如 Neo4j + APOC）在节点中注入 'scc_id' 字段。

        Returns:
            (nodes_data, edges_data)
            - nodes_data: [{"node_id": "...", "properties": {...}}, ...]
            - edges_data: [{"from": "...", "to": "...", "weight": 0.x}, ...]
        """
        try:
            structure = AgentStructureInterface.get_instance()
            # 假设新接口方法返回结构化 dict 而非 nx.DiGraph
            result = structure.get_influenced_subgraph_with_scc(
                root_code=root_code,
                threshold=threshold,
                max_hops=max_hops
            )
            nodes = result.get("nodes", [])
            edges = result.get("edges", [])
            self.logger.debug(f"Fetched subgraph: {len(nodes)} nodes, {len(edges)} edges")
            return nodes, edges
        except Exception as e:
            self.logger.error(f"Failed to fetch SCC-aware subgraph from Neo4j: {e}")
            return [], []

    def _plan_with_qwen_coordinated_scc(
        self,
        parent_agent_id: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        root_code = parent_agent_id
        threshold = context.get("influence_threshold", 0.3)

        nodes_data, edges_data = self._fetch_subgraph_with_scc_from_neo4j(
            root_code=root_code,
            threshold=threshold,
            max_hops=5
        )

        if not nodes_data:
            return [{"node_id": root_code, "intent_params": {}}]

        # 按 scc_id 分组
        scc_groups: Dict[str, List[Dict]] = {}
        node_to_scc: Dict[str, str] = {}
        node_properties: Dict[str, Dict] = {}

        for node in nodes_data:
            node_id = node["node_id"]
            props = node["properties"]
            scc_id = props.get("scc_id", f"SCC_SINGLE_{node_id}")
            node_properties[node_id] = props
            node_to_scc[node_id] = scc_id
            scc_groups.setdefault(scc_id, []).append({
                "node_id": node_id,
                "properties": props
            })

        # 构建影响映射
        influence_map: Dict[str, List[Dict]] = {nid: [] for nid in node_properties}
        for edge in edges_data:
            u, v, w = edge["from"], edge["to"], edge.get("weight", 0.0)
            if u in influence_map:
                influence_map[u].append({"target": v, "strength": round(w, 3)})
            if v in influence_map:
                influence_map[v].append({"source": u, "strength": round(w, 3)})

        # 协同规划每个 SCC 组
        all_task_details = {}
        for scc_id, group_nodes in scc_groups.items():
            if len(group_nodes) == 1:
                node = group_nodes[0]
                detail = self._plan_single_node_with_qwen(node, context)
                all_task_details[node["node_id"]] = detail
            else:
                group_plan = self._qwen_plan_scc_group(
                    scc_id=scc_id,
                    nodes=group_nodes,
                    influence_map=influence_map,
                    main_intent=context.get("main_intent", "执行系统变更"),
                    execution_memory=context.get("execution_memory", {})
                )
                all_task_details.update(group_plan)

        # 全局排序（容忍环）
        dg = nx.DiGraph()
        for nid in node_properties:
            dg.add_node(nid)
        for e in edges_data:
            dg.add_edge(e["from"], e["to"])
        
        try:
            global_order = list(nx.topological_sort(dg))
        except nx.NetworkXUnfeasible:
            global_order = self._topo_sort_with_scc(dg, node_to_scc)

        # 按序组装
        result = []
        for node_id in global_order:
            if node_id in all_task_details:
                result.append({
                    "node_id": node_id,
                    "intent_params": all_task_details[node_id]
                })
        return result

    def _plan_single_node_with_qwen(self, node: Dict, context: Dict[str, Any]) -> Dict[str, Any]:
        """单节点简化规划（可扩展）"""
        if not self.qwen_client:
            return {"intent": f"执行 {node['node_id']}", "parameters": {}, "fallback": "跳过"}
        
        prompt = f"""
你是一个任务规划专家。请为以下独立任务生成执行细节。

任务ID: {node['node_id']}
属性: {json.dumps(node['properties'], ensure_ascii=False, indent=2)}
主意图: {context.get('main_intent', '执行系统变更')}

输出严格 JSON：
{{
  "intent": "简明意图",
  "parameters": {{}},
  "fallback": "降级策略"
}}
"""
        try:
            resp = self.qwen_client.call(
                model="qwen-max",
                prompt=prompt,
                temperature=0.2,
                max_tokens=500,
                result_format="json"
            )
            return json.loads(resp.output.text)
        except Exception as e:
            self.logger.warning(f"Single-node Qwen planning failed: {e}")
            return {"intent": f"执行 {node['node_id']}", "parameters": {}, "fallback": "跳过"}

    def _qwen_plan_scc_group(
        self,
        scc_id: str,
        nodes: List[Dict],
        influence_map: Dict[str, List[Dict]],
        main_intent: str,
        execution_memory: Dict[str, Any]
    ) -> Dict[str, Dict]:
        node_ids = [n["node_id"] for n in nodes]
        intra_influences = []
        for nid in node_ids:
            for inf in influence_map.get(nid, []):
                if inf.get("target") in node_ids or inf.get("source") in node_ids:
                    intra_influences.append(inf)

        memory_summary = ""
        if execution_memory:
            failures = execution_memory.get("failures", [])
            relevant = [f for f in failures if f.get("node") in node_ids]
            if relevant:
                memory_summary = "历史失败记录（本组内）:\n" + "\n".join(
                    f"- {f['node']}: {f['reason']}" for f in relevant[-3:]
                )

        prompt = f"""你是一个高级系统协调 AI，负责对一组**强耦合任务**进行协同规划。这些任务互相高度依赖，必须统一设计执行细节以确保一致性。

## 主意图
{main_intent}

## 强耦合组信息
- 组ID: {scc_id}
- 包含任务: {json.dumps(node_ids, ensure_ascii=False)}

## 任务属性
{json.dumps([{n['node_id']: n['properties']} for n in nodes], indent=2, ensure_ascii=False)}

## 组内相互影响关系
{json.dumps(intra_influences, indent=2, ensure_ascii=False)}

{memory_summary}

## 你的任务
1. 为组内每个任务生成执行细节，必须满足：
   - 所有共享参数（如阈值、格式、时间窗口）必须一致
   - 输出格式与输入期望必须匹配
   - 若存在策略冲突，优先服从主意图
2. 显式声明任何共享的全局约束

## 输出格式（严格 JSON）
{{
  "shared_constraints": {{
    "common_output_format": "json",
    "unified_threshold": 0.75,
    "sync_window_sec": 10
  }},
  "task_details": {{
    "TaskA": {{
      "intent": "激活规则并输出标准JSON",
      "parameters": {{
        "mode": "active",
        "output_format": "json",
        "threshold": 0.75
      }},
      "fallback": "降级为 dry_run"
    }}
  }}
}}
"""

        try:
            response = self.qwen_client.call(
                model="qwen-max",
                prompt=prompt,
                temperature=0.1,
                max_tokens=2000,
                result_format="json"
            )
            plan = json.loads(response.output.text)
            task_details = plan.get("task_details", {})
            shared = plan.get("shared_constraints", {})
            for tid in task_details:
                task_details[tid]["shared_constraints"] = shared
            return task_details
        except Exception as e:
            self.logger.error(f"Qwen SCC planning failed for {scc_id}: {e}")
            fallback = {}
            for node in nodes:
                fallback[node["node_id"]] = {
                    "intent": f"执行 {node['node_id']}",
                    "parameters": {},
                    "fallback": "跳过",
                    "shared_constraints": {}
                }
            return fallback

    def _topo_sort_with_scc(self, graph: nx.DiGraph, node_to_scc: Dict[str, str]) -> List[str]:
        """对含环图按 SCC 分层进行近似拓扑排序"""
        scc_graph = nx.DiGraph()
        scc_map = {}
        for idx, comp in enumerate(nx.strongly_connected_components(graph)):
            scc_id = f"COMP_{idx}"
            for node in comp:
                scc_map[node] = scc_id
            scc_graph.add_node(scc_id)

        for u, v in graph.edges():
            su, sv = scc_map[u], scc_map[v]
            if su != sv:
                scc_graph.add_edge(su, sv)

        try:
            scc_order = list(nx.topological_sort(scc_graph))
        except:
            scc_order = list(scc_graph.nodes)

        node_order = []
        reverse_map = {}
        for node, sid in scc_map.items():
            reverse_map.setdefault(sid, []).append(node)
        for sid in scc_order:
            node_order.extend(reverse_map.get(sid, []))
        return node_order

    # ================================
    # 🔹 回退机制
    # ================================

    def _fallback_plan_by_template_or_default(self, parent_agent_id: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        # 可根据 parent_agent_id 查模板，此处简化
        return [{"node_id": parent_agent_id, "intent_params": {}}]

    # ================================
    # 🔹 模板管理（保持不变）
    # ================================

    def register_task_template(self, template_name: str, template: Dict[str, Any]) -> bool:
        if 'steps' not in template or not isinstance(template['steps'], list):
            self.logger.error(f"Template must have 'steps' list")
            return False
        self.task_templates[template_name] = template
        self.logger.info(f"Registered task template: {template_name}")
        return True

    def get_task_templates(self) -> Dict[str, Dict[str, Any]]:
        return self.task_templates.copy()