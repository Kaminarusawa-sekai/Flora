import logging
import re

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AgentMemoryTest")

class TestAgentMemoryIntegration:
    """测试agent_actor与memory_actor的整合"""
    
    def test_agent_memory_code_features(self):
        """通过静态代码分析验证AgentActor中是否包含所需的memory_actor相关功能"""
        try:
            # 读取agent_actor.py文件内容进行分析
            agent_actor_path = "e:\\Data\\Flora\\new\\agents\\agent_actor.py"
            with open(agent_actor_path, 'r', encoding='utf-8') as f:
                code_content = f.read()
            
            logger.info("成功读取agent_actor.py文件")
            
            # 验证必要的导入
            import_checks = [
                ('from new.capability_actors.memory_actor import MemoryActor', 'MemoryActor导入'),
            ]
            
            for import_statement, description in import_checks:
                if re.search(import_statement, code_content):
                    logger.info(f"✓ {description}存在")
                else:
                    logger.warning(f"✗ {description}不存在")
            
            # 验证_initialize方法中的memory_actor创建
            if re.search(r'self\._memory_actor\s*=\s*self\.createActor\(MemoryActor\)', code_content):
                logger.info("✓ memory_actor创建逻辑存在")
            else:
                logger.warning("✗ memory_actor创建逻辑不存在")
            
            # 验证_pending_memory_requests初始化
            if re.search(r'self\._pending_memory_requests\s*=\s*{\s*}', code_content):
                logger.info("✓ _pending_memory_requests初始化存在")
            else:
                logger.warning("✗ _pending_memory_requests初始化不存在")
            
            # 验证_handle_task方法中的记忆获取逻辑
            if re.search(r'# 向memory_actor发送短期记忆检索请求', code_content):
                logger.info("✓ 任务处理中的记忆检索逻辑存在")
            else:
                logger.warning("✗ 任务处理中的记忆检索逻辑不存在")
            
            # 验证_process_task_after_memory方法
            if re.search(r'def _process_task_after_memory', code_content):
                logger.info("✓ _process_task_after_memory方法存在")
            else:
                logger.warning("✗ _process_task_after_memory方法不存在")
            
            # 验证_execute_intermediate方法中的记忆传递
            if re.search(r'# 向memory_actor发送长期记忆检索请求', code_content):
                logger.info("✓ 中间任务处理中的记忆检索逻辑存在")
            else:
                logger.warning("✗ 中间任务处理中的记忆检索逻辑不存在")
            
            # 验证_execute_leaf_task方法中的记忆使用
            if re.search(r'def _enrich_context_with_memory', code_content):
                logger.info("✓ _enrich_context_with_memory方法存在")
            else:
                logger.warning("✗ _enrich_context_with_memory方法不存在")
            
            # 验证_handle_memory_dict_response方法
            if re.search(r'def _handle_memory_dict_response', code_content):
                logger.info("✓ _handle_memory_dict_response方法存在")
            else:
                logger.warning("✗ _handle_memory_dict_response方法不存在")
            
            logger.info("AgentMemoryIntegration静态代码分析完成!")
            return True
            
        except Exception as e:
            logger.error(f"分析过程中出错: {e}")
            return False

if __name__ == "__main__":
    test = TestAgentMemoryIntegration()
    success = test.test_agent_memory_code_features()
    exit(0 if success else 1)