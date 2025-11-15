"""数据访问能力Actor"""
from typing import Dict, Any, Optional, List
from thespian.actors import Actor
import logging
from ..capabilities.data_access.data_interface import DataAccessInterface
from ..capabilities.data_access.data_actor import DataAnalyticsActor
from ..capabilities.registry import capability_registry
from ..external.business_data.mysql_business import MySQLBusinessData


class DataActor(Actor):
    """
    数据访问能力Actor
    负责数据的查询、分析和管理
    从agent/io/data_actor.py迁移并重构
    集成并使用data_analytics层的功能
    """
    
    def __init__(self):
        """
        初始化数据Actor
        """
        self.logger = logging.getLogger(__name__)
        self.data_access = None
        self.business_data = None
        self.query_processor = None
        self.initialize_data_components()
    
    def initialize_data_components(self):
        """
        初始化数据访问组件
        使用capabilities中的数据访问能力
        """
        try:
            # 通过能力注册表获取数据访问能力
            data_capability = capability_registry.get_capability("data_access")
            
            if data_capability:
                self.data_access = data_capability
            else:
                # 如果能力注册表中没有，直接创建
                self.data_access = DataAnalyticsActor()
            
            # 初始化业务数据访问
            from ..common.config.config_manager import get_config
            business_config = get_config("business_data")
            if business_config and business_config.get("enabled", True):
                self.business_data = MySQLBusinessData(business_config)
            
            self.logger.info("数据组件初始化成功")
        except Exception as e:
            self.logger.error(f"数据组件初始化失败: {e}")
    
    def receiveMessage(self, msg: Dict[str, Any], sender: str) -> None:
        """
        接收消息并处理
        
        Args:
            msg: 消息内容
            sender: 发送者
        """
        try:
            msg_type = msg.get("type", "")
            
            if msg_type == "initialize":
                self._handle_initialize(msg, sender)
            elif msg_type == "query":
                self._handle_query(msg, sender)
            elif msg_type == "get_by_id":
                self._handle_get_by_id(msg, sender)
            elif msg_type == "update":
                self._handle_update(msg, sender)
            elif msg_type == "insert":
                self._handle_insert(msg, sender)
            elif msg_type == "delete":
                self._handle_delete(msg, sender)
            elif msg_type == "analyze":
                self._handle_analyze(msg, sender)
            elif msg_type == "get_schema":
                self._handle_get_schema(msg, sender)
            elif msg_type == "test_connection":
                self._handle_test_connection(msg, sender)
            elif msg_type == "get_capability_params":
                self._handle_get_capability_params(msg, sender)
            else:
                self.logger.warning(f"未知消息类型: {msg_type}")
                self.send(sender, {"status": "error", "message": f"未知消息类型: {msg_type}"})
        
        except Exception as e:
            self.logger.error(f"处理数据请求失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
    
    def _handle_initialize(self, msg: Dict[str, Any], sender: str):
        """
        处理初始化消息
        """
        config = msg.get("config", {})
        
        # 重新初始化数据访问组件
        if config.get("data_access"):
            self.data_access = DataAnalyticsActor(config["data_access"])
        
        # 重新初始化业务数据
        if config.get("business_data"):
            self.business_data = MySQLBusinessData(config["business_data"])
        
        self.send(sender, {"status": "success"})
    
    def _handle_query(self, msg: Dict[str, Any], sender: str):
        """
        处理查询请求
        """
        query_str = msg.get("query")
        params = msg.get("params", {})
        use_vanna = msg.get("use_vanna", False)
        
        if not query_str:
            self.send(sender, {"status": "error", "message": "缺少查询语句"})
            return
        
        try:
            # 优先使用数据访问能力
            if self.data_access:
                results = self.data_access.query(query_str, params)
                self.send(sender, {"status": "success", "results": results})
            else:
                # 直接使用业务数据
                if self.business_data:
                    results = self.business_data.execute_query(query_str, params)
                    self.send(sender, {"status": "success", "results": results})
                else:
                    self.send(sender, {"status": "error", "message": "数据访问组件未初始化"})
        except Exception as e:
            self.logger.error(f"执行查询失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
    
    def _handle_get_by_id(self, msg: Dict[str, Any], sender: str):
        """
        根据ID获取数据
        """
        data_id = msg.get("id")
        data_type = msg.get("type")
        
        if not data_id or not data_type:
            self.send(sender, {"status": "error", "message": "缺少必要参数"})
            return
        
        try:
            result = self.data_access.get_data_by_id(data_id, data_type)
            self.send(sender, {"status": "success", "result": result})
        except Exception as e:
            self.logger.error(f"获取数据失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
    
    def _handle_update(self, msg: Dict[str, Any], sender: str):
        """
        更新数据
        """
        data_id = msg.get("id")
        data_type = msg.get("type")
        updates = msg.get("updates", {})
        
        if not data_id or not data_type:
            self.send(sender, {"status": "error", "message": "缺少必要参数"})
            return
        
        try:
            success = self.data_access.update_data(data_id, data_type, updates)
            self.send(sender, {"status": "success" if success else "error", "updated": success})
        except Exception as e:
            self.logger.error(f"更新数据失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
    
    def _handle_insert(self, msg: Dict[str, Any], sender: str):
        """
        插入数据
        """
        data_type = msg.get("type")
        data = msg.get("data", {})
        
        if not data_type:
            self.send(sender, {"status": "error", "message": "缺少数据类型"})
            return
        
        try:
            result = self.data_access.insert_data(data_type, data)
            self.send(sender, {"status": "success", "result": result})
        except Exception as e:
            self.logger.error(f"插入数据失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
    
    def _handle_delete(self, msg: Dict[str, Any], sender: str):
        """
        删除数据
        """
        data_id = msg.get("id")
        data_type = msg.get("type")
        
        if not data_id or not data_type:
            self.send(sender, {"status": "error", "message": "缺少必要参数"})
            return
        
        try:
            success = self.data_access.delete_data(data_id, data_type)
            self.send(sender, {"status": "success" if success else "error", "deleted": success})
        except Exception as e:
            self.logger.error(f"删除数据失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
    
    def _handle_analyze(self, msg: Dict[str, Any], sender: str):
        """
        数据分析请求
        """
        data = msg.get("data", {})
        analysis_type = msg.get("analysis_type", "basic")
        
        try:
            result = self.data_access.analyze_data(data, analysis_type)
            self.send(sender, {"status": "success", "analysis": result})
        except Exception as e:
            self.logger.error(f"数据分析失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
    
    def _handle_get_schema(self, msg: Dict[str, Any], sender: str):
        """
        获取数据库模式
        """
        source = msg.get("source", "business")
        
        try:
            if source == "business" and self.business_data:
                tables = self.business_data.get_tables()
                schema = {}
                for table in tables:
                    schema[table] = self.business_data.get_table_schema(table)
                self.send(sender, {"status": "success", "schema": schema})
            else:
                # 使用数据访问能力
                schema = self.data_access.get_schema()
                self.send(sender, {"status": "success", "schema": schema})
        except Exception as e:
            self.logger.error(f"获取模式失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
    
    def _handle_get_capability_params(self, msg: Dict[str, Any], sender: str):
        """获取能力执行参数"""
        capability = msg.get("capability")
        task_id = msg.get("task_id")
        
        try:
            if not capability:
                self.send(sender, DataQueryResponse(request_id=task_id, error="缺少能力名称"))
                return
            
            # 模拟从数据库获取能力参数
            params = {
                "api_key": "your-api-key",  # 实际应从配置或数据库获取
                "base_url": "DIFY_URI",     # 实际应从配置或数据库获取
                "timeout": 30
            }
            
            # 如果有业务数据访问，可以从数据库获取更多参数
            if self.business_data:
                # 示例：从业务数据获取能力参数
                try:
                    db_params = self.business_data.execute_query(
                        "SELECT * FROM capability_params WHERE capability = %s",
                        (capability,)
                    )
                    if db_params:
                        params.update(db_params[0])
                except Exception as e:
                    self.logger.warning(f"从业务数据获取参数失败: {e}")
            
            self.send(sender, DataQueryResponse(request_id=task_id, result=params))
        except Exception as e:
            self.logger.error(f"获取能力参数失败: {e}")
            self.send(sender, DataQueryResponse(request_id=task_id, error=str(e)))
    
    def _handle_test_connection(self, msg: Dict[str, Any], sender: str):
        """测试连接"""
        source = msg.get("source", "business")
        
        try:
            if source == "business" and self.business_data:
                result = self.business_data.test_connection()
                self.send(sender, {"status": "success" if result["connected"] else "error", "test_result": result})
            else:
                # 测试数据访问能力
                result = self.data_access.test_connection()
                self.send(sender, {"status": "success" if result["connected"] else "error", "test_result": result})
        except Exception as e:
            self.logger.error(f"测试连接失败: {e}")
            self.send(sender, {"status": "error", "message": str(e)})
