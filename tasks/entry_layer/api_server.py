# api_server.py
"""
Flora多智能体协作系统 - API服务器实现（基于FastAPI）

FastAPI作为AgentActor的“翻译官”，将HTTP JSON请求转换为Python对象消息，
发送给Thespian ActorSystem，并将结果返回给用户。
"""

import logging
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from thespian.actors import ActorSystem
import uuid

# 导入Actor和消息定义
from tasks.agents.agent_actor import AgentActor
from tasks.common.messages.task_messages import AgentTaskMessage, ResumeTaskMessage

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Flora 多智能体协作系统 API",
    description="Flora系统的RESTful API接口",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. 启动Actor系统（单例）
actor_system = ActorSystem('multiprocTCPBase')

# 2. 获取AgentActor的引用
agent_actor_ref = actor_system.createActor(AgentActor)

# --- 定义请求体模型 (Pydantic) ---
class TaskRequest(BaseModel):
    user_input: str
    user_id: str

class ResumeRequest(BaseModel):
    task_id: str
    parameters: dict
    user_id: str

# --- 核心接口 1: 执行任务 ---
@app.post("/tasks/execute")
def execute_task(req: TaskRequest):
    """
    执行新任务
    
    Args:
        req: 任务请求，包含用户输入和用户ID
        
    Returns:
        任务执行结果
    """
    try:
        # 1. 生成唯一task_id
        task_id = str(uuid.uuid4())
        
        # 2. 构造Thespian消息
        msg = AgentTaskMessage(
            user_input=req.user_input,
            user_id=req.user_id,
            task_id=task_id
        )
        
        # 3. 发送给Actor并等待回复（同步阻塞）
        # timeout设为60秒，因为LLM处理可能较慢
        response = actor_system.ask(agent_actor_ref, msg, timeout=60)
        
        if response is None:
            raise HTTPException(status_code=504, detail="Agent processing timeout")
        
        # 4. 返回结果给前端
        return {
            "success": True,
            "data": response,
            "error": None
        }
    except Exception as e:
        logger.error(f"Error executing task: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "data": None,
                "error": str(e)
            }
        )

# --- 核心接口 2: 补充参数/恢复任务 ---
@app.post("/tasks/resume")
def resume_task(req: ResumeRequest):
    """
    恢复任务并补充参数
    
    Args:
        req: 恢复请求，包含任务ID、补充参数和用户ID
        
    Returns:
        任务执行结果
    """
    try:
        # 1. 构造Thespian消息
        msg = ResumeTaskMessage(
            task_id=req.task_id,
            parameters=req.parameters,
            user_id=req.user_id
        )
        
        # 2. 发送给Actor并等待回复
        response = actor_system.ask(agent_actor_ref, msg, timeout=60)
        
        if response is None:
            raise HTTPException(status_code=504, detail="Agent processing timeout")
        
        # 3. 返回结果给前端
        return {
            "success": True,
            "data": response,
            "error": None
        }
    except Exception as e:
        logger.error(f"Error resuming task: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "data": None,
                "error": str(e)
            }
        )

# --- 健康检查端点 ---
@app.get("/health")
def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "service": "flora-api-server"
    }


# 工厂函数，用于创建API服务器实例
def create_api_server(config: dict = None) -> FastAPI:
    """
    创建API服务器实例
    
    Args:
        config: 服务器配置
        
    Returns:
        FastAPI应用实例
    """
    return app


# 如果直接运行此文件，则启动服务器
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Flora API Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8000, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    
    args = parser.parse_args()
    
    # 配置日志
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info(f"Starting API server on {args.host}:{args.port}")
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.debug
    )