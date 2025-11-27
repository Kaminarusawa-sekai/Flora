"""RouterActor和SessionActor实现，负责AgentActor的引用管理和唯一性保障"""
from typing import Dict, Any, Optional
import logging
import time
import threading
from thespian.actors import Actor, ActorAddress

# 导入Actor引用管理工具
from ..common.utils.actor_reference_manager import actor_reference_manager


class UserRequest:
    """用户请求消息类"""
    def __init__(self, tenant_id: str, node_id: str, message: Dict[str, Any]):
        self.tenant_id = tenant_id
        self.node_id = node_id
        self.message = message


class RouterActor(Actor):
    """
    全局唯一的路由Actor
    负责所有用户请求的路由和AgentActor的注册管理
    确保同一租户和节点下只有一个AgentActor实例
    """
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("RouterActor")
        
        # 使用工具类中的Redis客户端
        self.redis_client = actor_reference_manager.get_redis_client()
        self.use_redis = actor_reference_manager.is_redis_available()
        
        # 如果Redis不可用，使用内存字典作为备选
        if not self.use_redis:
            self.logger.warning("Redis不可用，将使用内存字典作为备选方案")
            self._memory_dict = {}
        
        # 设置默认TTL (1小时)
        self.default_ttl = 3600
        
    def receiveMessage(self, msg, sender):
        """处理接收到的消息"""
        if isinstance(msg, UserRequest):
            # 处理用户请求
            self._handle_user_request(msg, sender)
        elif isinstance(msg, dict):
            msg_type = msg.get("message_type")
            if msg_type == "register_actor":
                # 处理Actor注册请求
                self._handle_actor_registration(msg, sender)
            elif msg_type == "unregister_actor":
                # 处理Actor注销请求
                self._handle_actor_unregistration(msg, sender)
            elif msg_type == "refresh_ttl":
                # 处理TTL刷新请求
                self._handle_refresh_ttl(msg)
            elif msg_type == "heartbeat":
                # 处理心跳消息
                self._handle_heartbeat(msg, sender)
            else:
                self.logger.warning(f"RouterActor收到未知消息类型: {msg_type}")
        else:
            self.logger.warning(f"RouterActor收到未知消息类型: {type(msg)}")
    
    def _handle_user_request(self, msg: UserRequest, sender: ActorAddress):
        """处理用户请求，路由到已存在的Actor或创建新Actor"""
        # 使用工具类构建键
        key = actor_reference_manager.create_redis_key("session", msg.tenant_id, msg.node_id)
        
        # 检查是否已存在对应的Actor
        existing_addr_str = self._get_actor_address(key)
        
        if existing_addr_str:
            # 已存在对应的Actor，转发消息
            try:
                existing_addr = self._deserialize_address(existing_addr_str)
                if existing_addr:
                    self.logger.info(f"找到已存在的Actor，转发消息到: {existing_addr}")
                    # 转发消息，并带上原始发送者信息
                    forward_msg = msg.message.copy()
                    forward_msg["original_sender"] = sender
                    self.send(existing_addr, forward_msg)
                else:
                    self.logger.error("反序列化Actor地址返回None")
                    # 创建新Actor
                    self._create_and_register_session_actor(msg, sender)
            except Exception as e:
                self.logger.error(f"反序列化Actor地址失败: {e}")
                # 如果反序列化失败，创建新Actor
                self._create_and_register_session_actor(msg, sender)
        else:
            # 不存在对应的Actor，创建新Actor
            self._create_and_register_session_actor(msg, sender)
    
    def _create_and_register_session_actor(self, msg: UserRequest, sender: ActorAddress):
        """创建并注册新的SessionActor"""
        try:
            # 创建SessionActor
            session_addr = self.createActor(SessionActor)
            self.logger.info(f"创建新的SessionActor: {session_addr}")
            
            # 构建注册消息
            register_msg = {
                "message_type": "initialize",
                "tenant_id": msg.tenant_id,
                "node_id": msg.node_id,
                "original_message": msg.message,
                "original_sender": sender
            }
            
            # 发送初始化消息给SessionActor
            self.send(session_addr, register_msg)
            
        except Exception as e:
            self.logger.error(f"创建SessionActor失败: {e}")
            # 向原始发送者返回错误
            self.send(sender, {"status": "error", "message": f"创建Actor失败: {str(e)}"})
    
    def _handle_actor_registration(self, msg: Dict[str, Any], sender: ActorAddress):
        """处理Actor注册"""
        tenant_id = msg.get("tenant_id")
        node_id = msg.get("node_id")
        
        if not tenant_id or not node_id:
            self.logger.error("注册失败：缺少tenant_id或node_id")
            return
        
        # 使用工具类创建键和序列化地址
        key = actor_reference_manager.create_redis_key("session", tenant_id, node_id)
        addr_str = actor_reference_manager.serialize_address(sender)
        
        if not addr_str:
            self.logger.error("序列化Actor地址失败")
            return
        
        # 注册到存储后端
        if self.use_redis:
            success = actor_reference_manager.set_with_ttl(key, addr_str, self.default_ttl)
            if not success:
                self.logger.error("使用Redis注册失败")
                # 降级到内存字典
                self._memory_dict[key] = {
                    "address": addr_str,
                    "expires_at": time.time() + self.default_ttl
                }
        else:
            self._memory_dict[key] = {
                "address": addr_str,
                "expires_at": time.time() + self.default_ttl
            }
        
        self.logger.info(f"Actor注册成功: {key} -> {sender}")
    
    def _handle_actor_unregistration(self, msg: Dict[str, Any], sender: ActorAddress):
        """处理Actor注销"""
        tenant_id = msg.get("tenant_id")
        node_id = msg.get("node_id")
        
        if not tenant_id or not node_id:
            self.logger.error("注销失败：缺少tenant_id或node_id")
            return
        
        # 使用工具类创建键
            key = actor_reference_manager.create_redis_key("session", tenant_id, node_id)
        
        # 从存储后端移除
        if self.use_redis:
            success = actor_reference_manager.delete(key)
            if not success:
                self.logger.warning("使用Redis注销失败，尝试清理内存字典")
                # 同时清理内存字典中的条目
                if key in self._memory_dict:
                    del self._memory_dict[key]
        else:
            if key in self._memory_dict:
                del self._memory_dict[key]
        
        self.logger.info(f"Actor注销成功: {key}")
    
    def _handle_refresh_ttl(self, msg: Dict[str, Any]):
        """处理TTL刷新"""
        tenant_id = msg.get("tenant_id")
        node_id = msg.get("node_id")
        
        if not tenant_id or not node_id:
            self.logger.error("刷新TTL失败：缺少tenant_id或node_id")
            return
        
        # 使用工具类创建键
            key = actor_reference_manager.create_redis_key("session", tenant_id, node_id)
        
        # 刷新TTL
        if self.use_redis:
            success = actor_reference_manager.expire(key, self.default_ttl)
            if not success:
                self.logger.warning("使用Redis刷新TTL失败")
        
        # 同时更新内存字典中的过期时间（作为备份）
        if hasattr(self, '_memory_dict') and key in self._memory_dict:
            self._memory_dict[key]["expires_at"] = time.time() + self.default_ttl
    
    def _handle_heartbeat(self, msg: Dict[str, Any], sender: ActorAddress):
        """处理心跳消息"""
        tenant_id = msg.get("tenant_id")
        node_id = msg.get("node_id")
        timestamp = msg.get("timestamp", 0)
        
        if not tenant_id or not node_id:
            self.logger.error("心跳消息缺少必要信息")
            return
            
        # 刷新TTL
        self._handle_refresh_ttl(msg)
        
        # 回复心跳响应
        try:
            self.send(sender, {"message_type": "heartbeat_response", "timestamp": timestamp})
            self.logger.debug(f"收到并响应心跳: tenant={tenant_id}, node={node_id}")
        except Exception as e:
            self.logger.error(f"发送心跳响应失败: {e}")
    
    def _get_actor_address(self, key: str) -> Optional[str]:
        """从存储后端获取Actor地址"""
        # 优先从Redis获取
        if self.use_redis:
            addr_str = actor_reference_manager.get(key)
            if addr_str:
                return addr_str
        
        # 从内存字典获取作为备选
        if key in self._memory_dict:
            entry = self._memory_dict[key]
            if time.time() < entry["expires_at"]:
                return entry["address"]
            else:
                # 过期了，删除
                del self._memory_dict[key]
        
        return None
    
    def _serialize_address(self, addr: ActorAddress) -> str:
        """序列化ActorAddress为字符串"""
        return actor_reference_manager.serialize_address(addr)
    
    def _deserialize_address(self, addr_str: str) -> Optional[ActorAddress]:
        """从字符串反序列化为ActorAddress"""
        return actor_reference_manager.deserialize_address(addr_str)


