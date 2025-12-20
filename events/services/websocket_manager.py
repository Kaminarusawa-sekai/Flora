from typing import Dict, List
from fastapi import WebSocket

class ConnectionManager:
    """
    WebSocket连接管理器，用于管理前端的WebSocket连接
    核心职责：
    1. 维护trace_id到WebSocket连接列表的映射
    2. 处理连接的建立和断开
    3. 向特定trace的所有连接推送事件
    """
    def __init__(self):
        # 存储trace_id到WebSocket连接列表的映射
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, trace_id: str):
        """
        建立WebSocket连接，并将其添加到指定trace_id的连接列表中
        """
        await websocket.accept()
        if trace_id not in self.active_connections:
            self.active_connections[trace_id] = []
        self.active_connections[trace_id].append(websocket)

    def disconnect(self, websocket: WebSocket, trace_id: str):
        """
        断开WebSocket连接，并将其从连接列表中移除
        """
        if trace_id in self.active_connections:
            self.active_connections[trace_id].remove(websocket)
            # 如果该trace_id下没有连接了，清理该条目
            if not self.active_connections[trace_id]:
                del self.active_connections[trace_id]

    async def broadcast_to_trace(self, trace_id: str, message: dict):
        """
        向指定trace_id的所有连接推送消息
        """
        if trace_id in self.active_connections:
            # 遍历连接列表，发送消息
            for websocket in self.active_connections[trace_id]:
                try:
                    await websocket.send_json(message)
                except Exception:
                    # 如果发送失败，将该连接从列表中移除
                    self.active_connections[trace_id].remove(websocket)
                    # 如果该trace_id下没有连接了，清理该条目
                    if not self.active_connections[trace_id]:
                        del self.active_connections[trace_id]
