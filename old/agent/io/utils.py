# utils.py
import re
from config import MIN_RESULT_ROWS, MAX_SQL_LENGTH, ALLOWED_TABLES

def is_safe_sql(sql: str) -> bool:
    """审核 SQL 安全性"""
    sql_upper = sql.upper().strip()
    
    # 1. 必须是 SELECT
    if not sql_upper.startswith("SELECT"):
        return False
    
    # 2. 禁止危险关键字
    dangerous = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "EXEC", "UNION"]
    if any(kw in sql_upper for kw in dangerous):
        return False

    # 3. 长度限制
    if len(sql) > MAX_SQL_LENGTH:
        return False

    # 4. 表名白名单（可选）
    # if ALLOWED_TABLES:
    #     # 简单提取表名（生产中建议用 SQL 解析器）
    #     tables = re.findall(r'FROM\s+`?(\w+)`?', sql_upper)
    #     if not all(t.lower() in [x.lower() for x in ALLOWED_TABLES] for t in tables):
    #         return False

    return True

def should_learn(df, sql: str) -> bool:
    """判断是否值得学习"""
    if not is_safe_sql(sql):
        return False
    if df is None or df.empty:
        return False
    if len(df) < MIN_RESULT_ROWS:
        return False
    return True

if __name__ == "__main__":
    # 测试 SQL
    test_sql = "SELECT * FROM eqiai_agent.agent_global_key WHERE global_value LIKE '%核心裂变玩法%'"
    print(is_safe_sql(test_sql))  # 应返回 True