class SessionActor(Actor):
    """
    会话Actor，代表一个具体的用户-节点会话
    管理AgentActor的生命周期并处理会话相关消息
    包含心跳机制确保系统健壮性
    """
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("SessionActor")
        self.tenant_id = None
        self.node_id = None
        self.agent_actor = None
        self.router_ref = None
        self.is_initialized = False
        
        # 心跳相关配置
        self.default_ttl = 3600  # 1小时
        self.heartbeat_interval = 3000  # 50分钟（略少于TTL，确保及时刷新）
        
        # 心跳计时器
        self._heartbeat_timer = None
        self._should_run_heartbeat = False
    
    def receiveMessage(self, msg, sender):
        """处理接收到的消息"""
        if isinstance(msg, dict):
            msg_type = msg.get("message_type")
            
            if msg_type == "initialize" and not self.is_initialized:
                # 初始化会话
                self._initialize(msg, sender)
            elif msg_type == "heartbeat_response":
                # 处理心跳响应
                self._handle_heartbeat_response(msg)
            elif self.is_initialized:
                # 已初始化的会话，处理业务消息
                self._forward_to_agent(msg, sender)
            else:
                self.logger.warning(f"未初始化的SessionActor收到消息: {msg_type}")
        else:
            self.logger.warning(f"SessionActor收到未知消息类型: {type(msg)}")
    
    def _initialize(self, msg: Dict[str, Any], sender: ActorAddress):
        """初始化SessionActor"""
        try:
            self.tenant_id = msg.get("tenant_id")
            self.node_id = msg.get("node_id")
            self.router_ref = sender
            
            # 创建AgentActor实例
            # 这里我们需要导入AgentActor并创建它
            # 注意：实际实现中可能需要根据配置或其他参数来创建正确的AgentActor实例
            from .agent_actor import AgentActor
            
            # 构建agent_id (可以基于tenant_id和node_id)
            agent_id = f"{self.tenant_id}_{self.node_id}"
            
            # 创建AgentActor
            # 注意：这里的创建方式需要根据实际的Actor系统进行调整
            # 在Thespian中，应该使用createActor方法
            self.agent_actor = self.createActor(AgentActor, args=(agent_id,))
            
            # 向RouterActor注册自己
            self._register_with_router()
            
            # 启动心跳机制
            self._start_heartbeat()
            
            self.is_initialized = True
            self.logger.info(f"SessionActor初始化成功: tenant={self.tenant_id}, node={self.node_id}")
            
            # 处理原始消息
            original_message = msg.get("original_message")
            original_sender = msg.get("original_sender")
            if original_message:
                self._forward_to_agent(original_message, original_sender)
            
        except Exception as e:
            self.logger.error(f"SessionActor初始化失败: {e}")
            # 向RouterActor返回错误
            self.send(sender, {"status": "error", "message": f"初始化失败: {str(e)}"})
    
    def _start_heartbeat(self):
        """启动心跳机制"""
        if not (self.tenant_id and self.node_id):
            self.logger.error("无法启动心跳：缺少tenant_id或node_id")
            return
            
        self._should_run_heartbeat = True
        
        # 启动心跳线程
        def heartbeat_thread_func():
            while self._should_run_heartbeat:
                try:
                    # 发送心跳到RouterActor
                    self._send_heartbeat()
                    # 等待指定的间隔时间
                    time.sleep(self.heartbeat_interval)
                except Exception as e:
                    self.logger.error(f"心跳线程出错: {e}")
                    # 出错后等待较短时间再尝试
                    time.sleep(60)
                    
        self._heartbeat_timer = threading.Thread(target=heartbeat_thread_func, daemon=True)
        self._heartbeat_timer.start()
        self.logger.info("心跳机制已启动")
    
    def _send_heartbeat(self):
        """发送心跳到RouterActor"""
        if not (self.tenant_id and self.node_id):
            return
            
        try:
            # 获取RouterActor引用并发送心跳
            if self.router_ref:
                self.send(self.router_ref, {
                    "message_type": "heartbeat",
                    "tenant_id": self.tenant_id,
                    "node_id": self.node_id,
                    "timestamp": time.time()
                })
                self.logger.debug(f"心跳发送: tenant={self.tenant_id}, node={self.node_id}")
        except Exception as e:
            self.logger.error(f"发送心跳失败: {e}")
    
    def _handle_heartbeat_response(self, msg: Dict[str, Any]):
        """处理心跳响应"""
        timestamp = msg.get("timestamp")
        self.logger.debug(f"收到心跳响应，timestamp: {timestamp}")
    
    def _register_with_router(self):
        """向RouterActor注册自己"""
        if self.router_ref and self.tenant_id and self.node_id:
            register_msg = {
                "message_type": "register_actor",
                "tenant_id": self.tenant_id,
                "node_id": self.node_id
            }
            self.send(self.router_ref, register_msg)
    
    def _forward_to_agent(self, msg: Dict[str, Any], sender: ActorAddress):
        """转发消息给AgentActor"""
        if self.agent_actor:
            try:
                # 刷新TTL
                self._refresh_ttl()
                
                # 转发消息，并记录原始发送者
                forwarded_msg = msg.copy()
                forwarded_msg["session_sender"] = sender
                self.send(self.agent_actor, forwarded_msg)
            except Exception as e:
                self.logger.error(f"转发消息失败: {e}")
                # 向原始发送者返回错误
                self.send(sender, {"status": "error", "message": f"转发失败: {str(e)}"})
    
    def _refresh_ttl(self):
        """刷新TTL，确保SessionActor在活跃状态时不会过期"""
        if self.router_ref and self.tenant_id and self.node_id:
            refresh_msg = {
                "message_type": "refresh_ttl",
                "tenant_id": self.tenant_id,
                "node_id": self.node_id
            }
            self.send(self.router_ref, refresh_msg)
            self.logger.debug(f"刷新TTL: tenant={self.tenant_id}, node={self.node_id}")
    
    def actorStopped(self):
        """Actor停止时调用，清理注册信息和心跳机制"""
        self.logger.info("SessionActor正在停止，清理资源...")
        
        # 停止心跳
        self._should_run_heartbeat = False
        if self._heartbeat_timer:
            try:
                self._heartbeat_timer.join(timeout=5.0)  # 等待心跳线程结束，最多5秒
            except Exception:
                pass
        
        # 向RouterActor注销自己
        if self.router_ref and self.tenant_id and self.node_id:
            try:
                unregister_msg = {
                    "message_type": "unregister_actor",
                    "tenant_id": self.tenant_id,
                    "node_id": self.node_id
                }
                self.send(self.router_ref, unregister_msg)
            except Exception as e:
                self.logger.error(f"注销失败: {e}")
        
        # 停止AgentActor
        if self.agent_actor:
            try:
                self.stopActor(self.agent_actor)
            except Exception as e:
                self.logger.error(f"停止AgentActor失败: {e}")
        
        self.logger.info("SessionActor已停止")
