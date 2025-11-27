# causal.py
import networkx as nx
from sklearn.preprocessing import KBinsDiscretizer
import numpy as np
from typing import List

def run_pc_algorithm(data: np.ndarray, alpha=0.05) -> nx.Graph:
    """运行 PC 算法得到无向骨架
    data: (n_samples, n_vars)
    """
    from sklearn.feature_selection import mutual_info_regression
    G = nx.Graph()
    n_vars = data.shape[1]
    G.add_nodes_from(range(n_vars))
    
    # 简化：用互信息 > 阈值作为边
    for i in range(n_vars):
        for j in range(i+1, n_vars):
            mi = mutual_info_regression(data[:, i:i+1], data[:, j])[0]
            if mi > 0.1:
                G.add_edge(i, j)
    return G

# 模拟 LLM 判断因果方向
def llm_causal_direction(var1: str, var2: str) -> str:
    """模拟：返回 'A->B', 'B->A', or 'none'"""
    # 实际可调用 Qwen API
    # from qwen import Qwen
    # resp = Qwen().chat(f"Which causes which: '{var1}' or '{var2}'? Answer only 'A' or 'B'.")
    # return 'A->B' if resp == 'A' else 'B->A'
    
    # 模拟逻辑：假设 "Sprinkler" → "WetGround", "Rain" → "WetGround"
    if var1 == "SprinklerOn(X)" and var2 == "WetGround(X)":
        return "A->B"
    elif var1 == "Rains(X)" and var2 == "WetGround(X)":
        return "A->B"
    else:
        return "none"

def orient_edges(skeleton: nx.Graph, variables: List[str]) -> nx.DiGraph:
    """使用 LLM 启发式定向"""
    DG = nx.DiGraph()
    DG.add_nodes_from(skeleton.nodes)
    for u, v in skeleton.edges:
        dir = llm_causal_direction(variables[u], variables[v])
        if dir == "A->B":
            DG.add_edge(u, v)
        elif dir == "B->A":
            DG.add_edge(v, u)
    return DG