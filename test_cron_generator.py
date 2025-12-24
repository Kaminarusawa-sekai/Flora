from datetime import datetime, timezone
from trigger.drivers.schedulers.cron_generator import CronGenerator

# 测试不同类型的 base_time 输入
def test_get_next_run_time():
    # 测试 1: 不提供 base_time
    cron_expr = "*/5 * * * *"  # 每 5 分钟执行一次
    next_run = CronGenerator.get_next_run_time(cron_expr)
    print(f"Test 1 - No base_time:")
    print(f"  Input: None")
    print(f"  Output: {next_run}")
    print(f"  Is aware: {next_run.tzinfo is not None}")
    print(f"  Timezone: {next_run.tzinfo}")
    assert next_run.tzinfo is not None, "Output should be aware datetime"
    assert next_run.tzinfo == timezone.utc, "Output should be in UTC timezone"
    print("✅ Passed")
    print()
    
    # 测试 2: 提供 naive datetime 作为 base_time
    naive_time = datetime.now()
    next_run = CronGenerator.get_next_run_time(cron_expr, naive_time)
    print(f"Test 2 - Naive datetime as base_time:")
    print(f"  Input: {naive_time} (naive)")
    print(f"  Output: {next_run}")
    print(f"  Is aware: {next_run.tzinfo is not None}")
    print(f"  Timezone: {next_run.tzinfo}")
    assert next_run.tzinfo is not None, "Output should be aware datetime"
    assert next_run.tzinfo == timezone.utc, "Output should be in UTC timezone"
    print("✅ Passed")
    print()
    
    # 测试 3: 提供 UTC aware datetime 作为 base_time
    utc_aware_time = datetime.now(timezone.utc)
    next_run = CronGenerator.get_next_run_time(cron_expr, utc_aware_time)
    print(f"Test 3 - UTC aware datetime as base_time:")
    print(f"  Input: {utc_aware_time}")
    print(f"  Output: {next_run}")
    print(f"  Is aware: {next_run.tzinfo is not None}")
    print(f"  Timezone: {next_run.tzinfo}")
    assert next_run.tzinfo is not None, "Output should be aware datetime"
    assert next_run.tzinfo == timezone.utc, "Output should be in UTC timezone"
    print("✅ Passed")
    print()
    
    # 测试 4: 提供其他时区的 aware datetime 作为 base_time
    # 创建一个 UTC+8 的 aware datetime
    from datetime import timedelta
    beijing_timezone = timezone(timedelta(hours=8))
    beijing_aware_time = datetime.now(beijing_timezone)
    next_run = CronGenerator.get_next_run_time(cron_expr, beijing_aware_time)
    print(f"Test 4 - Other timezone aware datetime as base_time:")
    print(f"  Input: {beijing_aware_time} (Beijing timezone)")
    print(f"  Output: {next_run}")
    print(f"  Is aware: {next_run.tzinfo is not None}")
    print(f"  Timezone: {next_run.tzinfo}")
    assert next_run.tzinfo is not None, "Output should be aware datetime"
    assert next_run.tzinfo == timezone.utc, "Output should be in UTC timezone"
    print("✅ Passed")
    print()
    
    # 测试 5: 测试不同的 CRON 表达式
    test_cases = [
        "0 0 * * *",  # 每天午夜
        "0 12 * * 1-5",  # 工作日中午 12 点
        "30 8 * * 1,3,5",  # 每周一、三、五早上 8:30
    ]
    
    for expr in test_cases:
        next_run = CronGenerator.get_next_run_time(expr)
        print(f"Test 5 - CRON expression: {expr}")
        print(f"  Output: {next_run}")
        print(f"  Is aware: {next_run.tzinfo is not None}")
        print(f"  Timezone: {next_run.tzinfo}")
        assert next_run.tzinfo is not None, f"Output for {expr} should be aware datetime"
        assert next_run.tzinfo == timezone.utc, f"Output for {expr} should be in UTC timezone"
        print("✅ Passed")
        print()
    
    print("🎉 All tests passed!")

if __name__ == "__main__":
    test_get_next_run_time()