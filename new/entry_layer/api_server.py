# api_server.py
"""
Flora多智能体协作系统 - API服务器实现（基于FastAPI）

负责接收外部HTTP请求，提供RESTful API接口，集成认证中间件，并将请求转发给请求处理器
"""

import logging
import uvicorn
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional, Annotated

# 导入入口层其他组件
from new.entry_layer.auth_middleware import AuthMiddleware, get_current_auth_info
from new.entry_layer.request_handler import RequestHandler
from new.entry_layer.tenant_router import TenantRouter

logger = logging.getLogger(__name__)


class APIServer:
    """
    API服务器类，封装FastAPI应用，提供系统的HTTP接口
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化API服务器
        
        Args:
            config: 服务器配置字典
        """
        self.config = config or {}
        # 认证配置
        self.config.setdefault("auth", {
            "default_auth_type": "jwt",
            "jwt_secret_key": "default_secret_key",
            "jwt_algorithm": "HS256",
            "jwt_expiration_minutes": 30
        })
        self.app = FastAPI(
            title="Flora 多智能体协作系统 API",
            description="Flora系统的RESTful API接口",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        self._setup_app()
        
        # 初始化组件
        self.auth_middleware = AuthMiddleware(self.config.get('auth', {}))
        self.tenant_router = TenantRouter(self.config.get('tenant', {}))
        
        # 将认证中间件实例存储到app.state中
        self.app.state.auth_middleware = self.auth_middleware
        
        # 注册EventActor服务
        from new.events.event_actor import EventActor
        self.tenant_router.register_service_factory('event_actor', EventActor)
        
        self.request_handler = RequestHandler(
            tenant_router=self.tenant_router,
            config=self.config.get('handler', {})
        )
        
        self._register_routes()
    
    def _setup_app(self):
        """
        配置FastAPI应用
        """
        # 启用CORS支持
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # 在生产环境中应该设置具体的域名
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # 设置日志级别
        if self.config.get('debug', False):
            logging_level = logging.DEBUG
        else:
            logging_level = logging.INFO
        
        # 配置日志
        logging.basicConfig(
            level=logging_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # 全局异常处理
        @self.app.exception_handler(Exception)
        async def global_exception_handler(request: Request, exc: Exception):
            logger.error(f"Global exception: {str(exc)}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "data": None,
                    "error": "Internal server error"
                }
            )
    
    def _register_routes(self):
        """
        注册API路由
        """
        # 获取当前认证信息的依赖项
        AuthInfo = Annotated[Dict[str, Any], Depends(get_current_auth_info)]
        
        @self.app.get("/health")
        async def health_check():
            """健康检查端点"""
            return {
                "status": "healthy",
                "service": "flora-api-server"
            }
        
        # API v1路由组
        @self.app.post("/api/v1/task")
        async def create_task(
            request: Request,
            data: Dict[str, Any],
            auth_info: AuthInfo
        ):
            """创建新任务"""
            return await self._handle_request(
                request=request,
                operation="create_task",
                data=data,
                auth_info=auth_info
            )

        @self.app.post("/api/v1/task/with-comment")
        async def create_task_and_comment(
            request: Request,
            data: Dict[str, Any],
            auth_info: AuthInfo
        ):
            """创建新任务并追加评论"""
            return await self._handle_request(
                request=request,
                operation="create_task_and_comment",
                data=data,
                auth_info=auth_info
            )
        
        @self.app.get("/api/v1/task/{task_id}")
        async def get_task(
            request: Request,
            task_id: str,
            auth_info: AuthInfo
        ):
            """获取任务状态"""
            return await self._handle_request(
                request=request,
                operation="get_task",
                auth_info=auth_info,
                task_id=task_id
            )
        
        @self.app.put("/api/v1/task/{task_id}")
        async def update_task(
            request: Request,
            task_id: str,
            data: Dict[str, Any],
            auth_info: AuthInfo
        ):
            """更新任务"""
            return await self._handle_request(
                request=request,
                operation="update_task",
                data=data,
                auth_info=auth_info,
                task_id=task_id
            )
        
        @self.app.delete("/api/v1/task/{task_id}")
        async def delete_task(
            request: Request,
            task_id: str,
            auth_info: AuthInfo
        ):
            """删除任务"""
            return await self._handle_request(
                request=request,
                operation="delete_task",
                auth_info=auth_info,
                task_id=task_id
            )
        
        @self.app.post("/api/v1/task/{task_id}/comment")
        async def add_task_comment(
            request: Request,
            task_id: str,
            data: Dict[str, Any],
            auth_info: AuthInfo
        ):
            """为任务追加评论"""
            return await self._handle_request(
                request=request,
                operation="add_task_comment",
                data=data,
                auth_info=auth_info,
                task_id=task_id
            )
        
        @self.app.get("/api/v1/task/{task_id}/current")
        async def get_task_current_execution(
            request: Request,
            task_id: str,
            auth_info: AuthInfo
        ):
            """获取任务当前执行内容"""
            return await self._handle_request(
                request=request,
                operation="get_task_current_execution",
                auth_info=auth_info,
                task_id=task_id
            )
        
        @self.app.get("/api/v1/task/{task_id}/plan")
        async def get_task_plan(
            request: Request,
            task_id: str,
            auth_info: AuthInfo
        ):
            """获取任务计划执行的n项内容"""
            return await self._handle_request(
                request=request,
                operation="get_task_plan",
                auth_info=auth_info,
                task_id=task_id
            )
        
        @self.app.get("/api/v1/task/{task_id}/people")
        async def get_task_people(
            request: Request,
            task_id: str,
            auth_info: AuthInfo
        ):
            """获取任务下人员的情况"""
            return await self._handle_request(
                request=request,
                operation="get_task_people",
                auth_info=auth_info,
                task_id=task_id
            )
        
        @self.app.get("/api/v1/task/{task_id}/leaf-agents")
        async def get_task_leaf_agents(
            request: Request,
            task_id: str,
            auth_info: AuthInfo
        ):
            """获取任务下各个叶子智能体执行情况"""
            return await self._handle_request(
                request=request,
                operation="get_task_leaf_agents",
                auth_info=auth_info,
                task_id=task_id
            )
        
        @self.app.get("/api/v1/task/{task_id}/execution-path")
        async def get_task_execution_path(
            request: Request,
            task_id: str,
            auth_info: AuthInfo
        ):
            """获取任务整体执行路径"""
            return await self._handle_request(
                request=request,
                operation="get_task_execution_path",
                auth_info=auth_info,
                task_id=task_id
            )
        
        @self.app.get("/api/v1/task/{task_id}/progress")
        async def get_task_progress(
            request: Request,
            task_id: str,
            auth_info: AuthInfo
        ):
            """获取任务进度详情"""
            return await self._handle_request(
                request=request,
                operation="get_task_progress",
                auth_info=auth_info,
                task_id=task_id
            )
        
        @self.app.get("/api/v1/agent/{agent_id}")
        async def get_agent(
            request: Request,
            agent_id: str,
            auth_info: AuthInfo
        ):
            """获取智能体信息"""
            return await self._handle_request(
                request=request,
                operation="get_agent",
                auth_info=auth_info,
                agent_id=agent_id
            )
    
    async def _handle_request(
        self,
        request: Request,
        operation: str,
        auth_info: Dict[str, Any],
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        统一请求处理入口
        
        Args:
            request: FastAPI请求对象
            operation: 操作类型
            auth_info: 认证信息
            data: 请求数据
            **kwargs: 额外参数
            
        Returns:
            处理结果
        """
        try:
            # 构建请求上下文
            context = {
                'tenant_id': auth_info.get('tenant_id'),
                'user_id': auth_info.get('user_id'),
                'request_id': request.headers.get('X-Request-ID'),
                'client_ip': request.client.host
            }
            
            # 调用请求处理器
            result = await self.request_handler.handle(
                operation=operation,
                data=data or {},
                context=context,
                **kwargs
            )
            
            # 返回成功响应
            return {
                "success": True,
                "data": result,
                "error": None
            }
            
        except HTTPException:
            # 重新抛出HTTPException，让FastAPI处理
            raise
        except Exception as e:
            logger.error(f"Request handling error: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "data": None,
                    "error": str(e)
                }
            )
    
    def run(self, host: str = '0.0.0.0', port: int = 8000):
        """
        启动API服务器
        
        Args:
            host: 主机地址
            port: 端口号
        """
        logger.info(f"Starting API server on {host}:{port}")
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            reload=self.config.get('debug', False)
        )


# 工厂函数，用于创建API服务器实例
def create_api_server(config: Optional[Dict[str, Any]] = None) -> FastAPI:
    """
    创建API服务器实例
    
    Args:
        config: 服务器配置
        
    Returns:
        FastAPI应用实例
    """
    api_server = APIServer(config)
    return api_server.app


# 如果直接运行此文件，则启动服务器
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Flora API Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8000, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    
    args = parser.parse_args()
    
    config = {
        'debug': args.debug
    }
    
    server = create_api_server(config)
    server.run(host=args.host, port=args.port)
