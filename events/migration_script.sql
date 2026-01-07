-- Events 系统重构数据迁移脚本

-- 1. 创建新表 EventTrace
CREATE TABLE IF NOT EXISTS event_traces (
    trace_id VARCHAR(64) PRIMARY KEY,
    request_id VARCHAR(64) INDEX,
    status VARCHAR(32) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    input_params JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at DATETIME NULL,
    meta JSON NULL
);

-- 2. 修改 EventDefinition 表，移除废弃字段
ALTER TABLE event_definitions
    DROP COLUMN IF EXISTS code_ref,
    DROP COLUMN IF EXISTS entrypoint,
    DROP COLUMN IF EXISTS schedule_type,
    DROP COLUMN IF EXISTS cron_expr,
    DROP COLUMN IF EXISTS loop_config,
    DROP COLUMN IF EXISTS resource_profile,
    DROP COLUMN IF EXISTS strategy_tags,
    DROP COLUMN IF EXISTS default_params,
    DROP COLUMN IF EXISTS default_timeout,
    DROP COLUMN IF EXISTS retry_policy,
    DROP COLUMN IF EXISTS ui_config,
    DROP COLUMN IF EXISTS updated_at,
    DROP COLUMN IF EXISTS last_triggered_at;

-- 3. 修改 EventInstance 表
ALTER TABLE event_instances
    MODIFY COLUMN trace_id VARCHAR(64) NOT NULL,
    MODIFY COLUMN def_id VARCHAR(64) NULL,
    DROP COLUMN IF EXISTS job_id,
    DROP COLUMN IF EXISTS schedule_type,
    DROP COLUMN IF EXISTS round_index,
    DROP COLUMN IF EXISTS cron_trigger_time;

-- 4. 添加外键约束（可选，根据实际情况决定是否添加）
-- ALTER TABLE event_instances
--     ADD CONSTRAINT fk_event_instances_trace_id
--     FOREIGN KEY (trace_id) REFERENCES event_traces(trace_id) ON DELETE CASCADE;

-- 5. 更新现有数据，确保新字段有合理的默认值
UPDATE event_instances SET trace_id = UUID() WHERE trace_id IS NULL;
UPDATE event_traces SET status = 'SUCCEEDED' WHERE status IS NULL;
