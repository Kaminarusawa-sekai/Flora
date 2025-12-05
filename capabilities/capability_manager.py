import logging
import os
import pkgutil
import importlib
import inspect
import re
from typing import Dict, Any, Type, Optional
from .registry import CapabilityRegistry
from .capability_base import CapabilityBase
from .capbility_config import CapabilityConfig

class CapabilityManager:
    """
    能力管理类 (重构版)
    负责动态扫描目录、自动化注册和统一初始化所有能力。
    """
    
    def __init__(self, config_path: str = "config.json"):
        self.registry = CapabilityRegistry()
        self.config = CapabilityConfig(config_path)
        self._setup_logging()
        
        # 存储扫描到的类定义： { "QwenAdapter": QwenAdapterClass, ... }
        self._available_classes: Dict[str, Type[CapabilityBase]] = {}
        
        # 存储能力类型映射： { "QwenAdapter": "llm", ... }
        self._class_type_map: Dict[str, str] = {}
        
    def _setup_logging(self) -> None:
        log_level = self.config.get_global_config().get("log_level", "INFO")
        logging.basicConfig(
            level=getattr(logging, log_level),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)

    def _to_snake_case(self, name: str) -> str:
        """辅助函数：驼峰转蛇形 (TaskRouter -> task_router)"""
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

    def auto_register_capabilities(self) -> None:
        """
        [核心改进] 动态扫描：
        1. 遍历 capabilities 目录下的子文件夹 (视为 capability_type)
        2. 遍历文件夹内的 .py 模块
        3. 自动导入并提取继承自 CapabilityBase 的类
        """
        self.logger.info("Starting dynamic discovery of capabilities...")
        
        # 获取 capabilities 包的根路径
        # 假设 manager 在 capabilities/capability_manager.py，所以 base_path 是当前目录
        base_path = os.path.dirname(__file__)
        
        # 遍历根目录下的子文件夹 (例如: llm, memory, routing...)
        for item in os.listdir(base_path):
            dir_path = os.path.join(base_path, item)
            
            # 只处理目录，且跳过 __pycache__
            if os.path.isdir(dir_path) and not item.startswith("__"):
                capability_type = item  # 文件夹名即为能力类型 (如 llm)
                self._scan_package(dir_path, f".{item}", capability_type)

        self.logger.info(f"Discovery completed. Found {len(self._available_classes)} capability classes.")

    def _scan_package(self, path: str, package_prefix: str, capability_type: str):
        """扫描指定包下的所有模块"""
        # package_prefix 例如: ".llm" (相对导入路径)
        
        for _, name, _ in pkgutil.iter_modules([path]):
            try:
                # 动态导入模块: .llm.qwen_adapter
                module = importlib.import_module(f"{package_prefix}.{name}", package=__package__)
                
                # 检查模块中的所有类
                for attr_name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) 
                        and issubclass(obj, CapabilityBase) 
                        and obj is not CapabilityBase):
                        
                        # 注册类
                        # 1. 使用类名注册 (TaskRouter)
                        self._register_class_internal(attr_name, obj, capability_type)
                        
                        # 2. 同时也支持蛇形命名 (task_router)，方便配置匹配
                        snake_name = self._to_snake_case(attr_name)
                        if snake_name != attr_name:
                            self._register_class_internal(snake_name, obj, capability_type)
                            
            except Exception as e:
                self.logger.warning(f"Failed to load module {name} in {capability_type}: {e}")

    def _register_class_internal(self, name: str, cls: Type[CapabilityBase], cap_type: str):
        """内部注册逻辑"""
        # 如果有重复名字，优先保留先扫描到的，或者覆盖（根据需求）
        # 这里选择覆盖，并记录日志
        self._available_classes[name] = cls
        self._class_type_map[name] = cap_type
        self.logger.debug(f"Discovered: {name} -> {cls.__name__} (Type: {cap_type})")

    def initialize_all_capabilities(self) -> None:
        self.logger.info("Starting initialization based on Config...")
        
        # 获取 capabilities 根配置
        root_config = self.config.config  # 假设获取到了完整的 config 字典
        caps_config = root_config.get("capabilities", {})

        # 遍历每一个能力大类 (如: llm, memory, routing)
        for cap_type, type_config in caps_config.items():
            if not isinstance(type_config, dict):
                continue
            
            # === 新增逻辑：检查是否有 active_impl 开关 ===
            active_implementation = type_config.get("active_impl")
            
            # 决定要初始化哪些具体的实现
            targets_to_init = []
            
            if active_implementation:
                # 模式 A: 【单选模式】
                # 如果指定了 active_impl，只初始化这一个
                if active_implementation in type_config:
                    targets_to_init.append(active_implementation)
                    self.logger.info(f"[{cap_type}] Active implementation selected: {active_implementation}")
                else:
                    self.logger.warning(f"[{cap_type}] active_impl is '{active_implementation}' but no config found for it.")
            else:
                # 模式 B: 【全选模式】
                # 没有指定 active_impl，则初始化该类型下所有配置了的具体能力
                # (适用于需要同时存在多个实例的情况，比如可能有 multiple memory stores)
                for key in type_config.keys():
                    if key != "active_impl" and isinstance(type_config[key], dict):
                        targets_to_init.append(key)

            # === 开始循环初始化 ===
            for cap_name in targets_to_init:
                cap_params = type_config.get(cap_name, {})
                
                # 在扫描到的类中查找 (支持类名 或 蛇形名)
                target_class = self._available_classes.get(cap_name)
                
                if not target_class:
                    self.logger.warning(f"Class not found for capability: {cap_name}")
                    continue

                try:
                    # 1. 实例化 & 初始化
                    try:
                        instance = target_class()
                    except TypeError:
                        instance = target_class(**cap_params)
                    
                    if hasattr(instance, 'initialize'):
                        instance.initialize(cap_params)
                    
                    # 2. 注册具体名称 (例如: "qwen")
                    # 使用闭包固定 instance
                    def factory_wrapper(inst=instance): 
                        return inst
                        
                    self.registry.register(capability_type=cap_name, factory=factory_wrapper)
                    
                    # 3. [关键步骤] 注册通用别名 (例如: "llm")
                    # 如果这是被选中的 active_impl，或者该类型下只有一个实现
                    # 我们就把它注册为该类型的默认实现
                    if active_implementation == cap_name:
                        self.registry.register(capability_type=cap_type, factory=factory_wrapper)
                        self.logger.info(f"Registered '{cap_name}' as default handler for '{cap_type}'")
                        
                    self.logger.info(f"Initialized: {cap_name}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to initialize {cap_name}: {e}", exc_info=True)

        self.logger.info("Initialization completed.")

    def _get_capability_type(self, capability_name: str) -> str:
        """
        不再需要硬编码字典，直接从扫描结果中查
        """
        return self._class_type_map.get(capability_name, "unknown")

    # --- 以下方法保持不变或做简单的透传 ---

    def get_capability(self, name: str, expected_type: Type[CapabilityBase] = CapabilityBase) -> CapabilityBase:
        return self.registry.get_capability(name, expected_type)

    def shutdown_all_capabilities(self) -> None:
        self.logger.info("Shutting down capabilities...")
        # 可以在这里遍历 registry 中的实例调用 shutdown
        pass
        
    def save_config(self) -> None:
        self.config.save_config()

    def get_registry(self) -> CapabilityRegistry:
        return self.registry