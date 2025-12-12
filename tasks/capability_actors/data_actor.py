import logging
import thespian.actors as actors
from tasks.agents.tree.tree_manager import treeManager
from tasks.common.messages import (
    DataQueryRequest, DataQueryResponse, 
    InitDataQueryActor
)



# 引入刚刚拆分出来的 Capability
from tasks.capabilities.registry import capability_registry

logger = logging.getLogger(__name__)

class DataActor(actors.Actor):
    def __init__(self):
        super().__init__()
        # 实例化能力对象（工人）
        from tasks.capabilities.registry import capability_registry
        from tasks.capabilities.text_to_sql.text_to_sql import ITextToSQLCapability
        self.analyst = capability_registry.get_capability("text_to_sql",expected_type=ITextToSQLCapability)
        
        # Actor 自身的状态
        self.agent_id = None
        self._memory_actor = None
        self._latest_memory = {}
        
        logger.info("[DataActor] Created")

    def receiveMessage(self, msg, sender):
        if isinstance(msg, InitDataQueryActor):
            self._handle_init(msg, sender)
            
        elif isinstance(msg, DataQueryRequest):
            self._handle_query(msg, sender)
            
            
        else:
            logger.warning(f"Unknown message: {type(msg)}")

    def _handle_init(self, msg, sender):
        try:
            self.agent_id = msg.agent_id
            
            # 1. 获取元数据 (通过 Registry)
            meta = treeManager.get_agent_meta(self.agent_id)
            if not meta:
                raise ValueError(f"Agent {self.agent_id} meta not found")

            # 2. 调用 Capability 进行重逻辑初始化
            self.analyst.initialize(self.agent_id, meta)
            logger.info(f"DataActor initialized for agent {self.agent_id}")
            # 4. (可选) 回复初始化成功，如果不回复，Router可能会超时
            # self.send(sender, {"status": "SUCCESS", "type": "INIT"})

        except Exception as e:
            logger.exception(f"Init failed for {msg.agent_id}")
            self.send(sender, {"error": str(e)})

    def _handle_query(self, msg: DataQueryRequest, sender):
        try:
            # 1. 直接调用 Capability 执行任务
            # 注意：Actor 将最新的内存上下文传递进去
            output = self.analyst.execute_query(
                user_query=msg.query,
                context=self._latest_memory
            )
            
            # 2. 包装成功响应
            response = DataQueryResponse(
                request_id=msg.request_id,
                result=output["result"],
                # metadata={"sql": output["sql"]} # 如果需要传回 SQL
            )
            self.send(sender, response)

        except Exception as e:
            logger.exception(f"Query failed: {msg.query}")
            # 3. 包装失败响应
            self.send(sender, DataQueryResponse(
                request_id=msg.request_id,
                result=None,
                error=str(e)
            ))