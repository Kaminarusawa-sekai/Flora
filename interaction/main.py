#!/usr/bin/env python3
"""主入口文件"""
import os
import sys
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# 从external目录导入API路由
from interaction.external import app as api_app

# 创建主应用
app = FastAPI(
    title="AI任务管理API",
    description="用于管理AI任务的RESTful API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载API路由
app.mount("/v1", api_app)


if __name__ == "__main__":
    """启动FastAPI服务"""
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
