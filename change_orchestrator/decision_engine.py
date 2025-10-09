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

# import faiss
import numpy as np


import asyncio
from collections import Counter, defaultdict
import traceback

# 假设你封装的图嵌入工具（需自行实现或替换）
# from graphbrain import node2vec_embedding  # 示例占位符
# def node2vec_embedding(graph: nx.DiGraph) -> np.ndarray:
#     """临时占位：返回随机向量，实际应替换为真实图嵌入"""
#     dim = 64
#     return np.random.randn(dim).astype(np.float32)


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
        if not llm:
            llm = Tongyi(model_name="qwen-max")
        else:
            self.llm = llm
        
        self.pattern_kb: Dict[str, ChangePattern] = {}  # 哈希 → 案例
        # self.vector_index = faiss.IndexFlatL2(vector_dim)  # 向量索引
        self.vectors: List[np.ndarray] = []
        self.hash_to_idx: Dict[str, int] = {}
        self.graph_cache: Dict[str, nx.DiGraph] = {}
        # self.step_chains = self._build_step_chains()  # ✅ 替换为 LCEL 链

    def _parse_json_output(self, text: str) -> Dict:
        """鲁棒性 JSON 解析"""
        import re
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if not match:
            return self._get_fallback_output()

        try:
            parsed = json.loads(match.group())
            # 确保结构完整
            parsed.setdefault("intent_propagation", {})
            parsed.setdefault("dag_structure", {
                "execution_order": [],
                "parallel_groups": []
            })
            parsed.setdefault("resolution_notes", "No resolution notes provided.")
            return parsed
        except json.JSONDecodeError:
            return self._get_fallback_output()
        
    async def _generate_with_cot_self_consistency(
        self,
        main_node: str,
        main_intent: str,
        graph_desc: str,
        num_samples: int = 3,  # 自我一致性采样数
        max_retries: int = 2   # 验证失败后最大重试次数
    ) -> Dict:
        """
        使用思维链 + 自我一致性 + 验证反馈 生成最终策略
        """

        # Step 0: 构建分步思维链提示模板（CoT）
        cot_prompt = PromptTemplate.from_template(
            """你是一个严谨的系统架构师。请按以下步骤逐步推理：

【STEP 1: 识别循环依赖】
请列出图中存在的所有循环依赖路径（如 A→B→A），并说明每条环的业务含义。
当前图：
{graph_desc}

【STEP 2: 解环策略设计】
针对每个环，提出具体的解环方案（如：边反转、引入中间状态、拆分阶段、异步化、添加缓冲等）。
请说明选择该方案的业务合理性。

【STEP 3: 意图传播推导】
基于主节点 '{main_node}' 的主意图：'{main_intent}'，为每个节点推导“修改意图”。
- 主节点是否需要追加附加意图？为什么？
- 其他节点的派生意图是什么？如何支持主目标？

【STEP 4: 构建执行DAG】
基于解环后的结构，输出：
- execution_order: 拓扑序（必须无环）
- parallel_groups: 可并行执行组
请确保 execution_order 中的顺序能支持所有依赖。

【STEP 5: 自我检查】
检查你的方案：
- 是否所有环都已解开？
- execution_order 是否合法拓扑序？
- 意图是否覆盖所有节点？
- 是否有遗漏或矛盾？

最后，输出严格 JSON 格式：
{{
  "intent_propagation": {{...}},
  "dag_structure": {{...}},
  "resolution_notes": "..."
}}
"""
        )

        chain = cot_prompt | self.llm | StrOutputParser()

        for retry in range(max_retries + 1):
            print(f"🔁 第 {retry + 1} 轮推理（含 {num_samples} 个并行样本）...")

            # 并行生成多个推理路径（Self-Consistency）
            tasks = [
                chain.ainvoke({
                    "main_node": main_node,
                    "main_intent": main_intent,
                    "graph_desc": graph_desc
                })
                for _ in range(num_samples)
            ]
            raw_outputs = await asyncio.gather(*tasks, return_exceptions=True)

            # 解析 & 验证每个样本
            candidates = []
            for i, output in enumerate(raw_outputs):
                if isinstance(output, Exception):
                    print(f"⚠️  样本 {i+1} 执行出错: {str(output)}")
                    continue

                parsed = self._parse_json_output(output)
                is_valid, error_msg = self._validate_strategy(parsed)
                if is_valid:
                    candidates.append(parsed)
                    print(f"✅ 样本 {i+1} 验证通过")
                else:
                    print(f"❌ 样本 {i+1} 验证失败: {error_msg}")

            if not candidates:
                if retry < max_retries:
                    # 所有样本都失败 → 生成反馈，引导下一轮
                    feedback = "所有候选方案均未通过验证。常见错误：" + "; ".join(
                        set(str(e) for e in raw_outputs if isinstance(e, Exception)) |
                        set("结构非法" for _ in range(len(raw_outputs) - len(candidates)))
                    )
                    graph_desc = self._enhance_graph_desc_with_feedback(graph_desc, feedback)
                    print(f"🔄 进入下一轮重试，已注入反馈: {feedback[:100]}...")
                    await asyncio.sleep(1)  # 避免 QPM 超限
                else:
                    print("🔥 达到最大重试次数，返回降级方案")
                    return self._get_fallback_output()
            else:
                # Self-Consistency: 对关键字段投票取共识
                consensus_strategy = self._extract_consensus(candidates)
                print(f"🎯 {len(candidates)} 个有效样本，已生成共识方案")
                return consensus_strategy

        return self._get_fallback_output()  # 理论上不会执行到这里

    def _validate_strategy(self, strategy: Dict) -> Tuple[bool, str]:
        """验证生成的策略是否合法（核心：execution_order 必须是合法拓扑序）"""
        try:
            order = strategy.get("dag_structure", {}).get("execution_order", [])
            if not order:
                return False, "execution_order 为空"

            # 检查是否有重复节点
            if len(order) != len(set(order)):
                return False, "execution_order 包含重复节点"

            # 构建有向图检查是否有环（基于顺序隐含的依赖）
            # 注意：我们不重建原始图，而是检查输出顺序是否自洽（无环）
            G_test = nx.DiGraph()
            G_test.add_nodes_from(order)
            # 假设顺序中靠前的节点应依赖靠后的？不，我们检查顺序本身是否形成环（不可能，因为是列表）
            # 更合理的验证：检查 parallel_groups 是否与 execution_order 一致
            groups = strategy.get("dag_structure", {}).get("parallel_groups", [])
            flat_groups = [item for group in groups for item in group]
            if set(flat_groups) != set(order):
                return False, "parallel_groups 与 execution_order 节点不一致"

            # 最强验证：模拟调度，检查组内无依赖（理想情况需要原始依赖图，这里简化）
            # 由于我们没有原始依赖边用于验证，此处仅做基础结构检查
            # 未来可传入原始图用于更严格验证

            return True, "OK"
        except Exception as e:
            return False, f"验证异常: {str(e)}"

    def _enhance_graph_desc_with_feedback(self, graph_desc: str, feedback: str) -> str:
        """在图描述后追加失败反馈，引导LLM修正"""
        return f"""{graph_desc}

⚠️【重要反馈】
上一轮生成的方案存在以下问题，请务必修正：
{feedback}

请重新思考解环策略和执行顺序，确保输出的 execution_order 是严格无环的拓扑序列。
"""

    def _extract_consensus(self, candidates: List[Dict]) -> Dict:
        """从多个候选方案中提取共识（简单投票机制）"""
        if len(candidates) == 1:
            return candidates[0]

        # 对 execution_order 进行投票（最核心字段）
        all_orders = [tuple(cand["dag_structure"]["execution_order"]) for cand in candidates if "dag_structure" in cand]
        if all_orders:
            order_counter = Counter(all_orders)
            consensus_order = order_counter.most_common(1)[0][0]
        else:
            consensus_order = candidates[0]["dag_structure"]["execution_order"]

        # 对 parallel_groups 投票（转为 frozenset(tuple) 以便哈希）
        all_groups = []
        for cand in candidates:
            groups = cand.get("dag_structure", {}).get("parallel_groups", [])
            # 标准化：组内排序 + 组间排序
            normalized = tuple(sorted(tuple(sorted(group)) for group in groups))
            all_groups.append(normalized)
        
        if all_groups:
            group_counter = Counter(all_groups)
            consensus_groups_tuple = group_counter.most_common(1)[0][0]
            consensus_groups = [list(group) for group in consensus_groups_tuple]
        else:
            consensus_groups = candidates[0]["dag_structure"]["parallel_groups"]

        # intent_propagation: 合并所有节点的意图（取第一个非空，或拼接）
        consensus_intents = {}
        node_intent_votes = defaultdict(list)
        
        for cand in candidates:
            intents = cand.get("intent_propagation", {})
            for node, intent_data in intents.items():
                node_intent_votes[node].append(intent_data)
        
        for node, votes in node_intent_votes.items():
            # 取第一个，或合并 derived_intent
            first = votes[0]
            if "derived_intent" in first:
                # 合并不同版本的派生意图（去重）
                all_derived = list(set(v.get("derived_intent", "") for v in votes if v.get("derived_intent")))
                consensus_intents[node] = {
                    "derived_intent": " | ".join(all_derived) if len(all_derived) > 1 else all_derived[0]
                }
            elif "primary_intent" in first:
                # 主节点：合并附加意图
                primary = first.get("primary_intent", "")
                all_additional = list(set(
                    a for v in votes for a in v.get("additional_intents", [])
                ))
                consensus_intents[node] = {
                    "primary_intent": primary,
                    "additional_intents": all_additional
                }

        # resolution_notes: 取最长的或拼接
        all_notes = [cand.get("resolution_notes", "") for cand in candidates]
        consensus_notes = " | ".join(set(all_notes)) if len(set(all_notes)) > 1 else all_notes[0]

        return {
            "intent_propagation": consensus_intents,
            "dag_structure": {
                "execution_order": list(consensus_order),
                "parallel_groups": consensus_groups
            },
            "resolution_notes": consensus_notes
        }


    def _get_fallback_output(self) -> Dict:
        return {
            "intent_propagation": {},
            "dag_structure": {
                "execution_order": [],
                "parallel_groups": []
            },
            "resolution_notes": "LLM 输出解析失败，需人工介入。"
        }
    

    def _format_graph_for_llm(self, graph: nx.DiGraph, main_node: str) -> str:
        """格式化图结构，突出主节点和权重"""
        lines = [f"主变更节点: {main_node}"]
        lines.append("\n受影响节点（按影响权重排序）:")
        sorted_nodes = sorted(graph.nodes, key=lambda n: graph.nodes[n].get("impact_strength", 0), reverse=True)
        for node in sorted_nodes:
            impact = graph.nodes[node].get("impact_strength", 0.0)
            mark = " <<< 主节点" if node == main_node else ""
            lines.append(f"- {node} (权重: {impact:.2f}){mark}")

        lines.append("\n依赖关系（可能存在循环）:")
        for u, v in graph.edges:
            edge_type = graph.edges[u, v].get("type", "affects")
            lines.append(f"  {u} --[{edge_type}]--> {v}")
        return "\n".join(lines)
    async def run(self, change_request: Dict) -> Dict:
        graph = change_request["graph"]
        main_node = change_request["main_node"]
        main_intent = change_request["main_intent"]
        # graph_hash = self._graph_to_hash(graph, main_node, main_intent)

        # 缓存检查（不变）
        # cached = self._retrieve_similar_case(graph_hash)
        # if cached:
        #     return {
        #         "change_id": str(uuid.uuid4()),
        #         "strategy": cached.coordination_strategy,
        #         "source": "cache",
        #         "graph_hash": graph_hash
        #     }

        # 🆕 调用新推理引擎
        print(f"🧠【CoT + Self-Consistency】基于主意图 '{main_intent}' 生成协调方案...")
        graph_desc = self._format_graph_for_llm(graph, main_node)
        
        # 🚀 核心替换：使用新方法
        strategy = await self._generate_with_cot_self_consistency(
            main_node=main_node,
            main_intent=main_intent,
            graph_desc=graph_desc,
            num_samples=3,      # 可配置
            max_retries=2       # 可配置
        )

        # # 缓存（不变）
        # vector = self._get_or_create_vector(graph)
        # idx = len(self.vectors)
        # self.vector_index.add(vector.reshape(1, -1))
        # self.vectors.append(vector)
        # self.hash_to_idx[graph_hash] = idx

        # self.pattern_kb[graph_hash] = ChangePattern(
        #     graph_hash=graph_hash,
        #     coordination_strategy=strategy,
        #     metadata={
        #         "main_node": main_node,
        #         "main_intent": main_intent,
        #     }
        # )

        return {
            "change_id": str(uuid.uuid4()),
            "strategy": strategy,
            "source": "llm_reasoning_cot_sc",  # 更新来源标记
            # "graph_hash": graph_hash
        }