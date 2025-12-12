"""
工具模块使用示例
展示如何使用common/utils目录下的各种工具模块
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any

# 导入所有工具函数
from . import (
    # 日志工具
    get_logger,
    LoggerConfig,
    LoggerLevel,
    log_context,
    
    # 错误处理
    retry,
    ErrorContext,
    ValidationError,
    
    # 单例模式
    Singleton,
    singleton,
    
    # 缓存工具
    LRUCache,
    TTLCache,
    cache,
    
    # 资源管理
    global_resource_manager,
    ResourcePool,
    
    # 验证工具
    StringValidator,
    NumberValidator,
    DictValidator,
    ValidationSchema,
    EmailValidator
)


# 1. 日志工具使用示例
def example_logging():
    """日志工具使用示例"""
    print("\n=== 日志工具使用示例 ===")
    
    # 配置日志
    config = LoggerConfig(
        name="example_logger",
        level=LoggerLevel.DEBUG,
        console_level=LoggerLevel.INFO,
        file_level=LoggerLevel.DEBUG,
        log_file="example.log",
        log_format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # 获取日志记录器
    logger = get_logger(config)
    
    # 记录不同级别的日志
    logger.debug("这是一条调试日志")
    logger.info("这是一条信息日志")
    logger.warning("这是一条警告日志")
    
    # 使用日志上下文
    with log_context(logger, user_id="user123", action="example"):
        logger.info("在上下文中记录的日志")
    
    print("日志已记录到example.log")


# 2. 错误处理工具使用示例
def example_error_handling():
    """错误处理工具使用示例"""
    print("\n=== 错误处理工具使用示例 ===")
    
    # 重试装饰器使用
    @retry(max_attempts=3, delay=1, exceptions=(ValueError,))
    def unstable_function(count):
        if count < 3:
            print(f"尝试 {count + 1} 失败，抛出异常")
            raise ValueError("模拟的不稳定错误")
        print(f"尝试 {count + 1} 成功")
        return "成功结果"
    
    try:
        result = unstable_function(0)
        print(f"重试后结果: {result}")
    except Exception as e:
        print(f"所有重试都失败: {e}")
    
    # 错误上下文使用
    with ErrorContext("处理用户数据"):
        try:
            # 模拟验证错误
            raise ValidationError("数据格式不正确", field="username")
        except ValidationError as e:
            print(f"捕获到验证错误: {e}")
            print(f"错误上下文: {e.context}")


# 3. 单例模式使用示例
def example_singleton():
    """单例模式使用示例"""
    print("\n=== 单例模式使用示例 ===")
    
    # 使用装饰器方式创建单例
    @singleton
    class ConfigManager:
        def __init__(self):
            self.config = {"app_name": "Flora App"}
        
        def get_config(self):
            return self.config
    
    # 使用元类方式创建单例
    class DatabaseConnection(metaclass=Singleton):
        def __init__(self):
            self.connected = False
            self.connect()
        
        def connect(self):
            self.connected = True
            print("数据库已连接")
        
        def is_connected(self):
            return self.connected
    
    # 验证单例
    config1 = ConfigManager()
    config2 = ConfigManager()
    print(f"ConfigManager 是单例: {config1 is config2}")
    
    db1 = DatabaseConnection()
    db2 = DatabaseConnection()
    print(f"DatabaseConnection 是单例: {db1 is db2}")
    print(f"数据库连接状态: {db1.is_connected()}")


# 4. 缓存工具使用示例
def example_caching():
    """缓存工具使用示例"""
    print("\n=== 缓存工具使用示例 ===")
    
    # LRU缓存示例
    lru_cache = LRUCache(max_size=3)
    lru_cache.put("key1", "value1")
    lru_cache.put("key2", "value2")
    lru_cache.put("key3", "value3")
    print(f"LRU缓存内容: {lru_cache.get_all()}")
    
    # 触发LRU替换
    lru_cache.put("key4", "value4")
    print(f"添加key4后LRU缓存内容: {lru_cache.get_all()}")
    print(f"key1是否还在缓存中: {lru_cache.get('key1') is not None}")
    
    # TTL缓存示例
    ttl_cache = TTLCache(max_size=10, ttl=2)
    ttl_cache.put("temp_key", "temp_value")
    print(f"TTL缓存初始值: {ttl_cache.get('temp_key')}")
    import time
    print("等待3秒，让TTL过期...")
    time.sleep(3)
    print(f"TTL过期后的值: {ttl_cache.get('temp_key')}")
    
    # 缓存装饰器示例
    @cache(ttl=5)
    def expensive_computation(a, b):
        print(f"执行昂贵计算: {a} + {b}")
        return a + b
    
    print("首次调用昂贵计算")
    result1 = expensive_computation(10, 20)
    print(f"结果: {result1}")
    
    print("第二次调用（应该使用缓存）")
    result2 = expensive_computation(10, 20)
    print(f"结果: {result2}")


# 5. 资源管理工具使用示例
def example_resource_management():
    """资源管理工具使用示例"""
    print("\n=== 资源管理工具使用示例 ===")
    
    # 定义资源创建和清理函数
    def create_database_connection(connection_string):
        print(f"创建数据库连接: {connection_string}")
        # 模拟数据库连接对象
        return {"connection_string": connection_string, "connected": True}
    
    def close_database_connection(connection):
        print(f"关闭数据库连接: {connection['connection_string']}")
        connection['connected'] = False
    
    # 注册资源类型
    resource_manager = global_resource_manager
    resource_manager.register_resource_type(
        "database_connection",
        create_database_connection,
        close_database_connection
    )
    
    # 使用上下文管理器获取资源
    print("使用上下文管理器获取资源:")
    with resource_manager.use_resource("database_connection", "main_db", "mysql://localhost:3306/main") as db:
        print(f"使用资源: {db}")
    
    # 直接获取和释放资源
    print("\n直接获取和释放资源:")
    db2 = resource_manager.get_resource("database_connection", "test_db", "mysql://localhost:3306/test")
    print(f"获取资源: {db2}")
    resource_manager.release_resource("database_connection", "test_db")
    
    # 资源池示例
    print("\n资源池示例:")
    def create_connection():
        return {"id": id, "created_at": datetime.now()}
    
    def validate_connection(conn):
        # 检查连接是否在30秒内创建
        return (datetime.now() - conn["created_at"]) < timedelta(seconds=30)
    
    def destroy_connection(conn):
        print(f"销毁连接: {conn}")
    
    connection_pool = ResourcePool(
        create_func=create_connection,
        max_size=5,
        validate_func=validate_connection,
        destroy_func=destroy_connection
    )
    
    # 获取连接
    conn1 = connection_pool.acquire()
    conn2 = connection_pool.acquire()
    print(f"获取了两个连接，池中资源数: {connection_pool.size}")
    print(f"可用连接数: {connection_pool.available_count}")
    
    # 释放连接
    connection_pool.release(conn1)
    print(f"释放一个连接后，可用连接数: {connection_pool.available_count}")
    
    # 清空池
    connection_pool.clear()
    print(f"清空池后，池中资源数: {connection_pool.size}")


# 6. 数据验证工具使用示例
def example_validation():
    """数据验证工具使用示例"""
    print("\n=== 数据验证工具使用示例 ===")
    
    # 基本验证器示例
    print("基本验证器:")
    string_validator = StringValidator(min_length=3, max_length=10)
    result = string_validator.validate("test")
    print(f"'test' 字符串验证: {'通过' if result else '失败'}")
    
    result = string_validator.validate("a")
    print(f"'a' 字符串验证: {'通过' if result else '失败'}")
    print(f"错误信息: {result.errors}")
    
    email_validator = EmailValidator()
    result = email_validator.validate("user@example.com")
    print(f"'user@example.com' 邮箱验证: {'通过' if result else '失败'}")
    
    # 复合验证器示例
    print("\n复合验证器:")
    number_validator = NumberValidator(min_value=0, max_value=100, is_integer=True)
    result = number_validator.validate(50)
    print(f"50 数字验证: {'通过' if result else '失败'}")
    
    # 字典验证器示例
    print("\n字典验证器:")
    user_schema = DictValidator(
        schema={
            "username": StringValidator(min_length=3, max_length=50),
            "age": NumberValidator(min_value=18, is_integer=True),
            "email": EmailValidator()
        },
        required_fields={"username", "age"},
        allow_extra_fields=False
    )
    
    valid_user = {
        "username": "john_doe",
        "age": 30,
        "email": "john@example.com"
    }
    
    invalid_user = {
        "username": "ab",
        "age": 16,
        "email": "invalid-email"
    }
    
    result = user_schema.validate(valid_user)
    print(f"有效用户验证: {'通过' if result else '失败'}")
    
    result = user_schema.validate(invalid_user)
    print(f"无效用户验证: {'通过' if result else '失败'}")
    print(f"错误信息: {result.errors}")
    
    # 验证模式示例
    print("\n验证模式:")
    schema = ValidationSchema()
    schema.add_field("name", StringValidator(min_length=2))
    schema.add_field("score", NumberValidator(min_value=0, max_value=100))
    schema.add_field("tags", ListValidator(min_length=1, item_validator=StringValidator()))
    
    data = {
        "name": "Alice",
        "score": 85,
        "tags": ["math", "science"]
    }
    
    result = schema.validate(data)
    print(f"数据验证: {'通过' if result else '失败'}")


# 主函数，运行所有示例
def run_all_examples():
    """运行所有示例"""
    print("=== Flora 工具模块使用示例 ===")
    
    example_logging()
    example_error_handling()
    example_singleton()
    example_caching()
    example_resource_management()
    example_validation()
    
    print("\n=== 所有示例运行完成 ===")


if __name__ == "__main__":
    run_all_examples()