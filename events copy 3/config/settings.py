import json
import os
import time
from typing import Dict, Any
from pydantic_settings import BaseSettings
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class SettingsConfigHandler(FileSystemEventHandler):
    """监控配置文件变化的事件处理器"""
    
    def __init__(self, settings_instance):
        self.settings_instance = settings_instance
    
    def on_modified(self, event):
        """当配置文件被修改时触发"""
        if event.src_path == self.settings_instance._full_config_path:
            print(f"配置文件 {event.src_path} 已修改，重新加载配置...")
            self.settings_instance.load_config()


# 默认配置文件路径
DEFAULT_CONFIG_FILE_PATH = "../event_config.json"


class Settings(BaseSettings):
    # 数据库配置
    db_url: str
    
    # Redis 配置
    redis_url: str
    
    # RabbitMQ 配置
    rabbitmq_url: str
    
    # 服务配置
    worker_callback_url: str
    
    # FastAPI 配置
    host: str
    port: int
    
    # 健康检查配置
    health_check_interval: int
    task_timeout_sec: int
    pending_timeout_sec: int
    
    # 私有属性
    _observer: Observer = None
    _full_config_path: str = None
    _config_data: Dict[str, Any] = None
    
    def __init__(self, **kwargs):
        # 确定配置文件的绝对路径
        base_dir = os.path.dirname(os.path.abspath(__file__))
        full_config_path = os.path.join(base_dir, DEFAULT_CONFIG_FILE_PATH)
        
        # 读取配置文件
        self._config_data = None
        self.load_config(full_config_path)
        
        # 调用父类初始化
        super().__init__(**self._config_data)
        
        # 设置实例属性
        self._full_config_path = full_config_path
        self._observer = None
        
        # 启动配置文件监控
        self._start_watcher()
    
    def load_config(self, full_config_path=None):
        """从 JSON 文件加载配置"""
        # 使用传入的路径或当前实例的路径
        config_path = full_config_path or self._full_config_path
        
        # 如果配置文件不存在，创建默认配置
        if not os.path.exists(config_path):
            self._create_default_config(config_path)
        
        # 读取配置文件
        with open(config_path, "r", encoding="utf-8") as f:
            self._config_data = json.load(f)
        
        # 更新实例属性
        for key, value in self._config_data.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def _create_default_config(self, file_path: str):
        """创建默认配置文件"""
        default_config = {
            "db_url": "postgresql+asyncpg://user:pass@localhost/command_tower",
            "redis_url": "redis://localhost:6379/0",
            "rabbitmq_url": "amqp://guest:guest@localhost:5672/",
            "worker_callback_url": "http://worker-svc:8000",
            "host": "0.0.0.0",
            "port": 8000,
            "health_check_interval": 60,
            "task_timeout_sec": 300,
            "pending_timeout_sec": 3600
        }
        
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 写入默认配置
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        
        print(f"已创建默认配置文件: {file_path}")
    
    def _start_watcher(self):
        """启动配置文件监控"""
        # 创建监控器和事件处理器
        event_handler = SettingsConfigHandler(self)
        self._observer = Observer()
        self._observer.schedule(event_handler, path=os.path.dirname(self._full_config_path), recursive=False)
        self._observer.start()
        
        print(f"已启动配置文件监控: {self._full_config_path}")
    
    def __del__(self):
        """停止监控器"""
        try:
            if hasattr(self, '_observer') and self._observer:
                self._observer.stop()
                self._observer.join(timeout=1.0)  # 设置超时，避免阻塞
        except (RuntimeError, AttributeError):
            # 忽略线程未启动或已停止的错误
            pass


# 创建全局设置实例
settings = Settings()