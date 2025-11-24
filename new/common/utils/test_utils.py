"""
工具模块测试文件
对common/utils目录下的工具模块进行单元测试
"""

import unittest
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any

# 导入需要测试的工具模块
from . import (
    # 错误处理
    ErrorContext,
    retry_decorator as retry,
    ValidationError,
    
    # 单例模式
    Singleton,
    singleton,
    clear_singletons,
    
    # 缓存工具
    Cache,
    LRUCache,
    MemoryCache,
    TTLCache,
    cache,
    
    # 资源管理
    ResourceManager,
    ResourcePool,
    global_resource_manager,
    
    # 验证工具
    ValidationResult,
    Validator,
    StringValidator,
    NumberValidator,
    ListValidator,
    DictValidator,
    EmailValidator,
    ValidationSchema
)


class TestErrorHandling(unittest.TestCase):
    """错误处理模块测试"""
    
    def test_error_context(self):
        """测试错误上下文"""
        with ErrorContext("测试上下文"):
            try:
                raise ValueError("测试错误")
            except ValueError as e:
                # 检查错误是否包含上下文信息
                self.assertTrue(hasattr(e, 'context'))
                self.assertEqual(e.context, "测试错误处理 - 测试上下文")
    
    def test_retry_decorator(self):
        """测试重试装饰器"""
        attempts = [0]
        
        @retry(max_retries=3, delay=0.1, exceptions=(ValueError,))
        def unstable_function():
            attempts[0] += 1
            if attempts[0] < 3:
                raise ValueError("故意失败")
            return "成功"
        
        # 应该在第3次尝试成功
        result = unstable_function()
        self.assertEqual(result, "成功")
        self.assertEqual(attempts[0], 3)
        
        # 重置并测试失败情况
        attempts[0] = 0
        
        @retry(max_retries=2, delay=0.1, exceptions=(ValueError,))
        def always_fail():
            attempts[0] += 1
            raise ValueError("总是失败")
        
        # 应该在2次尝试后失败
        with self.assertRaises(ValueError):
            always_fail()
        self.assertEqual(attempts[0], 2)


class TestSingleton(unittest.TestCase):
    """单例模式测试"""
    
    def setUp(self):
        # 测试前清除所有单例
        clear_singletons()
    
    def test_metaclass_singleton(self):
        """测试元类方式的单例"""
        class TestSingletonClass(metaclass=Singleton):
            def __init__(self):
                self.value = id(self)
        
        instance1 = TestSingletonClass()
        instance2 = TestSingletonClass()
        
        # 验证是同一个实例
        self.assertIs(instance1, instance2)
        self.assertEqual(instance1.value, instance2.value)
    
    def test_decorator_singleton(self):
        """测试装饰器方式的单例"""
        @singleton
        class TestDecoratorSingleton:
            def __init__(self):
                self.value = id(self)
        
        instance1 = TestDecoratorSingleton()
        instance2 = TestDecoratorSingleton()
        
        # 验证是同一个实例
        self.assertIs(instance1, instance2)
        self.assertEqual(instance1.value, instance2.value)
    
    def test_thread_safety(self):
        """测试单例的线程安全性"""
        @singleton
        class ThreadSafeSingleton:
            def __init__(self):
                self.initialized = True
        
        # 创建多个线程同时获取单例
        instances = []
        
        def get_instance():
            instances.append(ThreadSafeSingleton())
        
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=get_instance)
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证所有实例都是同一个
        first_instance = instances[0]
        for instance in instances[1:]:
            self.assertIs(instance, first_instance)


