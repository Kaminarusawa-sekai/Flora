# main.py
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from typing import Dict
import asyncio
import logging

from optimization.engine import OptimizationEngine
from optimization.schemas import OptimizationConfig, OptimizationStatus
from config import settings

# 配置日志
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

# 全局优化引擎实例
engine: OptimizationEngine

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global engine
    logger.info("Initializing Optimization Engine...")
    engine = OptimizationEngine()
    yield
    logger.info("Shutting down Optimization Engine...")

app = FastAPI(lifespan=lifespan, title="Auto Optimization Platform")

@app.post("/optimize", status_code=202)
async def start_optimization(config: OptimizationConfig):
    """启动一个新的优化任务"""
    try:
        await engine.create_study(config)
        # 在后台运行优化
        asyncio.create_task(engine.run_optimization(config.study_name))
        return {"message": f"Optimization started for {config.study_name}", "study_name": config.study_name}
    except Exception as e:
        logger.error(f"Failed to start optimization: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{study_name}", response_model=OptimizationStatus)
async def get_optimization_status(study_name: str):
    """获取优化任务状态"""
    try:
        status = await engine.get_status(study_name)
        if "error" in status:
            raise HTTPException(status_code=404, detail=status["error"])
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Auto Optimization Platform is running!", "docs": "/docs"}

# --- 可选：接收执行器的回调 ---
# @app.post("/callback/feedback")
# async def receive_feedback(feedback: FeedbackData):
#     """接收来自执行器的实时反馈推送"""
#     # 可以在这里处理实时反馈，更新内部状态或用于更复杂的早停逻辑
#     logger.info(f"Received feedback: {feedback}")
#     return {"status": "received"}