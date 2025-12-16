"""能力配置管理模块"""
from typing import Dict, Any, Optional
import sys
import os

# 添加项目根目录到路径，以便导入config模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import os
import logging
from typing import Dict, Any, Optional

class CapabilityConfig:
    """
    能力配置管理类，负责从 config.json 加载配置
    """
    
    def __init__(self, config_path: str = "./tasks/config.json"):
        """
        初始化配置管理
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)
        # 核心修改：这里不再调用 _get_config_from_main，而是直接加载文件
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        [核心修复] 从 JSON 文件加载配置
        """
        if not os.path.exists(self.config_path):
            self.logger.warning(f"Config file not found at {self.config_path}. Using empty config.")
            return {}
            
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load config file: {e}")
            return {}
    
    def get_capability_config(self, capability_type: str, capability_name: str) -> Optional[Dict[str, Any]]:
        """
        获取指定能力的配置
        路径：capabilities -> [type] -> [name]
        """
        # 保护性获取：防止 capabilities 键不存在
        caps = self.config.get("capabilities", {})
        if not caps:
            return {}
            
        # 获取类型层 (如 connectors)
        type_config = caps.get(capability_type, {})
        if not type_config:
            return {}
            
        # 获取名称层 (如 universal_excution)
        return type_config.get(capability_name, {})
    
    def get_global_config(self) -> Dict[str, Any]:
        """
        获取全局配置
        注意：你的 JSON 里写的是 "global_config"，但之前的代码写的是 "global"
        这里我已经帮你修正为读取 "global_config"
        """
        return self.config.get("global_config", {})
    
    # --- 以下方法保持不变或根据需要保留 ---
    
    def update_capability_config(self, capability_type: str, capability_name: str, config: Dict[str, Any]) -> None:
        if "capabilities" not in self.config:
            self.config["capabilities"] = {}
        if capability_type not in self.config["capabilities"]:
            self.config["capabilities"][capability_type] = {}
        self.config["capabilities"][capability_type][capability_name] = config
        
    def save_config(self) -> None:
        """支持将内存中的修改写回 json 文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")