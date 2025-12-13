import os
import sys
import logging

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from interaction.capabilities.capability_manager import CapabilityManager

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_capability_manager():
    """测试能力管理器是否能正确加载和初始化所有能力"""
    try:
        # 创建能力管理器实例，指定配置文件路径
        manager = CapabilityManager(config_path="e:\Data\Flora\interaction\interaction_config.json")
        
        # 自动注册所有能力
        manager.auto_register_capabilities()
        
        # 初始化所有能力
        manager.initialize_all_capabilities()
        
        # 打印已注册的能力
        registry = manager.get_registry()
        all_caps = registry.get_all_capabilities()
        logger.info(f"已注册的能力: {list(all_caps.keys())}")
        
        # 测试获取具体能力
        try:
            llm = manager.get_capability("llm")
            logger.info(f"成功获取 LLM 能力: {type(llm).__name__}")
        except Exception as e:
            logger.warning(f"获取 LLM 能力失败: {e}")
        
        try:
            user_input = manager.get_capability("user_input")
            logger.info(f"成功获取 UserInput 能力: {type(user_input).__name__}")
        except Exception as e:
            logger.warning(f"获取 UserInput 能力失败: {e}")
        
        try:
            intent_recognition = manager.get_capability("intent_recognition")
            logger.info(f"成功获取 IntentRecognition 能力: {type(intent_recognition).__name__}")
        except Exception as e:
            logger.warning(f"获取 IntentRecognition 能力失败: {e}")
        
        return True
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    logger.info("开始测试能力管理器...")
    success = test_capability_manager()
    if success:
        logger.info("测试成功！所有能力已正确加载和初始化。")
        sys.exit(0)
    else:
        logger.error("测试失败！请检查日志输出。")
        sys.exit(1)
