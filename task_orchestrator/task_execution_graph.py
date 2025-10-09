import asyncio

from task_orchestrator.context import current_task_id,current_frame_id
 # 假设 orchestrator 管理 graphs 和 futures
from task_orchestrator.task_frame import TaskFrame
from typing import Dict, Optional, Any,List

class TaskExecutionGraph:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.frames: Dict[str, TaskFrame] = {}  # frame_id → frame
        self.root_frame_ids: List[str] = []     # 👈 改为列表！支持多个根帧

    def add_frame(self, frame: TaskFrame):
        self.frames[frame.frame_id] = frame
        if frame.parent_frame_id is None:
            # 这是一个新的根帧
            self.root_frame_ids.append(frame.frame_id)
        else:
            # 添加为子帧
            if frame.parent_frame_id not in self.frames:
                raise ValueError(f"Parent frame {frame.parent_frame_id} not found")
            parent = self.frames[frame.parent_frame_id]
            parent.sub_frames.append(frame.frame_id)

    def get_frame(self, frame_id: str) -> TaskFrame:
        return self.frames[frame_id]

    def is_all_roots_done(self) -> bool:
        """判断所有根帧（及其子树）是否都已完成或失败"""
        if not self.root_frame_ids:
            return False  # 还没创建任何帧
        return all(
            self._is_frame_tree_done(rid)
            for rid in self.root_frame_ids
        )

    def _is_frame_tree_done(self, frame_id: str) -> bool:
        """递归判断一个帧及其所有子孙是否都完成"""
        frame = self.frames[frame_id]
        if frame.status not in ("completed", "failed"):
            return False
        # 递归检查所有子帧
        return all(
            self._is_frame_tree_done(child_id)
            for child_id in frame.sub_frames
        )

    def are_all_children_done(self, frame_id: str) -> bool:
        """判断某个帧的直接子帧是否都完成了（用于聚合）"""
        frame = self.frames[frame_id]
        if not frame.sub_frames:
            return True
        return all(
            self.frames[child_id].status in ("completed", "failed")
            for child_id in frame.sub_frames
        )
    
    def _frame_to_dict(self, frame_id: str) -> Dict[str, Any]:
        """将单个帧转为可读字典（不含子帧）"""
        f = self.frames[frame_id]
        return {
            "frame_id": f.frame_id,
            "caller_agent_id": f.caller_agent_id,
            "target_agent_id": f.target_agent_id,
            "capability": f.capability,
            "status": f.status,
            "parent_frame_id": f.parent_frame_id,
            "sub_frames": []  # 子帧将在递归中填充
        }

    def _build_subtree(self, frame_id: str) -> Dict[str, Any]:
        """递归构建以 frame_id 为根的子树"""
        node = self._frame_to_dict(frame_id)
        for child_id in self.frames[frame_id].sub_frames:
            node["sub_frames"].append(self._build_subtree(child_id))
        return node

    def get_all_call_chains(self) -> List[Dict[str, Any]]:
        """
        返回该 task 下所有调用链的树形结构。
        每个调用链是一个从根帧开始的树。
        """
        chains = []
        for root_id in self.root_frame_ids:
            chains.append(self._build_subtree(root_id))
        return chains
    
    def print_call_chains(self):
        """在控制台打印所有调用链（缩进树形）"""
        def _print_node(node: Dict[str, Any], indent: int = 0):
            prefix = "  " * indent
            print(f"{prefix}→ {node['target_agent_id']} "
                f"({node['capability']}) [{node['status']}] "
                f"frame={node['frame_id']}")
            for child in node["sub_frames"]:
                _print_node(child, indent + 1)

        if not self.root_frame_ids:
            print("No call chains yet.")
            return

        for i, chain in enumerate(self.get_all_call_chains()):
            print(f"\n--- Call Chain #{i + 1} ---")
            _print_node(chain)

