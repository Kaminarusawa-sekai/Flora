import sys
import os
import logging
from typing import List, Dict, Any

# 设置日志级别为INFO
logging.basicConfig(level=logging.INFO)

def read_file_content(file_path: str) -> str:
    """
    读取文件内容
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logging.error(f"无法读取文件 {file_path}: {e}")
        return ""

def check_import_statement(file_content: str) -> bool:
    """
    检查导入语句是否正确
    """
    expected_import = "from new.capabilities.llm_memory.manager import UnifiedMemoryManager"
    return expected_import in file_content

def check_manager_initialization(file_content: str) -> bool:
    """
    检查管理器初始化是否正确
    """
    expected_initialization = "self.manager = UnifiedMemoryManager(user_id=agent_id)"
    return expected_initialization in file_content

def check_method_calls(file_content: str) -> Dict[str, bool]:
    """
    检查是否使用了正确的方法调用
    """
    method_checks = {
        "ingest": ".ingest(" in file_content,
        "build_context_for_llm": ".build_context_for_llm(" in file_content,
        "search_memories": ".search_memories(" in file_content,
        "clear_short_term": ".clear_short_term(" in file_content,
        # 确保不再使用旧的方法
        "store_memory": ".store_memory(" not in file_content,
        "retrieve_memory": ".retrieve_memory(" not in file_content,
        "update_memory": ".update_memory(" not in file_content,
        "clear_memory": ".clear_memory(" not in file_content,
        "search_memory": ".search_memory(" not in file_content,
        "get_status": ".get_status(" not in file_content,
        "initialize": ".initialize(" not in file_content
    }
    return method_checks

def verify_agent_actor_implementation():
    """
    验证agent_actor.py的实现是否正确使用了UnifiedMemoryManager
    """
    file_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "new", "agents", "agent_actor.py")
    
    # 读取文件内容
    content = read_file_content(file_path)
    if not content:
        return False
    
    # 执行检查
    results = {
        "import_statement": check_import_statement(content),
        "manager_initialization": check_manager_initialization(content),
        "method_calls": check_method_calls(content)
    }
    
    # 输出检查结果
    logging.info("验证agent_actor.py的memory实现...")
    logging.info(f"导入语句检查: {'通过' if results['import_statement'] else '失败'}")
    logging.info(f"管理器初始化检查: {'通过' if results['manager_initialization'] else '失败'}")
    
    logging.info("方法调用检查:")
    all_method_checks_passed = True
    for method, passed in results['method_calls'].items():
        status = "通过" if passed else "失败"
        logging.info(f"  {method}: {status}")
        if not passed:
            all_method_checks_passed = False
    
    # 整体验证结果
    all_passed = results['import_statement'] and results['manager_initialization'] and all_method_checks_passed
    
    if all_passed:
        logging.info("\n验证成功！agent_actor.py正确使用了UnifiedMemoryManager及其方法。")
    else:
        logging.error("\n验证失败！agent_actor.py的memory实现仍有问题。")
    
    return all_passed

def verify_manager_import_fix():
    """
    验证manager.py的导入语句修复
    """
    file_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "new", "capabilities", "llm_memory", "manager.py")
    
    # 读取文件内容
    content = read_file_content(file_path)
    if not content:
        return False
    
    # 检查相对导入是否正确
    expected_imports = [
        "from .short_term import ShortTermMemory",
        "from .resource_memory import ResourceMemory",
        "from .vault import KnowledgeVault"
    ]
    
    all_imports_correct = all(import_statement in content for import_statement in expected_imports)
    
    logging.info("\n验证manager.py的导入修复...")
    for imp in expected_imports:
        status = "通过" if imp in content else "失败"
        logging.info(f"  {imp}: {status}")
    
    if all_imports_correct:
        logging.info("导入修复验证成功！")
    else:
        logging.error("导入修复验证失败！")
    
    return all_imports_correct

def main():
    """
    主函数，执行所有验证
    """
    agent_actor_passed = verify_agent_actor_implementation()
    manager_passed = verify_manager_import_fix()
    
    if agent_actor_passed and manager_passed:
        logging.info("\n所有验证通过！代码修改成功。")
        return True
    else:
        logging.error("\n验证未全部通过，请检查上述问题。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
