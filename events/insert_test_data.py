import uuid
import json
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# 导入模型
from events.external.db.models import (
    Base,
    EventTraceDB,
    EventInstanceDB,
    EventLogDB,
    EventDefinitionDB
)
from common.enums import ActorType, NodeType, EventInstanceStatus

# 配置数据库连接
DATABASE_URL = "sqlite:///./events.db"  # 替换为你的数据库连接字符串

# 创建同步引擎和会话
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 确保表存在
Base.metadata.create_all(bind=engine)

# 测试数据
REQUEST_ID = "c27d2e14-76ff-4284-b977-052aa965bc64"
TRACE_ID = "test-trace-" + str(uuid.uuid4())[:8]
USER_ID = "test-user-123"

# 创建测试数据
def create_test_data():
    with SessionLocal() as session:
        # 1. 创建 EventTraceDB
        trace = EventTraceDB(
            trace_id=TRACE_ID,
            request_id=REQUEST_ID,
            status="RUNNING",
            user_id=USER_ID,
            input_params={"test_param": "test_value"},
            created_at=datetime.now(timezone.utc)
        )
        session.add(trace)
        session.commit()
        
        # 2. 创建 EventDefinitionDB (可选，用于测试)
        definition = EventDefinitionDB(
            id="test-def-1",
            name="Test Definition",
            user_id=USER_ID,
            node_type=NodeType.AGENT,
            actor_type=ActorType.AGENT
        )
        session.add(definition)
        session.commit()
        
        # 3. 创建根节点 EventInstanceDB
        root_instance = EventInstanceDB(
            id="root-" + str(uuid.uuid4())[:8],
            trace_id=TRACE_ID,
            request_id=REQUEST_ID,
            parent_id=None,
            def_id="test-def-1",
            user_id=USER_ID,
            node_path="/",
            depth=0,
            actor_type=ActorType.AGENT,
            status=EventInstanceStatus.RUNNING,
            input_params={"root_param": "root_value"},
            runtime_state_snapshot={"lifecycle": "running"},
            created_at=datetime.now(timezone.utc),
            started_at=datetime.now(timezone.utc)
        )
        session.add(root_instance)
        session.commit()
        
        # 4. 创建子节点 EventInstanceDB
        child_instances = []
        for i in range(3):
            child_id = f"child-{i}-" + str(uuid.uuid4())[:8]
            child = EventInstanceDB(
                id=child_id,
                trace_id=TRACE_ID,
                request_id=REQUEST_ID,
                parent_id=root_instance.id,
                def_id="test-def-1",
                user_id=USER_ID,
                node_path=f"/{root_instance.id}/",
                depth=1,
                actor_type=ActorType.AGENT,
                status=EventInstanceStatus.SUCCESS if i < 2 else EventInstanceStatus.FAILED,
                input_params={"child_param": f"child_value_{i}"},
                runtime_state_snapshot={"lifecycle": "completed" if i < 2 else "failed"},
                created_at=datetime.now(timezone.utc),
                started_at=datetime.now(timezone.utc),
                finished_at=datetime.now(timezone.utc),
                progress=100,
                result_summary=f"Result for child {i}" if i < 2 else None,
                error_detail={"msg": f"Error for child {i}"} if i == 2 else None
            )
            child_instances.append(child)
        
        session.add_all(child_instances)
        session.commit()
        
        # 5. 创建 EventLogDB 记录
        logs = []
        
        # 根节点日志
        logs.append(EventLogDB(
            id=str(uuid.uuid4()),
            instance_id=root_instance.id,
            trace_id=TRACE_ID,
            event_type="TRACE_STARTED",
            level="INFO",
            content="Root task started",
            payload_snapshot={"input_params": root_instance.input_params},
            execution_node="worker-1",
            agent_id="agent-1",
            created_at=datetime.now(timezone.utc)
        ))
        
        logs.append(EventLogDB(
            id=str(uuid.uuid4()),
            instance_id=root_instance.id,
            trace_id=TRACE_ID,
            event_type="STARTED",
            level="INFO",
            content="Root task started execution",
            payload_snapshot={"runtime_state_snapshot": root_instance.runtime_state_snapshot},
            execution_node="worker-1",
            agent_id="agent-1",
            created_at=datetime.now(timezone.utc)
        ))
        
        # 拓扑扩展日志
        logs.append(EventLogDB(
            id=str(uuid.uuid4()),
            instance_id=root_instance.id,
            trace_id=TRACE_ID,
            event_type="TOPOLOGY_EXPANDED",
            level="INFO",
            content=f"Spawned {len(child_instances)} subtasks",
            payload_snapshot={
                "children_ids": [child.id for child in child_instances],
                "meta_preview": "test meta"
            },
            execution_node="worker-1",
            agent_id="agent-1",
            created_at=datetime.now(timezone.utc)
        ))
        
        # 子节点日志
        for i, child in enumerate(child_instances):
            logs.append(EventLogDB(
                id=str(uuid.uuid4()),
                instance_id=child.id,
                trace_id=TRACE_ID,
                event_type="STARTED",
                level="INFO",
                content=f"Child task {i} started",
                payload_snapshot={"input_params": child.input_params},
                execution_node=f"worker-{i+2}",
                agent_id=f"agent-{i+2}",
                created_at=datetime.now(timezone.utc)
            ))
            
            if child.status == EventInstanceStatus.SUCCESS:
                logs.append(EventLogDB(
                    id=str(uuid.uuid4()),
                    instance_id=child.id,
                    trace_id=TRACE_ID,
                    event_type="COMPLETED",
                    level="INFO",
                    content=f"Child task {i} completed successfully",
                    payload_snapshot={"output_result": {"result": f"success_{i}"}},
                    execution_node=f"worker-{i+2}",
                    agent_id=f"agent-{i+2}",
                    created_at=datetime.now(timezone.utc)
                ))
            else:
                logs.append(EventLogDB(
                    id=str(uuid.uuid4()),
                    instance_id=child.id,
                    trace_id=TRACE_ID,
                    event_type="FAILED",
                    level="ERROR",
                    content=f"Child task {i} failed",
                    payload_snapshot={"error_detail": child.error_detail},
                    execution_node=f"worker-{i+2}",
                    agent_id=f"agent-{i+2}",
                    error_detail=child.error_detail,
                    created_at=datetime.now(timezone.utc)
                ))
        
        session.add_all(logs)
        session.commit()
        
        print(f"Test data created successfully!")
        print(f"REQUEST_ID: {REQUEST_ID}")
        print(f"TRACE_ID: {TRACE_ID}")
        print(f"Root Instance ID: {root_instance.id}")
        print(f"Child Instance IDs: {[child.id for child in child_instances]}")

if __name__ == "__main__":
    create_test_data()
