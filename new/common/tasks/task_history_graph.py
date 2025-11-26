# services/task_history_graph.py
from typing import List, Optional, Dict
from .models.task_node import TaskNode

_NODES: Dict[str, TaskNode] = {}  # node_id → node
_ROOT_INDEX: Dict[str, List[str]] = {}  # task_root_id → [node_id...]

class TaskHistoryGraph:
    @staticmethod
    def create_root_node(user_id: str, initial_description: str, **kwargs) -> TaskNode:
        node = TaskNode(
            id=str(uuid.uuid4()),
            task_root_id=str(uuid.uuid4()),  # 新树
            parent_id=None,
            user_id=user_id,
            type=TaskNodeType.CREATED,
            timestamp=datetime.now(),
            description=initial_description,
            goal=kwargs.get("goal", initial_description),
            summary_for_llm=f"创建任务：{initial_description}",
            **kwargs
        )
        _NODES[node.id] = node
        _ROOT_INDEX[node.task_root_id] = [node.id]
        return node

    @staticmethod
    def append_child(parent_id: str, node_type: TaskNodeType, **kwargs) -> TaskNode:
        parent = _NODES[parent_id]
        node = TaskNode(
            id=str(uuid.uuid4()),
            task_root_id=parent.task_root_id,
            parent_id=parent_id,
            user_id=parent.user_id,
            type=node_type,
            timestamp=datetime.now(),
            # 继承父状态并覆盖变更
            goal=kwargs.get("goal", parent.goal),
            description=kwargs.get("description", ""),
            status=kwargs.get("status", parent.status),
            schedule_config=kwargs.get("schedule_config", parent.schedule_config),
            subtasks=kwargs.get("subtasks", parent.subtasks),
            execution_result=kwargs.get("execution_result"),
            comment=kwargs.get("comment"),
            corrected_result=kwargs.get("corrected_result"),
            summary_for_llm=kwargs.get("summary_for_llm", ""),
        )
        _NODES[node.id] = node
        _ROOT_INDEX[node.task_root_id].append(node.id)
        return node

    @staticmethod
    def get_tree(task_root_id: str) -> List[TaskNode]:
        """按时间顺序返回整棵树（扁平）"""
        ids = _ROOT_INDEX.get(task_root_id, [])
        return [_NODES[i] for i in ids if i in _NODES]

    @staticmethod
    def get_latest_node(task_root_id: str) -> Optional[TaskNode]:
        tree = TaskHistoryGraph.get_tree(task_root_id)
        return tree[-1] if tree else None

    # —————— 关键：语义化检索 ——————
    @staticmethod
    def find_best_matching_node(user_id: str, query: str, qwen_client) -> Optional[TaskNode]:
        """
        使用 LLM 从用户所有任务历史中选出最匹配的节点
        """
        # 1. 获取用户所有任务树的最新节点（缩小范围）
        candidate_nodes = []
        for node in _NODES.values():
            if node.user_id == user_id and node.type in {TaskNodeType.CREATED, TaskNodeType.MODIFIED, TaskNodeType.EXECUTED}:
                candidate_nodes.append(node)

        if not candidate_nodes:
            return None

        # 2. 构建候选列表（供 LLM 选择）
        options_text = "\n".join([
            f"选项{idx}: [ID={node.id[:8]}] {node.summary_for_llm} (时间: {node.timestamp.strftime('%Y-%m-%d %H:%M')})"
            for idx, node in enumerate(candidate_nodes)
        ])

        prompt = f"""
你是一个任务历史选择器。请根据用户查询，从以下候选任务历史中选择最匹配的一项。

用户查询：
{query}

候选任务（每项包含简要摘要和时间）：
{options_text}

要求：
- 如果有明确匹配，输出对应选项编号（如 "0"）
- 如果都不匹配，输出 "none"
- 只输出数字或 "none"，不要解释

你的选择：
"""
        try:
            resp = qwen_client.generate(prompt, max_tokens=10, temperature=0.0).strip()
            if resp.isdigit():
                idx = int(resp)
                if 0 <= idx < len(candidate_nodes):
                    return candidate_nodes[idx]
            return None
        except:
            # fallback: 返回最新节点
            return max(candidate_nodes, key=lambda x: x.timestamp)