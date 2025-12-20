import os
import json
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class Settings:
    """系统配置类，支持从JSON文件读取和热加载"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式实现"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(Settings, cls).__new__(cls)
                cls._instance._initialize()
            return cls._instance
    
    def _initialize(self):
        """初始化配置"""
        self.config_path = Path(__file__).parent.parent / "trigger_config.json"
        self._config_data = {}
        self._load_config()
        self._start_watcher()
    
    def _load_config(self):
        """从JSON文件加载配置"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._config_data = json.load(f)
            
            # 应用配置到实例属性
            self._apply_config()
            print(f"配置已从 {self.config_path} 加载")
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            # 使用默认值
            self._config_data = {
                "task_timeout_sec": 3600,
                "pending_timeout_sec": 1800,
                "health_check_interval": 60,
                "database_url": "sqlite+aiosqlite:///./trigger.db",
                "redis_url": "redis://localhost:6379/0",
                "rabbitmq_url": "amqp://guest:guest@localhost:5672/",
                "worker_url": "http://localhost:8001",
                "message_broker_type": "redis"
            }
            self._apply_config()
    
    def _apply_config(self):
        """将配置数据应用到实例属性"""
        # 任务超时设置（秒）
        self.task_timeout_sec = int(os.getenv("TASK_TIMEOUT_SEC", str(self._config_data.get("task_timeout_sec", 3600))))
        
        # 任务处于PENDING状态的超时时间（秒）
        self.pending_timeout_sec = int(os.getenv("PENDING_TIMEOUT_SEC", str(self._config_data.get("pending_timeout_sec", 1800))))
        
        # 健康检查间隔（秒）
        self.health_check_interval = int(os.getenv("HEALTH_CHECK_INTERVAL", str(self._config_data.get("health_check_interval", 60))))
        
        # 数据库配置
        self.database_url = os.getenv("DATABASE_URL", self._config_data.get("database_url", "sqlite+aiosqlite:///./trigger.db"))
        
        # Redis配置
        self.redis_url = os.getenv("REDIS_URL", self._config_data.get("redis_url", "redis://localhost:6379/0"))
        
        # RabbitMQ配置（如果使用RabbitMQ）
        self.rabbitmq_url = os.getenv("RABBITMQ_URL", self._config_data.get("rabbitmq_url", "amqp://guest:guest@localhost:5672/"))
        
        # Worker URL
        self.worker_url = os.getenv("WORKER_URL", self._config_data.get("worker_url", "http://localhost:8001"))
        
        # 消息队列配置
        # 支持的值: "redis", "rabbitmq"
        self.message_broker_type = os.getenv("MESSAGE_BROKER_TYPE", self._config_data.get("message_broker_type", "redis"))
    
    def _start_watcher(self):
        """启动配置文件监控"""
        class ConfigFileHandler(FileSystemEventHandler):
            def __init__(self, settings_instance):
                self.settings_instance = settings_instance
            
            def on_modified(self, event):
                if event.src_path == str(self.settings_instance.config_path):
                    print(f"配置文件 {event.src_path} 已修改，重新加载...")
                    self.settings_instance._load_config()
        
        self.event_handler = ConfigFileHandler(self)
        self.observer = Observer()
        self.observer.schedule(self.event_handler, path=str(self.config_path.parent), recursive=False)
        self.observer.start()
        print(f"配置文件监控已启动，监控路径: {self.config_path.parent}")
    
    def stop_watcher(self):
        """停止配置文件监控"""
        if hasattr(self, 'observer'):
            self.observer.stop()
            self.observer.join()
            print("配置文件监控已停止")

# 创建全局配置实例
settings = Settings()
