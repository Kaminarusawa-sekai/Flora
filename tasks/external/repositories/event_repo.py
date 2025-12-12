"""
事件仓库实现
负责事件的持久化存储和查询
"""
from typing import Dict, Any, List, Optional
from tasks.common.messages.event_message import SystemEventMessage


class EventRepository:
    """
    事件仓库类
    负责事件的持久化存储和查询
    """
    
# 全局模拟数据库实例，所有 EventRepository 共享
_global_mock_db = None


class EventRepository:
    """
    事件仓库类
    负责事件的持久化存储和查询
    """
    
    def __init__(self):
        """初始化事件仓库"""
        # 初始化数据库连接
        global _global_mock_db
        try:
            from tasks.external.database.mysql_client import MySQLClient
            self.db = MySQLClient()
        except ImportError:
            # 如果MySQL客户端不存在，使用模拟实现
            if _global_mock_db is None:
                _global_mock_db = self._create_mock_database()
            self.db = _global_mock_db
    
    def _create_mock_database(self):
        """
        创建模拟数据库实例
        
        Returns:
            模拟数据库实例
        """
        class MockMySQLClient:
            def __init__(self):
                self.events = []
            
            def execute_update(self, sql: str, params: tuple):
                """模拟执行更新操作"""
                import json
                event = {
                    "id": params[0],
                    "trace_id": params[1],
                    "event_type": params[2],
                    "source": params[3],
                    "content": params[4],
                    "created_at": params[5],
                    "level": params[6]
                }
                self.events.append(event)
                return 1
            
            def query(self, sql: str, params: tuple):
                """模拟执行查询操作"""
                trace_id = params[0]
                # 过滤出符合trace_id的事件，并按时间排序
                filtered_events = [e for e in self.events if e["trace_id"] == trace_id]
                filtered_events.sort(key=lambda x: x["created_at"])
                return filtered_events
        
        return MockMySQLClient()
    
    def save(self, event: SystemEventMessage) -> bool:
        """
        保存事件到数据库
        
        Args:
            event: 系统事件消息
            
        Returns:
            保存是否成功
        """
        import json
        from datetime import datetime
        
        # 转换为数据库存储格式
        db_event = event.to_db_dict()
        
        # 执行插入操作
        sql = """
            INSERT INTO system_events 
            (id, trace_id, event_type, source, content, created_at, level)
            VALUES (%s, %s, %s, %s, %s, FROM_UNIXTIME(%s), %s)
        """
        
        try:
            result = self.db.execute_update(sql, (
                db_event["id"],
                db_event["trace_id"],
                db_event["event_type"],
                db_event["source"],
                db_event["content"],
                event.timestamp,
                db_event["level"]
            ))
            return result > 0
        except Exception as e:
            # 记录错误日志
            import logging
            log = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
            log.error(f"Failed to save event: {str(e)}", exc_info=True)
            return False
    
    def get_timeline(self, trace_id: str) -> List[Dict[str, Any]]:
        """
        获取某个任务的所有相关事件，按时间排序
        供 API Server 调用
        
        Args:
            trace_id: 追踪ID (Task ID)
            
        Returns:
            按时间排序的事件列表
        """
        sql = """
            SELECT event_type, source, content, created_at, level
            FROM system_events
            WHERE trace_id = %s
            ORDER BY created_at ASC
        """
        
        try:
            rows = self.db.query(sql, (trace_id,))
            
            # 处理查询结果
            events = []
            for row in rows:
                # 解析JSON格式的content字段
                import json
                content = json.loads(row["content"]) if isinstance(row["content"], str) else row["content"]
                
                events.append({
                    "event_type": row["event_type"],
                    "source": row["source"],
                    "content": content,
                    "timestamp": row["created_at"].timestamp() if hasattr(row["created_at"], "timestamp") else row["created_at"],
                    "level": row["level"]
                })
            
            return events
        except Exception as e:
            # 记录错误日志
            import logging
            log = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
            log.error(f"Failed to get timeline: {str(e)}", exc_info=True)
            return []
    
    def get_event_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        根据事件ID获取事件
        
        Args:
            event_id: 事件ID
            
        Returns:
            事件字典或None
        """
        sql = """
            SELECT id, trace_id, event_type, source, content, created_at, level
            FROM system_events
            WHERE id = %s
        """
        
        try:
            rows = self.db.query(sql, (event_id,))
            if rows:
                row = rows[0]
                import json
                content = json.loads(row["content"]) if isinstance(row["content"], str) else row["content"]
                
                return {
                    "event_id": row["id"],
                    "trace_id": row["trace_id"],
                    "event_type": row["event_type"],
                    "source": row["source"],
                    "content": content,
                    "timestamp": row["created_at"].timestamp() if hasattr(row["created_at"], "timestamp") else row["created_at"],
                    "level": row["level"]
                }
            return None
        except Exception as e:
            # 记录错误日志
            import logging
            log = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
            log.error(f"Failed to get event by id: {str(e)}", exc_info=True)
            return None
    
    def get_events_by_type(self, event_type: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        根据事件类型获取事件
        
        Args:
            event_type: 事件类型
            limit: 限制返回数量
            
        Returns:
            事件列表
        """
        sql = """
            SELECT id, trace_id, event_type, source, content, created_at, level
            FROM system_events
            WHERE event_type = %s
            ORDER BY created_at DESC
            LIMIT %s
        """
        
        try:
            rows = self.db.query(sql, (event_type, limit))
            
            # 处理查询结果
            events = []
            for row in rows:
                import json
                content = json.loads(row["content"]) if isinstance(row["content"], str) else row["content"]
                
                events.append({
                    "event_id": row["id"],
                    "trace_id": row["trace_id"],
                    "event_type": row["event_type"],
                    "source": row["source"],
                    "content": content,
                    "timestamp": row["created_at"].timestamp() if hasattr(row["created_at"], "timestamp") else row["created_at"],
                    "level": row["level"]
                })
            
            return events
        except Exception as e:
            # 记录错误日志
            import logging
            log = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
            log.error(f"Failed to get events by type: {str(e)}", exc_info=True)
            return []
    
    def delete_events_by_trace_id(self, trace_id: str) -> bool:
        """
        根据trace_id删除事件
        
        Args:
            trace_id: 追踪ID
            
        Returns:
            删除是否成功
        """
        sql = """
            DELETE FROM system_events
            WHERE trace_id = %s
        """
        
        try:
            result = self.db.execute_update(sql, (trace_id,))
            return result > 0
        except Exception as e:
            # 记录错误日志
            import logging
            log = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
            log.error(f"Failed to delete events by trace_id: {str(e)}", exc_info=True)
            return False