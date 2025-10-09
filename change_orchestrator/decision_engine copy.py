# decision_engine.py
import hashlib
import json
import uuid
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

import networkx as nx
from langchain.prompts import PromptTemplate
from langchain_community.llms import Tongyi  # ✅ 修正：使用 Tongyi 而非 Qwen
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

import faiss
import numpy as np

# 假设你封装的图嵌入工具（需自行实现或替换）
# from graphbrain import node2vec_embedding  # 示例占位符
def node2vec_embedding(graph: nx.DiGraph) -> np.ndarray:
    """临时占位：返回随机向量，实际应替换为真实图嵌入"""
    dim = 64
    return np.random.randn(dim).astype(np.float32)


@dataclass
class ChangePattern:
    graph_hash: str
    graph_structure: Dict
    vector: np.ndarray
    coordination_strategy: Dict
    metadata: Dict


class IntelligentChangeEngine:
    """
    智能变更决策引擎
    支持：思维链推理、自我一致性、图缓存、案例检索
    """

    def __init__(self, llm, vector_dim=64):
        self.llm = llm
        self.pattern_kb: Dict[str, ChangePattern] = {}  # 哈希 → 案例
        self.vector_index = faiss.IndexFlatL2(vector_dim)  # 向量索引
        self.vectors: List[np.ndarray] = []
        self.hash_to_idx: Dict[str, int] = {}
        self.graph_cache: Dict[str, nx.DiGraph] = {}
        self.step_chains = self._build_step_chains()  # ✅ 替换为 LCEL 链

    def _build_step_chains(self):
        """构建分步推理链（LCEL 方式）"""
        parser = StrOutputParser()
        return {
            "step1": (
                PromptTemplate.from_template(
                    "Step 1: 分析变更源头 '{main_flow}' 及其直接依赖。\n"
                    "输入参数依赖: {inputs}\n"
                    "输出影响: {outputs}\n"
                    "请列出所有直接受影响的模块及其依赖关系。"
                )
                | self.llm
                | parser
            ),
            "step2": (
                PromptTemplate.from_template(
                    "Step 2: 识别关键瓶颈路径（如最长延迟链）。\n"
                    "当前依赖图: {graph_desc}\n"
                    "请指出哪条路径最可能成为性能/稳定性瓶颈，并解释原因。"
                )
                | self.llm
                | parser
            ),
            "step3": (
                PromptTemplate.from_template(
                    "Step 3: 检查是否存在循环依赖或资源竞争。\n"
                    "图结构: {edges}\n"
                    "请判断是否存在环路或并发冲突，若有，请指出。"
                )
                | self.llm
                | parser
            ),
            "step4": (
                PromptTemplate.from_template(
                    "Step 4: 对每个受影响模块提出参数调整建议。\n"
                    "模块: {modules}\n"
                    "当前配置: {configs}\n"
                    "请为每个模块建议合理的参数调整（如超时、重试、并发数）。"
                )
                | self.llm
                | parser
            ),
            "step5": (
                PromptTemplate.from_template(
                    "Step 5: 验证整体是否满足稳定性约束。\n"
                    "系统要求: {constraints}\n"
                    "当前方案: {proposed}\n"
                    "请评估风险并提出改进建议。"
                )
                | self.llm
                | parser
            ),
            "step6": (
                PromptTemplate.from_template(
                    "Step 6: 综合以上分析，输出最终协调方案。\n"
                    "请以 JSON 格式输出：{ 'execution_order': [...], 'parallel_groups': [...], 'param_adjustments': { ... } }"
                )
                | self.llm
                | parser
            ),
        }

    def _graph_to_hash(self, graph: nx.DiGraph) -> str:
        """对图结构做标准化哈希"""
        nodes = sorted(graph.nodes)
        edges = sorted((u, v) for u, v in graph.edges)
        data = json.dumps({"nodes": nodes, "edges": edges}, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()

    def _build_influence_graph(self, req: Dict) -> nx.DiGraph:
        """构建影响图（可增量更新）"""
        G = nx.DiGraph()

        main = req["main_affected_flow"]
        G.add_node(main, type="root", impact=1.0)

        interfaces = req["flow_interfaces"]
        for item in req["impacted_flows"]:
            flow = item["flow"]
            impact = item["impact_strength"]
            G.add_node(flow, impact=impact)
            # 添加 I/O 依赖边
            if flow in interfaces:
                inputs = interfaces[flow].get("inputs", [])
                for inp in inputs:
                    source_flow = self._infer_source_flow(inp, req)
                    if source_flow and source_flow in G:
                        G.add_edge(source_flow, flow, type="data_dependency")

        return G

    def _infer_source_flow(self, param: str, req: Dict) -> str:
        """根据参数名反推来源流程（可增强为正则或元数据）"""
        for flow_name, iface in req["flow_interfaces"].items():
            if param in iface.get("outputs", []):
                return flow_name
        return None

    def _get_or_create_vector(self, graph: nx.DiGraph) -> np.ndarray:
        """生成图嵌入向量（简化版：Node2Vec）"""
        # 实际可用 node2vec、Graph2Vec 等
        return node2vec_embedding(graph)  # 返回 shape=(dim,)

    def _retrieve_similar_case(self, graph: nx.DiGraph, threshold=0.9) -> ChangePattern:
        """向量检索最相似的历史案例"""
        vec = self._get_or_create_vector(graph).reshape(1, -1)
        if self.vector_index.ntotal == 0:
            return None

        dists, indices = self.vector_index.search(vec, k=1)
        if dists[0][0] < (1 - threshold):  # 距离越小越相似
            idx = indices[0][0]
            for h, i in self.hash_to_idx.items():
                if i == idx:
                    return self.pattern_kb[h]
        return None

    async def _run_cot_reasoning(self, req: Dict, graph: nx.DiGraph) -> List[Dict]:
        """运行多路径思维链推理（Self-Consistency）"""
        candidates = []
        for _ in range(3):  # 3 条独立推理路径
            strategy = {}
            for step_name, chain in self.step_chains.items():
                input_data = self._build_step_input(step_name, req, graph, strategy)
                output = await chain.ainvoke(input_data)  # ✅ 支持异步调用
                # 解析 step6 的最终输出
                if step_name == "step6":
                    strategy = self._parse_json(output)
            candidates.append(strategy)
        return candidates

    def _build_step_input(self, step: str, req: Dict, graph: nx.DiGraph, strategy: Dict) -> Dict:
        """构建每一步的输入"""
        if step == "step1":
            iface = req["flow_interfaces"].get(req["main_affected_flow"], {})
            return {
                "main_flow": req["main_affected_flow"],
                "inputs": ", ".join(iface.get("inputs", [])),
                "outputs": ", ".join(iface.get("outputs", []))
            }
        elif step == "step2":
            return {"graph_desc": str([(u, v) for u, v in graph.edges])}
        elif step == "step3":
            return {"edges": str([(u, v) for u, v in graph.edges])}
        elif step == "step4":
            return {
                "modules": ", ".join(graph.nodes),
                "configs": json.dumps({n: "default" for n in graph.nodes})
            }
        elif step == "step5":
            return {
                "constraints": "低延迟、无死锁、高可用",
                "proposed": json.dumps(strategy)
            }
        elif step == "step6":
            return {"proposed": json.dumps(strategy)}
        return {}

    def _parse_json(self, text: str) -> Dict:
        import re
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
        return {}

    def _self_consensus(self, candidates: List[Dict]) -> Dict:
        """自我一致性：取出现次数最多的字段组合（简化版）"""
        from collections import Counter
        orders = tuple(sorted(c.get("execution_order", [])) for c in candidates)
        best_order = Counter(orders).most_common(1)[0][0]

        # 合并参数调整
        param_adj = {}
        for c in candidates:
            for k, v in c.get("param_adjustments", {}).items():
                param_adj.setdefault(k, []).append(v)
        final_param = {k: max(v, key=v.count) for k, v in param_adj.items()}  # 投票取众数

        return {
            "execution_order": list(best_order),
            "parallel_groups": [],  # 可进一步分析
            "param_adjustments": final_param
        }

    async def run(self, change_request: Dict) -> Dict:
        """主入口（异步）"""
        # Step 1: 构建影响子图
        G = self._build_influence_graph(change_request)
        graph_hash = self._graph_to_hash(G)

        # Step 2: 检查缓存 & 向量检索
        cached_case = self._retrieve_similar_case(G)
        if cached_case and cached_case.graph_hash == graph_hash:
            print(f"🔁 命中完全匹配缓存: {graph_hash[:8]}")
            return {
                "change_id": str(uuid.uuid4()),
                "strategy": cached_case.coordination_strategy,
                "source": "cache_exact",
                "graph_hash": graph_hash
            }

        if cached_case:
            print(f"🎯 命中相似案例: {cached_case.graph_hash[:8]}，进行微调")
            return {
                "change_id": str(uuid.uuid4()),
                "strategy": cached_case.coordination_strategy,
                "source": "cache_similar",
                "graph_hash": graph_hash
            }

        # Step 3: 启动多路径推理
        print("🧠 启动多路径思维链推理...")
        candidates = await self._run_cot_reasoning(change_request, G)
        final_strategy = self._self_consensus(candidates)

        # Step 4: 缓存新结果
        vector = self._get_or_create_vector(G)
        idx = len(self.vectors)
        self.vector_index.add(vector.reshape(1, -1))
        self.vectors.append(vector)
        self.hash_to_idx[graph_hash] = idx

        self.pattern_kb[graph_hash] = ChangePattern(
            graph_hash=graph_hash,
            graph_structure={},
            vector=vector,
            coordination_strategy=final_strategy,
            metadata={"request_intent": change_request["proposed_change"]["intent"]}
        )

        return {
            "change_id": str(uuid.uuid4()),
            "strategy": final_strategy,
            "source": "llm_reasoning",
            "graph_hash": graph_hash,
            "candidate_count": len(candidates)
        }