class TestCache(unittest.TestCase):
    """缓存模块测试"""
    
    def test_lru_cache(self):
        """测试LRU缓存"""
        cache = LRUCache(max_size=3)
        
        # 添加元素
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")
        
        # 验证元素存在
        self.assertEqual(cache.get("key1"), "value1")
        self.assertEqual(cache.get("key2"), "value2")
        self.assertEqual(cache.get("key3"), "value3")
        
        # 测试LRU替换
        cache.put("key4", "value4")
        # key1应该被替换出去
        self.assertIsNone(cache.get("key1"))
        self.assertEqual(cache.get("key2"), "value2")
        self.assertEqual(cache.get("key3"), "value3")
        self.assertEqual(cache.get("key4"), "value4")
        
        # 测试更新已存在的键
        cache.put("key2", "new_value2")
        self.assertEqual(cache.get("key2"), "new_value2")
        
        # 测试删除
        cache.delete("key3")
        self.assertIsNone(cache.get("key3"))
        
        # 测试清除
        cache.clear()
        self.assertIsNone(cache.get("key2"))
        self.assertIsNone(cache.get("key4"))
    
    def test_ttl_cache(self):
        """测试TTL缓存"""
        cache = TTLCache(max_size=10, ttl=0.5)  # 0.5秒TTL
        
        # 添加元素
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        
        # 立即获取，应该存在
        self.assertEqual(cache.get("key1"), "value1")
        
        # 等待TTL过期
        time.sleep(0.6)
        
        # 再次获取，应该不存在
        self.assertIsNone(cache.get("key1"))
        self.assertIsNone(cache.get("key2"))
        
        # 测试更新TTL
        cache.put("key3", "value3")
        self.assertEqual(cache.get("key3"), "value3")
        
        # 更新键，应该重置TTL
        time.sleep(0.3)  # 不到过期时间
        cache.put("key3", "new_value3")
        time.sleep(0.3)  # 再等0.3秒，总共0.6秒
        
        # 应该仍然存在，因为TTL被重置了
        self.assertEqual(cache.get("key3"), "new_value3")
    
    def test_cache_decorator(self):
        """测试缓存装饰器"""
        call_count = [0]
        
        @cache(ttl=0.5)
        def cached_function(a, b):
            call_count[0] += 1
            return a + b
        
        # 第一次调用，应该执行函数
        result1 = cached_function(10, 20)
        self.assertEqual(result1, 30)
        self.assertEqual(call_count[0], 1)
        
        # 第二次调用相同参数，应该使用缓存
        result2 = cached_function(10, 20)
        self.assertEqual(result2, 30)
        self.assertEqual(call_count[0], 1)  # 调用次数不变
        
        # 调用不同参数，应该执行函数
        result3 = cached_function(20, 30)
        self.assertEqual(result3, 50)
        self.assertEqual(call_count[0], 2)  # 调用次数增加
        
        # 等待TTL过期
        time.sleep(0.6)
        
        # 再次调用，应该重新执行函数
        result4 = cached_function(10, 20)
        self.assertEqual(result4, 30)
        self.assertEqual(call_count[0], 3)  # 调用次数增加


class TestResourceManagement(unittest.TestCase):
    """资源管理模块测试"""
    
    def test_resource_manager(self):
        """测试资源管理器"""
        resource_manager = ResourceManager()
        
        # 定义资源创建和清理函数
        created_resources = []
        destroyed_resources = []
        
        def create_resource(name):
            resource = {"name": name}
            created_resources.append(resource)
            return resource
        
        def destroy_resource(resource):
            destroyed_resources.append(resource)
        
        # 注册资源类型
        resource_manager.register_resource_type("test_resource", create_resource, destroy_resource)
        
        # 获取资源
        resource1 = resource_manager.get_resource("test_resource", "resource1", "Resource 1")
        self.assertEqual(resource1["name"], "Resource 1")
        
        # 再次获取同一资源，应该返回相同实例
        resource2 = resource_manager.get_resource("test_resource", "resource1", "Resource 1")
        self.assertIs(resource1, resource2)
        
        # 获取不同资源
        resource3 = resource_manager.get_resource("test_resource", "resource2", "Resource 2")
        self.assertEqual(resource3["name"], "Resource 2")
        self.assertIsNot(resource1, resource3)
        
        # 验证创建的资源数
        self.assertEqual(len(created_resources), 2)
        
        # 释放资源（计数减1但不销毁）
        resource_manager.release_resource("test_resource", "resource1")
        # 应该没有被销毁
        self.assertEqual(len(destroyed_resources), 0)
        
        # 再次释放，应该销毁
        resource_manager.release_resource("test_resource", "resource1")
        self.assertEqual(len(destroyed_resources), 1)
        
        # 测试上下文管理器
        with resource_manager.use_resource("test_resource", "context_resource", "Context Resource") as resource:
            self.assertEqual(resource["name"], "Context Resource")
        
        # 上下文退出后应该被销毁
        self.assertEqual(len(destroyed_resources), 2)
    
    def test_resource_pool(self):
        """测试资源池"""
        # 定义资源创建、验证和销毁函数
        created_count = [0]
        destroyed_count = [0]
        
        def create_resource():
            created_count[0] += 1
            return {"id": created_count[0], "created_at": datetime.now()}
        
        def validate_resource(resource):
            # 资源5秒内有效
            return (datetime.now() - resource["created_at"]) < timedelta(seconds=5)
        
        def destroy_resource(resource):
            destroyed_count[0] += 1
        
        # 创建资源池
        pool = ResourcePool(
            create_func=create_resource,
            max_size=2,
            validate_func=validate_resource,
            destroy_func=destroy_resource
        )
        
        # 获取资源
        resource1 = pool.acquire()
        resource2 = pool.acquire()
        self.assertEqual(created_count[0], 2)
        self.assertEqual(pool.size, 2)
        
        # 尝试获取超过最大大小的资源，应该抛出异常
        with self.assertRaises(RuntimeError):
            pool.acquire()
        
        # 释放资源
        pool.release(resource1)
        self.assertEqual(pool.available_count, 1)
        
        # 再次获取，应该重用之前释放的资源
        resource3 = pool.acquire()
        self.assertIs(resource1, resource3)
        
        # 清空池
        pool.clear()
        self.assertEqual(pool.size, 0)
        self.assertEqual(destroyed_count[0], 2)


