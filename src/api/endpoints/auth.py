"""
用户认证相关API端点
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from ..schemas import (
    BaseResponse,
    ErrorResponse,
    PaginationParams,
    PaginatedResponse,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    UserInfo,
    CreateUserRequest,
    UpdateUserRequest,
    ChangePasswordRequest,
    PermissionInfo,
    SessionInfo,
    ApiKeyInfo,
    CreateApiKeyRequest,
    ApiKeyResponse,
    UserRole,
    UserStatus
)
from ..middleware import (
    auth_manager,
    get_current_user,
    require_permission,
    require_role,
    Permissions,
    ROLE_PERMISSIONS
)


# 创建路由器
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(request: Request, login_request: LoginRequest):
    """用户登录"""
    try:
        # 模拟用户验证
        # 在实际应用中，这里应该验证用户名和密码
        if login_request.username == "admin" and login_request.password == "admin123":
            user_id = "user_1"
            username = login_request.username
            role = "admin"
            permissions = ROLE_PERMISSIONS.get(role, [])
            
            # 创建访问令牌和刷新令牌
            access_token = auth_manager.token_manager.create_access_token(
                user_id=user_id,
                username=username,
                role=role,
                permissions=permissions
            )
            
            refresh_token = auth_manager.token_manager.create_refresh_token(
                user_id=user_id,
                username=username
            )
            
            # 记录登录成功
            security_middleware = auth_manager  # 获取安全中间件实例
            if hasattr(security_middleware, 'handle_authentication_success'):
                security_middleware.handle_authentication_success(request, username)
            
            return LoginResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=30 * 60,  # 30分钟
                user_info={
                    "id": user_id,
                    "username": username,
                    "role": role,
                    "permissions": permissions
                }
            )
        else:
            # 记录登录失败
            security_middleware = auth_manager  # 获取安全中间件实例
            if hasattr(security_middleware, 'handle_authentication_failure'):
                security_middleware.handle_authentication_failure(request, login_request.username)
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登录失败: {str(e)}"
        )


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(refresh_request: RefreshTokenRequest):
    """刷新访问令牌"""
    try:
        # 验证刷新令牌
        token_payload = auth_manager.token_manager.verify_token(refresh_request.refresh_token)
        
        if not token_payload or token_payload.token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="刷新令牌无效"
            )
        
        # 创建新的访问令牌
        # 在实际应用中，这里应该从数据库获取用户信息
        user_id = token_payload.user_id
        username = token_payload.username
        role = "admin"  # 应该从数据库获取
        permissions = ROLE_PERMISSIONS.get(role, [])
        
        access_token = auth_manager.token_manager.create_access_token(
            user_id=user_id,
            username=username,
            role=role,
            permissions=permissions
        )
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_request.refresh_token,
            token_type="bearer",
            expires_in=30 * 60,
            user_info={
                "id": user_id,
                "username": username,
                "role": role,
                "permissions": permissions
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"刷新令牌失败: {str(e)}"
        )


@router.post("/logout", response_model=BaseResponse)
async def logout(current_user: dict = Depends(get_current_user)):
    """用户登出"""
    try:
        # 撤销所有用户令牌
        user_id = current_user["user_id"]
        revoked_count = auth_manager.token_manager.revoke_all_user_tokens(user_id)
        
        return BaseResponse(
            message="登出成功",
            data={"revoked_tokens": revoked_count}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登出失败: {str(e)}"
        )


@router.get("/me", response_model=BaseResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    try:
        # 模拟用户信息
        user_info = UserInfo(
            id=current_user["user_id"],
            username=current_user["username"] or "admin",
            email="admin@example.com",
            full_name="管理员",
            role=UserRole(current_user["role"]) if current_user["role"] else UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            permissions=current_user["permissions"],
            last_login=datetime.now() - timedelta(minutes=30),
            created_at=datetime.now() - timedelta(days=30),
            updated_at=datetime.now()
        )
        
        return BaseResponse(
            message="获取用户信息成功",
            data=user_info.dict()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取用户信息失败: {str(e)}"
        )


@router.put("/me", response_model=BaseResponse)
async def update_current_user(
    update_request: UpdateUserRequest,
    current_user: dict = Depends(get_current_user)
):
    """更新当前用户信息"""
    try:
        # 模拟更新用户信息
        return BaseResponse(
            message="更新用户信息成功",
            data={"user_id": current_user["user_id"], "status": "updated"}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"更新用户信息失败: {str(e)}"
        )


@router.post("/change-password", response_model=BaseResponse)
async def change_password(
    password_request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    """修改密码"""
    try:
        # 验证当前密码
        # 在实际应用中，这里应该验证当前密码
        if password_request.current_password != "admin123":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="当前密码错误"
            )
        
        # 模拟密码修改
        hashed_password = auth_manager.password_manager.hash_password(password_request.new_password)
        
        # 撤销所有用户令牌，强制重新登录
        user_id = current_user["user_id"]
        auth_manager.token_manager.revoke_all_user_tokens(user_id)
        
        return BaseResponse(
            message="密码修改成功，请重新登录",
            data={"user_id": user_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"修改密码失败: {str(e)}"
        )


@router.get("/users", response_model=PaginatedResponse)
async def get_users(
    role: Optional[UserRole] = None,
    status: Optional[UserStatus] = None,
    pagination: PaginationParams = Depends(),
    current_user: dict = Depends(require_permission(Permissions.USER_READ))
):
    """获取用户列表"""
    try:
        # 模拟用户列表
        users = []
        for i in range(pagination.page_size):
            user_id = f"user_{i + pagination.skip}"
            user = UserInfo(
                id=user_id,
                username=f"user_{i}",
                email=f"user_{i}@example.com",
                full_name=f"用户{i}",
                role=UserRole.TRADER if i % 2 == 0 else UserRole.VIEWER,
                status=UserStatus.ACTIVE,
                permissions=ROLE_PERMISSIONS.get("trader" if i % 2 == 0 else "viewer", []),
                last_login=datetime.now() - timedelta(minutes=i),
                created_at=datetime.now() - timedelta(days=i),
                updated_at=datetime.now() - timedelta(hours=i)
            )
            users.append(user.dict())
        
        response = PaginatedResponse(
            message="获取用户列表成功",
            data=users
        )
        response.set_pagination(
            total=100,  # 模拟总数
            page=pagination.page,
            page_size=pagination.page_size
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取用户列表失败: {str(e)}"
        )


@router.post("/users", response_model=BaseResponse)
async def create_user(
    user_request: CreateUserRequest,
    current_user: dict = Depends(require_permission(Permissions.USER_CREATE))
):
    """创建用户"""
    try:
        # 模拟创建用户
        user_id = f"user_{int(datetime.now().timestamp())}"
        
        # 哈希密码
        hashed_password = auth_manager.password_manager.hash_password(user_request.password)
        
        user = UserInfo(
            id=user_id,
            username=user_request.username,
            email=user_request.email,
            full_name=user_request.full_name,
            role=user_request.role,
            status=UserStatus.ACTIVE,
            permissions=user_request.permissions,
            last_login=None,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        return BaseResponse(
            message="创建用户成功",
            data=user.dict()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"创建用户失败: {str(e)}"
        )


@router.put("/users/{user_id}", response_model=BaseResponse)
async def update_user(
    user_id: str,
    user_request: UpdateUserRequest,
    current_user: dict = Depends(require_permission(Permissions.USER_UPDATE))
):
    """更新用户"""
    try:
        # 模拟更新用户
        return BaseResponse(
            message="更新用户成功",
            data={"user_id": user_id, "status": "updated"}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"更新用户失败: {str(e)}"
        )


@router.delete("/users/{user_id}", response_model=BaseResponse)
async def delete_user(
    user_id: str,
    current_user: dict = Depends(require_permission(Permissions.USER_DELETE))
):
    """删除用户"""
    try:
        # 撤销用户所有令牌
        auth_manager.token_manager.revoke_all_user_tokens(user_id)
        
        # 模拟删除用户
        return BaseResponse(
            message="删除用户成功",
            data={"user_id": user_id, "status": "deleted"}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"删除用户失败: {str(e)}"
        )


@router.get("/permissions", response_model=BaseResponse)
async def get_permissions(
    current_user: dict = Depends(require_permission(Permissions.USER_READ))
):
    """获取权限列表"""
    try:
        # 模拟权限列表
        permissions = [
            PermissionInfo(
                name=Permissions.TRADING_READ,
                description="查看交易信息",
                category="trading"
            ),
            PermissionInfo(
                name=Permissions.TRADING_CREATE,
                description="创建交易订单",
                category="trading"
            ),
            PermissionInfo(
                name=Permissions.PORTFOLIO_READ,
                description="查看投资组合",
                category="portfolio"
            ),
            PermissionInfo(
                name=Permissions.PORTFOLIO_CREATE,
                description="创建投资组合",
                category="portfolio"
            ),
            PermissionInfo(
                name=Permissions.RISK_READ,
                description="查看风险信息",
                category="risk"
            ),
            PermissionInfo(
                name=Permissions.MONITORING_READ,
                description="查看监控信息",
                category="monitoring"
            ),
            PermissionInfo(
                name=Permissions.USER_READ,
                description="查看用户信息",
                category="user"
            ),
            PermissionInfo(
                name=Permissions.USER_CREATE,
                description="创建用户",
                category="user"
            )
        ]
        
        return BaseResponse(
            message="获取权限列表成功",
            data=[perm.dict() for perm in permissions]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取权限列表失败: {str(e)}"
        )


@router.get("/sessions", response_model=PaginatedResponse)
async def get_sessions(
    pagination: PaginationParams = Depends(),
    current_user: dict = Depends(require_permission(Permissions.USER_READ))
):
    """获取会话列表"""
    try:
        # 模拟会话列表
        sessions = []
        for i in range(pagination.page_size):
            session_id = f"session_{i + pagination.skip}"
            session = SessionInfo(
                session_id=session_id,
                user_id=f"user_{i}",
                ip_address=f"192.168.1.{i + 1}",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                created_at=datetime.now() - timedelta(hours=i),
                last_activity=datetime.now() - timedelta(minutes=i),
                expires_at=datetime.now() + timedelta(hours=1),
                is_active=True
            )
            sessions.append(session.dict())
        
        response = PaginatedResponse(
            message="获取会话列表成功",
            data=sessions
        )
        response.set_pagination(
            total=50,  # 模拟总数
            page=pagination.page,
            page_size=pagination.page_size
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取会话列表失败: {str(e)}"
        )


@router.get("/api-keys", response_model=BaseResponse)
async def get_api_keys(
    current_user: dict = Depends(get_current_user)
):
    """获取API密钥列表"""
    try:
        # 获取用户的API密钥
        user_id = current_user["user_id"]
        api_keys = auth_manager.api_key_manager.get_user_api_keys(user_id)
        
        return BaseResponse(
            message="获取API密钥列表成功",
            data=api_keys
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取API密钥列表失败: {str(e)}"
        )


@router.post("/api-keys", response_model=BaseResponse)
async def create_api_key(
    api_key_request: CreateApiKeyRequest,
    current_user: dict = Depends(get_current_user)
):
    """创建API密钥"""
    try:
        # 创建API密钥
        user_id = current_user["user_id"]
        key_id, api_key = auth_manager.api_key_manager.generate_api_key(
            user_id=user_id,
            name=api_key_request.name,
            permissions=api_key_request.permissions,
            expires_at=api_key_request.expires_at
        )
        
        # 获取密钥信息
        key_info = ApiKeyInfo(
            key_id=key_id,
            name=api_key_request.name,
            key_prefix=api_key[:8] + "...",
            permissions=api_key_request.permissions,
            created_at=datetime.now(),
            last_used=None,
            expires_at=api_key_request.expires_at,
            is_active=True
        )
        
        response = ApiKeyResponse(
            key_id=key_id,
            api_key=api_key,
            key_info=key_info
        )
        
        return BaseResponse(
            message="创建API密钥成功",
            data=response.dict()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"创建API密钥失败: {str(e)}"
        )


@router.delete("/api-keys/{key_id}", response_model=BaseResponse)
async def revoke_api_key(
    key_id: str,
    current_user: dict = Depends(get_current_user)
):
    """撤销API密钥"""
    try:
        # 撤销API密钥
        success = auth_manager.api_key_manager.revoke_api_key(key_id)
        
        if success:
            return BaseResponse(
                message="撤销API密钥成功",
                data={"key_id": key_id, "status": "revoked"}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API密钥不存在"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"撤销API密钥失败: {str(e)}"
        )