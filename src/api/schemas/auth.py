"""
认证相关数据模式
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    """用户角色枚举"""
    ADMIN = "admin"
    TRADER = "trader"
    VIEWER = "viewer"


class UserStatus(str, Enum):
    """用户状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class LoginRequest(BaseModel):
    """登录请求模型"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    remember_me: bool = Field(default=False, description="记住我")
    
    @validator('username')
    def validate_username(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('用户名只能包含字母、数字、下划线和横线')
        return v.lower()


class LoginResponse(BaseModel):
    """登录响应模型"""
    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间（秒）")
    user_info: Dict[str, Any] = Field(..., description="用户信息")


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求模型"""
    refresh_token: str = Field(..., description="刷新令牌")


class UserInfo(BaseModel):
    """用户信息模型"""
    id: str = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    email: Optional[str] = Field(None, description="邮箱")
    full_name: Optional[str] = Field(None, description="全名")
    role: UserRole = Field(..., description="用户角色")
    status: UserStatus = Field(..., description="用户状态")
    permissions: List[str] = Field(default_factory=list, description="权限列表")
    last_login: Optional[datetime] = Field(None, description="最后登录时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class CreateUserRequest(BaseModel):
    """创建用户请求模型"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    email: Optional[str] = Field(None, description="邮箱")
    full_name: Optional[str] = Field(None, description="全名")
    role: UserRole = Field(..., description="用户角色")
    permissions: List[str] = Field(default_factory=list, description="权限列表")
    
    @validator('username')
    def validate_username(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('用户名只能包含字母、数字、下划线和横线')
        return v.lower()
    
    @validator('email')
    def validate_email(cls, v):
        if v and '@' not in v:
            raise ValueError('邮箱格式不正确')
        return v


class UpdateUserRequest(BaseModel):
    """更新用户请求模型"""
    email: Optional[str] = Field(None, description="邮箱")
    full_name: Optional[str] = Field(None, description="全名")
    role: Optional[UserRole] = Field(None, description="用户角色")
    status: Optional[UserStatus] = Field(None, description="用户状态")
    permissions: Optional[List[str]] = Field(None, description="权限列表")
    
    @validator('email')
    def validate_email(cls, v):
        if v and '@' not in v:
            raise ValueError('邮箱格式不正确')
        return v


class ChangePasswordRequest(BaseModel):
    """修改密码请求模型"""
    current_password: str = Field(..., description="当前密码")
    new_password: str = Field(..., min_length=6, max_length=128, description="新密码")
    confirm_password: str = Field(..., description="确认密码")
    
    @validator('confirm_password')
    def validate_passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('密码确认不匹配')
        return v


class PermissionInfo(BaseModel):
    """权限信息模型"""
    name: str = Field(..., description="权限名称")
    description: str = Field(..., description="权限描述")
    category: str = Field(..., description="权限分类")


class SessionInfo(BaseModel):
    """会话信息模型"""
    session_id: str = Field(..., description="会话ID")
    user_id: str = Field(..., description="用户ID")
    ip_address: str = Field(..., description="IP地址")
    user_agent: str = Field(..., description="用户代理")
    created_at: datetime = Field(..., description="创建时间")
    last_activity: datetime = Field(..., description="最后活动时间")
    expires_at: datetime = Field(..., description="过期时间")
    is_active: bool = Field(..., description="是否活跃")


class ApiKeyInfo(BaseModel):
    """API密钥信息模型"""
    key_id: str = Field(..., description="密钥ID")
    name: str = Field(..., description="密钥名称")
    key_prefix: str = Field(..., description="密钥前缀")
    permissions: List[str] = Field(..., description="权限列表")
    created_at: datetime = Field(..., description="创建时间")
    last_used: Optional[datetime] = Field(None, description="最后使用时间")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    is_active: bool = Field(..., description="是否活跃")


class CreateApiKeyRequest(BaseModel):
    """创建API密钥请求模型"""
    name: str = Field(..., min_length=1, max_length=100, description="密钥名称")
    permissions: List[str] = Field(..., description="权限列表")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    
    @validator('expires_at')
    def validate_expires_at(cls, v):
        if v and v <= datetime.now():
            raise ValueError('过期时间必须在未来')
        return v


class ApiKeyResponse(BaseModel):
    """API密钥响应模型"""
    key_id: str = Field(..., description="密钥ID")
    api_key: str = Field(..., description="API密钥")
    key_info: ApiKeyInfo = Field(..., description="密钥信息")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }