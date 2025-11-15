from new.entry_layer.auth_middleware import create_auth_middleware

# 创建AuthMiddleware实例
auth_middleware = create_auth_middleware()

# 生成JWT令牌
token = auth_middleware.create_jwt_token(
    tenant_id="default",
    user_id="user123",
    username="testuser",
    roles=["admin", "user"]
)

print(f"Generated JWT Token: {token}")