class TestValidation(unittest.TestCase):
    """数据验证模块测试"""
    
    def test_string_validator(self):
        """测试字符串验证器"""
        validator = StringValidator(min_length=3, max_length=10)
        
        # 有效输入
        result = validator.validate("test")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.errors, {})
        
        # 无效输入 - 太短
        result = validator.validate("ab")
        self.assertFalse(result.is_valid)
        self.assertIn("value", result.errors)
        
        # 无效输入 - 太长
        result = validator.validate("this is too long")
        self.assertFalse(result.is_valid)
        self.assertIn("value", result.errors)
        
        # 无效输入 - 非字符串
        result = validator.validate(123)
        self.assertFalse(result.is_valid)
        self.assertIn("value", result.errors)
    
    def test_number_validator(self):
        """测试数字验证器"""
        validator = NumberValidator(min_value=0, max_value=100, is_integer=True)
        
        # 有效输入
        result = validator.validate(50)
        self.assertTrue(result.is_valid)
        
        # 无效输入 - 小于最小值
        result = validator.validate(-10)
        self.assertFalse(result.is_valid)
        
        # 无效输入 - 大于最大值
        result = validator.validate(150)
        self.assertFalse(result.is_valid)
        
        # 无效输入 - 非整数
        result = validator.validate(50.5)
        self.assertFalse(result.is_valid)
    
    def test_email_validator(self):
        """测试邮箱验证器"""
        validator = EmailValidator()
        
        # 有效邮箱
        self.assertTrue(validator.validate("user@example.com"))
        self.assertTrue(validator.validate("user.name+tag@example.co.uk"))
        
        # 无效邮箱
        self.assertFalse(validator.validate("invalid-email"))
        self.assertFalse(validator.validate("user@"))
        self.assertFalse(validator.validate("@example.com"))
    
    def test_list_validator(self):
        """测试列表验证器"""
        validator = ListValidator(min_length=1, max_length=3, item_validator=StringValidator(min_length=2))
        
        # 有效列表
        result = validator.validate(["ab", "cd"])
        self.assertTrue(result.is_valid)
        
        # 无效列表 - 空列表
        result = validator.validate([])
        self.assertFalse(result.is_valid)
        
        # 无效列表 - 元素无效
        result = validator.validate(["a", "bc"])
        self.assertFalse(result.is_valid)
        self.assertIn("[0].value", result.errors)  # 索引前缀
    
    def test_dict_validator(self):
        """测试字典验证器"""
        validator = DictValidator(
            schema={
                "name": StringValidator(min_length=2),
                "age": NumberValidator(min_value=18)
            },
            required_fields={"name"},
            allow_extra_fields=False
        )
        
        # 有效字典
        valid_data = {"name": "John", "age": 30}
        result = validator.validate(valid_data)
        self.assertTrue(result.is_valid)
        
        # 无效字典 - 缺少必填字段
        invalid_data1 = {"age": 25}
        result = validator.validate(invalid_data1)
        self.assertFalse(result.is_valid)
        self.assertIn("name", result.errors)
        
        # 无效字典 - 字段验证失败
        invalid_data2 = {"name": "J", "age": 15}
        result = validator.validate(invalid_data2)
        self.assertFalse(result.is_valid)
        self.assertIn("name", result.errors)
        self.assertIn("age", result.errors)
        
        # 无效字典 - 额外字段
        invalid_data3 = {"name": "John", "age": 30, "email": "john@example.com"}
        result = validator.validate(invalid_data3)
        self.assertFalse(result.is_valid)
        self.assertIn("email", result.errors)
    
    def test_validation_schema(self):
        """测试验证模式"""
        schema = ValidationSchema()
        schema.add_field("username", StringValidator(min_length=3))
        schema.add_field("scores", ListValidator(item_validator=NumberValidator(min_value=0, max_value=100)))
        
        # 有效数据
        valid_data = {
            "username": "alice",
            "scores": [85, 90, 95]
        }
        result = schema.validate(valid_data)
        self.assertTrue(result.is_valid)
        
        # 无效数据
        invalid_data = {
            "username": "a",  # 太短
            "scores": [85, -10, 120]  # 包含无效分数
        }
        result = schema.validate(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertIn("username", result.errors)
        self.assertIn("scores[1].value", result.errors)  # 嵌套错误路径
        self.assertIn("scores[2].value", result.errors)


# 运行测试
if __name__ == "__main__":
    unittest.main()