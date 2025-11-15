# auth_middleware.py
"""
Flora多智能体协作系统 - 认证中间件

负责请求的身份验证和授权，支持多种认证方式
"""

import logging
import os
from typing import Dict, Any, Optional, Union, Callable, List
from datetime import datetime, timedelta
from fastapi import HTTPException, status, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from functools import wraps

logger = logging.getLogger(__name__)

# 定义认证信息的上下文存储
_auth_context_storage = {}


class AuthMiddleware:
    """
    认证中间件类，提供身份验证和授权功能
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化认证中间件
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        
        # 认证方式映射
        # 格式: {auth_type: auth_handler}
        self._auth_handlers = {
            'api_key': self._authenticate_api_key,
            'jwt': self._authenticate_jwt,
            'basic': self._authenticate_basic
        }
        
        # JWT配置
        self.jwt_secret_key = self.config.get('jwt_secret_key', 'default_secret_key')
        self.jwt_algorithm = self.config.get('jwt_algorithm', 'HS256')
        self.jwt_expiration_minutes = self.config.get('jwt_expiration_minutes', 30)
        
        # API密钥配置
        self.api_keys = self.config.get('api_keys', {
            'test_key': {'tenant_id': 'default_tenant', 'user_id': 'system_user'}
        })
        
        # 默认认证方式
        self.default_auth_type = self.config.get('default_auth_type', 'api_key')
    
    def authenticate(self, func: Callable) -> Callable:
        """
        认证装饰器，用于Flask等传统框架
        
        Args:
            func: 被装饰的函数
            
        Returns:
            装饰后的函数
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 这里实现传统框架的认证逻辑
            # 在FastAPI中，我们主要使用依赖注入方式
            return func(*args, **kwargs)
        return wrapper
    
    async def verify_request(
        self,
        request: Request,
        auth_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        验证请求的认证信息
        
        Args:
            request: FastAPI请求对象
            auth_type: 认证方式，如果为None则使用默认方式
            
        Returns:
            认证信息字典
            
        Raises:
            HTTPException: 认证失败时抛出
        """
        # 使用指定的认证方式或默认认证方式
        auth_type = auth_type or self.default_auth_type
        
        # 检查认证方式是否支持
        if auth_type not in self._auth_handlers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": f"Unsupported authentication type: {auth_type}"
                }
            )
        
        # 获取认证处理器
        auth_handler = self._auth_handlers[auth_type]
        
        try:
            # 执行认证
            auth_info = await auth_handler(request)
            
            # 验证租户和用户权限
            await self._verify_permissions(auth_info)
            
            # 记录认证成功日志
            logger.info(
                f"Authentication successful | "
                f"Type: {auth_type} | "
                f"Tenant: {auth_info.get('tenant_id')} | "
                f"User: {auth_info.get('user_id')}"
            )
            
            # 存储认证信息到上下文
            request_id = request.headers.get('X-Request-ID', 'unknown')
            _auth_context_storage[request_id] = auth_info
            
            return auth_info
            
        except HTTPException:
            # 重新抛出HTTP异常
            raise
        except Exception as e:
            # 记录认证失败日志
            logger.error(f"Authentication failed: {str(e)}", exc_info=True)
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "success": False,
                    "error": "Authentication failed"
                },
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    async def _authenticate_api_key(
        self,
        request: Request
    ) -> Dict[str, Any]:
        """
        使用API密钥进行认证
        
        Args:
            request: FastAPI请求对象
            
        Returns:
            认证信息字典
            
        Raises:
            HTTPException: 认证失败时抛出
        """
        # 从请求头获取API密钥
        api_key = request.headers.get('X-API-Key')
        
        # 也支持从Authorization头获取
        if not api_key:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('ApiKey '):
                api_key = auth_header[7:]
        
        # 验证API密钥是否存在
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "success": False,
                    "error": "API key required"
                }
            )
        
        # 验证API密钥是否有效
        if api_key not in self.api_keys:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "success": False,
                    "error": "Invalid API key"
                }
            )
        
        # 返回认证信息
        auth_info = self.api_keys[api_key].copy()
        auth_info['auth_type'] = 'api_key'
        auth_info['api_key_id'] = api_key
        auth_info['authenticated_at'] = datetime.now().isoformat()
        
        return auth_info
    
    async def _authenticate_jwt(
        self,
        request: Request
    ) -> Dict[str, Any]:
        """
        使用JWT令牌进行认证
        
        Args:
            request: FastAPI请求对象
            
        Returns:
            认证信息字典
            
        Raises:
            HTTPException: 认证失败时抛出
        """
        # 从Authorization头获取JWT令牌
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "success": False,
                    "error": "Bearer token required"
                },
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token = auth_header[7:]
        
        try:
            # 解码JWT令牌
            payload = jwt.decode(
                token,
                self.jwt_secret_key,
                algorithms=[self.jwt_algorithm]
            )
            
            # 验证令牌是否过期
            if 'exp' in payload and datetime.now().timestamp() > payload['exp']:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "success": False,
                        "error": "Token has expired"
                    },
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # 提取认证信息
            auth_info = {
                'tenant_id': payload.get('tenant_id', 'default_tenant'),
                'user_id': payload.get('sub'),
                'username': payload.get('username'),
                'roles': payload.get('roles', []),
                'auth_type': 'jwt',
                'token_id': payload.get('jti'),
                'authenticated_at': datetime.now().isoformat()
            }
            
            return auth_info
            
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "success": False,
                    "error": "Invalid token"
                },
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    async def _authenticate_basic(
        self,
        request: Request
    ) -> Dict[str, Any]:
        """
        使用基本认证进行身份验证
        
        Args:
            request: FastAPI请求对象
            
        Returns:
            认证信息字典
            
        Raises:
            HTTPException: 认证失败时抛出
        """
        # 从Authorization头获取基本认证信息
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Basic '):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "success": False,
                    "error": "Basic authentication required"
                },
                headers={"WWW-Authenticate": "Basic"},
            )
        
        # 注意：这里只是模拟实现，实际应该解码和验证用户名密码
        # 为了开发和测试目的，这里返回模拟认证信息
        auth_info = {
            'tenant_id': 'default_tenant',
            'user_id': 'basic_user',
            'auth_type': 'basic',
            'authenticated_at': datetime.now().isoformat()
        }
        
        return auth_info
    
    async def _verify_permissions(
        self,
        auth_info: Dict[str, Any]
    ) -> None:
        """
        验证用户权限
        
        Args:
            auth_info: 认证信息字典
            
        Raises:
            HTTPException: 权限不足时抛出
        """
        # 这里可以实现更复杂的权限验证逻辑
        # 例如检查用户是否有权限访问特定租户的资源
        tenant_id = auth_info.get('tenant_id')
        user_id = auth_info.get('user_id')
        
        if not tenant_id or not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "success": False,
                    "error": "Invalid authentication information"
                }
            )
    
    def create_jwt_token(
        self,
        tenant_id: str,
        user_id: str,
        username: Optional[str] = None,
        roles: Optional[List[str]] = None,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        创建JWT令牌
        
        Args:
            tenant_id: 租户ID
            user_id: 用户ID
            username: 用户名
            roles: 用户角色列表
            additional_claims: 额外的声明
            
        Returns:
            JWT令牌字符串
        """
        # 创建令牌过期时间
        expire = datetime.now() + timedelta(minutes=self.jwt_expiration_minutes)
        
        # 创建令牌载荷
        payload = {
            "sub": user_id,
            "tenant_id": tenant_id,
            "username": username,
            "roles": roles or [],
            "exp": expire,
            "iat": datetime.now(),
            "jti": os.urandom(16).hex()  # 生成唯一标识符
        }
        
        # 添加额外声明
        if additional_claims:
            payload.update(additional_claims)
        
        # 生成JWT令牌
        token = jwt.encode(
            payload,
            self.jwt_secret_key,
            algorithm=self.jwt_algorithm
        )
        
        return token


# 创建安全方案
security = HTTPBearer()


async def get_current_auth_info(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    获取当前请求的认证信息
    作为FastAPI的依赖注入使用
    
    Args:
        request: FastAPI请求对象
        credentials: HTTP认证凭据
        
    Returns:
        认证信息字典
    """
    try:
        # 使用存储在app.state中的认证中间件实例
        auth_middleware = request.app.state.auth_middleware
        
        # 验证请求并获取认证信息
        auth_info = await auth_middleware.verify_request(request)
        
        return auth_info
        
    except HTTPException:
        # 对于开发和测试环境，允许使用默认认证信息
        # 在生产环境中应该移除这个逻辑
        import os
        if os.environ.get('FLORA_ENV') in ['development', 'test']:
            logger.warning("Using default authentication in development mode")
            return {
                'tenant_id': 'default_tenant',
                'user_id': 'system_user',
                'auth_type': 'default',
                'authenticated_at': datetime.now().isoformat()
            }
        else:
            raise


# 清理认证上下文的辅助函数
def cleanup_auth_context(request_id: str):
    """
    清理认证上下文
    
    Args:
        request_id: 请求ID
    """
    if request_id in _auth_context_storage:
        del _auth_context_storage[request_id]


# 工厂函数，用于创建认证中间件实例
def create_auth_middleware(config: Optional[Dict[str, Any]] = None) -> AuthMiddleware:
    """
    创建认证中间件实例
    
    Args:
        config: 配置字典
        
    Returns:
        AuthMiddleware实例
    """
    return AuthMiddleware(config=config)
