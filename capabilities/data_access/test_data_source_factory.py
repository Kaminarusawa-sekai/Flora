"""
测试数据源工厂类
"""
import unittest
import logging
from .data_source import DataSourceFactory, DataSourceType, DataSource

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestDataSourceFactory(unittest.TestCase):
    """测试数据源工厂类"""
    
    def setUp(self):
        """每个测试用例前的设置"""
        # 清除所有缓存的数据源实例
        DataSourceFactory.release_all_data_sources()
    
    def tearDown(self):
        """每个测试用例后的清理"""
        # 清除所有缓存的数据源实例
        DataSourceFactory.release_all_data_sources()
    
    def test_create_memory_data_source(self):
        """测试创建内存数据源"""
        config = {
            'tables': {
                'users': {'id': 'int', 'name': 'str', 'age': 'int'},
                'products': {'id': 'int', 'name': 'str', 'price': 'float'}
            },
            'initial_data': {
                'users': [
                    {'id': 1, 'name': 'Alice', 'age': 30},
                    {'id': 2, 'name': 'Bob', 'age': 25}
                ]
            }
        }
        
        # 创建数据源
        data_source = DataSourceFactory.create_data_source('memory', config)
        
        # 验证数据源创建成功
        self.assertIsNotNone(data_source)
        self.assertEqual(data_source.source_type, DataSourceType.MEMORY)
        self.assertTrue(data_source.is_connected)
        
        # 测试查询功能
        result = data_source.execute_query('select * from users')
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['name'], 'Alice')
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        config = {'tables': {'test': {}}}
        
        # 创建两个具有相同实例ID的数据源
        instance1 = DataSourceFactory.create_data_source('memory', config, instance_id='test_instance')
        instance2 = DataSourceFactory.create_data_source('memory', config, instance_id='test_instance')
        
        # 验证它们是同一个实例
        self.assertIs(instance1, instance2)
        
        # 通过get_data_source获取实例
        instance3 = DataSourceFactory.get_data_source('test_instance')
        self.assertIs(instance1, instance3)
    
    def test_unsupported_data_source_type(self):
        """测试不支持的数据源类型"""
        config = {}
        
        # 验证抛出ValueError异常
        with self.assertRaises(ValueError):
            DataSourceFactory.create_data_source('unsupported_type', config)
    
    def test_exception_handling(self):
        """测试异常处理"""
        # 故意提供错误的配置
        config = {'invalid_config': True}
        
        # 创建一个SQLite数据源，但使用内存类型（应该会失败但不会抛出异常）
        data_source = DataSourceFactory.create_data_source('sqlite', config)
        
        # 验证数据源对象被创建，但is_connected为False
        self.assertIsNotNone(data_source)
        self.assertFalse(data_source.is_connected)
    
    def test_register_custom_data_source(self):
        """测试注册自定义数据源"""
        # 定义一个自定义数据源类
        class CustomDataSource(DataSource):
            def _connect(self):
                return {}
            
            def _disconnect(self):
                pass
            
            def _execute_query(self, query, params=None):
                return [{'result': 'custom'}]
            
            def _execute_command(self, command, params=None):
                return 1
            
            def _get_schema(self, entity=None):
                return {'custom': {}}
        
        # 注册自定义数据源
        DataSourceFactory.register_data_source('custom', CustomDataSource)
        
        # 验证注册成功
        self.assertIn('custom', DataSourceFactory.get_available_types())
        
        # 创建自定义数据源
        data_source = DataSourceFactory.create_data_source('custom', {})
        self.assertIsNotNone(data_source)
        self.assertTrue(data_source.is_connected)
        
        # 测试查询功能
        result = data_source.execute_query('test')
        self.assertEqual(result[0]['result'], 'custom')
    
    def test_release_data_source(self):
        """测试释放数据源"""
        config = {'tables': {'test': {}}}
        
        # 创建数据源
        data_source = DataSourceFactory.create_data_source('memory', config, instance_id='release_test')
        
        # 验证数据源被缓存
        self.assertIsNotNone(DataSourceFactory.get_data_source('release_test'))
        
        # 释放数据源
        success = DataSourceFactory.release_data_source('release_test')
        
        # 验证释放成功
        self.assertTrue(success)
        self.assertIsNone(DataSourceFactory.get_data_source('release_test'))
    
    def test_release_all_data_sources(self):
        """测试释放所有数据源"""
        config = {'tables': {'test': {}}}
        
        # 创建多个数据源
        DataSourceFactory.create_data_source('memory', config, instance_id='test1')
        DataSourceFactory.create_data_source('memory', config, instance_id='test2')
        
        # 验证数据源被缓存
        self.assertIsNotNone(DataSourceFactory.get_data_source('test1'))
        self.assertIsNotNone(DataSourceFactory.get_data_source('test2'))
        
        # 释放所有数据源
        DataSourceFactory.release_all_data_sources()
        
        # 验证所有数据源都被释放
        self.assertIsNone(DataSourceFactory.get_data_source('test1'))
        self.assertIsNone(DataSourceFactory.get_data_source('test2'))
    
    def test_get_available_types(self):
        """测试获取可用的数据源类型"""
        types = DataSourceFactory.get_available_types()
        
        # 验证基本类型都在列表中
        self.assertIn('memory', types)
        self.assertIn('sqlite', types)
        self.assertIn('csv', types)
        self.assertIn('json', types)
        self.assertIn('rest_api', types)
    
    def test_test_data_source(self):
        """测试测试数据源连接功能"""
        # 测试成功情况
        config = {'tables': {'test': {}}}
        success, message = DataSourceFactory.test_data_source('memory', config)
        self.assertTrue(success)
        self.assertEqual(message, 'Connection successful')
        
        # 测试失败情况
        config = {'invalid_config': True}
        success, message = DataSourceFactory.test_data_source('sqlite', config)
        self.assertFalse(success)


if __name__ == '__main__':
    unittest.main()
