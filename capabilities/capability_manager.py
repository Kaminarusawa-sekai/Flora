"""能力管理模块，负责自动化注册和初始化"""
import logging
from typing import Dict, Any, Type
from .registry import CapabilityRegistry
from .capability_base import CapabilityBase
from .config import CapabilityConfig


class CapabilityManager:
    """
    能力管理类，负责自动化注册和初始化所有能力
    """
    
    def __init__(self, config_path: str = "config.json"):
        """
        初始化能力管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.registry = CapabilityRegistry()
        self.config = CapabilityConfig(config_path)
        self._setup_logging()
        self._capability_classes: Dict[str, Type[CapabilityBase]] = {}
        
    def _setup_logging(self) -> None:
        """
        设置日志
        """
        log_level = self.config.get_global_config().get("log_level", "INFO")
        logging.basicConfig(
            level=getattr(logging, log_level),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)
    
    def register_capability_class(self, name: str, capability_class: Type[CapabilityBase]) -> None:
        """
        注册能力类
        
        Args:
            name: 能力名称
            capability_class: 能力类
        """
        self._capability_classes[name] = capability_class
        self.logger.info(f"Registered capability class: {name}")
    
    def auto_register_capabilities(self) -> None:
        """
        自动注册所有能力
        """
        self.logger.info("Starting auto-registration of capabilities...")
        
        # 注册LLM能力
        try:
            from .llm.qwen_adapter import QwenAdapter
            self.register_capability_class("qwen", QwenAdapter)
        except ImportError as e:
            self.logger.warning(f"Failed to import QwenAdapter: {e}")
        
        # 注册记忆能力
        try:
            from .llm_memory.memory_capability import MemoryCapability
            self.register_capability_class("core_memory", MemoryCapability)
        except ImportError as e:
            self.logger.warning(f"Failed to import MemoryCapability: {e}")
        
        # 注册TextToSQL能力
        try:
            from .text_to_sql.vanna_text_to_sql import VannaTextToSQL
            self.register_capability_class("vanna", VannaTextToSQL)
        except ImportError as e:
            self.logger.warning(f"Failed to import VannaTextToSQL: {e}")
        
        # 注册决策能力
        try:
            from .decision.decision_impl import TaskStrategyCapability, TaskOperationCapability
            self.register_capability_class("task_strategy", TaskStrategyCapability)
            self.register_capability_class("task_operation", TaskOperationCapability)
        except ImportError as e:
            self.logger.warning(f"Failed to import decision capabilities: {e}")
        
        self.logger.info(f"Auto-registration completed. Registered {len(self._capability_classes)} capability classes.")
    
    def _create_qwen_factory(self, capability_class, capability_config):
        """
        创建QwenAdapter工厂
        """
        def factory():
            instance = capability_class(**capability_config)
            instance.initialize({})
            return instance
        return factory
    
    def _create_memory_factory(self, capability_class, capability_config):
        """
        创建MemoryCapability工厂
        """
        def factory():
            instance = capability_class(user_id=capability_config.get("user_id"))
            instance.initialize(capability_config)
            return instance
        return factory
    
    def _create_vanna_factory(self, capability_class, capability_config):
        """
        创建VannaTextToSQL工厂
        """
        def factory():
            instance = capability_class()
            instance.initialize(capability_config)
            return instance
        return factory
    
    def initialize_all_capabilities(self) -> None:
        """
        初始化所有已注册的能力
        """
        self.logger.info("Starting initialization of all capabilities...")
        
        for capability_name, capability_class in self._capability_classes.items():
            try:
                # 确定能力类型
                capability_type = self._get_capability_type(capability_name)
                
                # 获取配置
                capability_config = self.config.get_capability_config(capability_type, capability_name)
                if not capability_config:
                    self.logger.warning(f"No config found for capability: {capability_name}")
                    capability_config = {}
                
                # 根据不同的能力类使用不同的初始化方式
                if capability_name == "qwen":
                    # QwenAdapter需要在__init__中传递参数
                    factory = self._create_qwen_factory(capability_class, capability_config)
                    self.registry.register(capability_type=capability_name, factory=factory)
                
                elif capability_name == "core_memory":
                    # MemoryCapability需要在__init__中传递user_id
                    factory = self._create_memory_factory(capability_class, capability_config)
                    self.registry.register(capability_type=capability_name, factory=factory)
                
                elif capability_name == "vanna":
                    # VannaTextToSQL需要在__init__中传递参数
                    factory = self._create_vanna_factory(capability_class, capability_config)
                    self.registry.register(capability_type=capability_name, factory=factory)
                
                else:
                    # 默认方式
                    self.registry.register_class(
                        capability_type=capability_name,
                        capability_class=capability_class,
                        init_kwargs=capability_config
                    )
                
                self.logger.info(f"Successfully registered and initialized capability: {capability_name}")
            except Exception as e:
                self.logger.error(f"Failed to initialize capability {capability_name}: {e}", exc_info=True)
        
        self.logger.info("Initialization of all capabilities completed.")
    
    def _get_capability_type(self, capability_name: str) -> str:
        """
        根据能力名称确定能力类型
        
        Args:
            capability_name: 能力名称
            
        Returns:
            能力类型
        """
        # 简单的映射逻辑，可以根据需要扩展
        capability_type_map = {
            "qwen": "llm",
            "core_memory": "memory",
            "vanna": "text_to_sql"
        }
        return capability_type_map.get(capability_name, "unknown")
    
    def get_capability(self, name: str, expected_type: Type[CapabilityBase]) -> CapabilityBase:
        """
        获取能力实例
        
        Args:
            name: 能力名称
            expected_type: 期望的能力类型
            
        Returns:
            能力实例
        """
        return self.registry.get_capability(name, expected_type)
    
    def shutdown_all_capabilities(self) -> None:
        """
        关闭所有能力
        """
        self.logger.info("Shutting down all capabilities...")
        # 目前注册表不直接管理实例的生命周期，
        # 实际使用时，由调用方负责调用实例的shutdown方法
        self.logger.info("Shutdown completed.")
    
    def save_config(self) -> None:
        """
        保存配置
        """
        self.config.save_config()
        self.logger.info(f"Config saved to {self.config.config_path}")
    
    def update_capability_config(self, capability_type: str, capability_name: str, config: Dict[str, Any]) -> None:
        """
        更新能力配置
        
        Args:
            capability_type: 能力类型
            capability_name: 能力名称
            config: 新的配置
        """
        self.config.update_capability_config(capability_type, capability_name, config)
        self.logger.info(f"Updated config for {capability_type}.{capability_name}")
    
    def get_capability_config(self, capability_type: str, capability_name: str) -> Dict[str, Any]:
        """
        获取能力配置
        
        Args:
            capability_type: 能力类型
            capability_name: 能力名称
            
        Returns:
            能力配置
        """
        return self.config.get_capability_config(capability_type, capability_name)
    
    def get_registry(self) -> CapabilityRegistry:
        """
        获取注册表实例
        
        Returns:
            注册表实例
        """
        return self.registry