# -*- coding: utf-8 -*-
"""
认证中间件
"""

import jwt
import hashlib
import secrets
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from src.utils.helpers.logger import main_logger
from src.core.exceptions.trading_exceptions import ValidationException
from config import system_config


class UserRole(Enum):
    """用户角色"""
    ADMIN = "admin"
    TRADER = "trader"
    VIEWER = "viewer"
    API_USER = "api_user"


class TokenType(Enum):
    """令牌类型"""
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"


@dataclass
class User:
    """用户信息"""
    user_id: str
    username: str
    email: str
    role: UserRole
    permissions: List[str]
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "role": self.role.value,
            "permissions": self.permissions,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "is_active": self.is_active
        }


@dataclass
class Token:
    """令牌信息"""
    token: str
    token_type: TokenType
    user_id: str
    expires_at: datetime
    permissions: List[str]
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        return datetime.utcnow() > self.expires_at
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "token": self.token,
            "token_type": self.token_type.value,
            "user_id": self.user_id,
            "expires_at": self.expires_at.isoformat(),
            "permissions": self.permissions
        }


class AuthManager:
    """认证管理器"""
    
    def __init__(self):
        self.secret_key = system_config.SECRET_KEY
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 7
        self.api_key_expire_days = 365
        
        # 用户存储 (生产环境应使用数据库)
        self.users: Dict[str, User] = {}
        self.tokens: Dict[str, Token] = {}
        self.api_keys: Dict[str, Token] = {}
        
        # 权限定义
        self.permissions = {
            UserRole.ADMIN: [
                "read", "write", "delete", "admin", 
                "trading", "system", "user_management"
            ],
            UserRole.TRADER: [
                "read", "write", "trading", "portfolio"
            ],
            UserRole.VIEWER: [
                "read"
            ],
            UserRole.API_USER: [
                "read", "write", "trading"
            ]
        }
        
        self._create_default_users()
        
    def _create_default_users(self):
        """创建默认用户"""
        # 创建管理员用户
        admin_user = User(
            user_id="admin_001",
            username="admin",
            email="admin@trading.ai",
            role=UserRole.ADMIN,
            permissions=self.permissions[UserRole.ADMIN],
            created_at=datetime.utcnow()
        )
        
        self.users[admin_user.user_id] = admin_user
        
        # 创建交易员用户
        trader_user = User(
            user_id="trader_001",
            username="trader",
            email="trader@trading.ai",
            role=UserRole.TRADER,
            permissions=self.permissions[UserRole.TRADER],
            created_at=datetime.utcnow()
        )
        
        self.users[trader_user.user_id] = trader_user
        
        main_logger.info("默认用户创建完成")
        
    def hash_password(self, password: str) -> str:
        """哈希密码"""
        return hashlib.sha256(password.encode()).hexdigest()
        
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """验证密码"""
        return self.hash_password(password) == hashed_password
        
    def create_access_token(self, user: User) -> str:
        """创建访问令牌"""
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            "user_id": user.user_id,
            "username": user.username,
            "role": user.role.value,
            "permissions": user.permissions,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": TokenType.ACCESS.value
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        # 存储令牌
        token_obj = Token(
            token=token,
            token_type=TokenType.ACCESS,
            user_id=user.user_id,
            expires_at=expire,
            permissions=user.permissions
        )
        
        self.tokens[token] = token_obj
        
        return token
        
    def create_refresh_token(self, user: User) -> str:
        """创建刷新令牌"""
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        
        payload = {
            "user_id": user.user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": TokenType.REFRESH.value
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        # 存储令牌
        token_obj = Token(
            token=token,
            token_type=TokenType.REFRESH,
            user_id=user.user_id,
            expires_at=expire,
            permissions=user.permissions
        )
        
        self.tokens[token] = token_obj
        
        return token
        
    def create_api_key(self, user: User) -> str:
        """创建API密钥"""
        # 生成API密钥
        api_key = f"ak_{secrets.token_urlsafe(32)}"
        
        expire = datetime.utcnow() + timedelta(days=self.api_key_expire_days)
        
        # 存储API密钥
        token_obj = Token(
            token=api_key,
            token_type=TokenType.API_KEY,
            user_id=user.user_id,
            expires_at=expire,
            permissions=user.permissions
        )
        
        self.api_keys[api_key] = token_obj
        
        return api_key
        
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证令牌"""
        try:
            # 检查是否是API密钥
            if token.startswith("ak_"):
                return self._verify_api_key(token)
                
            # 解码JWT令牌
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # 检查令牌是否在存储中
            if token not in self.tokens:
                return None
                
            token_obj = self.tokens[token]
            
            # 检查是否过期
            if token_obj.is_expired():
                del self.tokens[token]
                return None
                
            return payload
            
        except jwt.ExpiredSignatureError:
            # 令牌过期
            if token in self.tokens:
                del self.tokens[token]
            return None
        except jwt.InvalidTokenError:
            # 无效令牌
            return None
            
    def _verify_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """验证API密钥"""
        if api_key not in self.api_keys:
            return None
            
        token_obj = self.api_keys[api_key]
        
        # 检查是否过期
        if token_obj.is_expired():
            del self.api_keys[api_key]
            return None
            
        # 获取用户信息
        user = self.users.get(token_obj.user_id)
        if not user or not user.is_active:
            return None
            
        return {
            "user_id": user.user_id,
            "username": user.username,
            "role": user.role.value,
            "permissions": user.permissions,
            "type": TokenType.API_KEY.value
        }
        
    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """刷新访问令牌"""
        payload = self.verify_token(refresh_token)
        
        if not payload or payload.get("type") != TokenType.REFRESH.value:
            return None
            
        user = self.users.get(payload["user_id"])
        if not user or not user.is_active:
            return None
            
        # 创建新的访问令牌
        return self.create_access_token(user)
        
    def revoke_token(self, token: str) -> bool:
        """撤销令牌"""
        if token in self.tokens:
            del self.tokens[token]
            return True
        elif token in self.api_keys:
            del self.api_keys[token]
            return True
        return False
        
    def check_permission(self, user_permissions: List[str], required_permission: str) -> bool:
        """检查权限"""
        return required_permission in user_permissions or "admin" in user_permissions
        
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """根据ID获取用户"""
        return self.users.get(user_id)
        
    def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        for user in self.users.values():
            if user.username == username:
                return user
        return None
        
    def create_user(self, username: str, email: str, role: UserRole, 
                   password: str = None) -> User:
        """创建用户"""
        user_id = f"user_{secrets.token_urlsafe(8)}"
        
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            role=role,
            permissions=self.permissions[role],
            created_at=datetime.utcnow()
        )
        
        self.users[user_id] = user
        
        main_logger.info(f"创建用户: {username} ({role.value})")
        
        return user
        
    def update_user(self, user_id: str, **kwargs) -> bool:
        """更新用户"""
        if user_id not in self.users:
            return False
            
        user = self.users[user_id]
        
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
                
        main_logger.info(f"更新用户: {user.username}")
        
        return True
        
    def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        if user_id not in self.users:
            return False
            
        user = self.users[user_id]
        
        # 撤销所有令牌
        tokens_to_revoke = [
            token for token, token_obj in self.tokens.items() 
            if token_obj.user_id == user_id
        ]
        
        for token in tokens_to_revoke:
            self.revoke_token(token)
            
        # 撤销所有API密钥
        api_keys_to_revoke = [
            api_key for api_key, token_obj in self.api_keys.items() 
            if token_obj.user_id == user_id
        ]
        
        for api_key in api_keys_to_revoke:
            self.revoke_token(api_key)
            
        del self.users[user_id]
        
        main_logger.info(f"删除用户: {user.username}")
        
        return True
        
    def list_users(self) -> List[User]:
        """列出所有用户"""
        return list(self.users.values())
        
    def get_user_tokens(self, user_id: str) -> List[Token]:
        """获取用户的所有令牌"""
        tokens = []
        
        # 访问令牌
        for token_obj in self.tokens.values():
            if token_obj.user_id == user_id:
                tokens.append(token_obj)
                
        # API密钥
        for token_obj in self.api_keys.values():
            if token_obj.user_id == user_id:
                tokens.append(token_obj)
                
        return tokens
        
    def cleanup_expired_tokens(self) -> int:
        """清理过期令牌"""
        expired_tokens = [
            token for token, token_obj in self.tokens.items() 
            if token_obj.is_expired()
        ]
        
        for token in expired_tokens:
            del self.tokens[token]
            
        expired_api_keys = [
            api_key for api_key, token_obj in self.api_keys.items() 
            if token_obj.is_expired()
        ]
        
        for api_key in expired_api_keys:
            del self.api_keys[api_key]
            
        total_cleaned = len(expired_tokens) + len(expired_api_keys)
        
        if total_cleaned > 0:
            main_logger.info(f"清理了 {total_cleaned} 个过期令牌")
            
        return total_cleaned
        
    def get_auth_stats(self) -> Dict[str, Any]:
        """获取认证统计信息"""
        active_tokens = sum(1 for token_obj in self.tokens.values() if not token_obj.is_expired())
        active_api_keys = sum(1 for token_obj in self.api_keys.values() if not token_obj.is_expired())
        
        return {
            "total_users": len(self.users),
            "active_users": sum(1 for user in self.users.values() if user.is_active),
            "active_tokens": active_tokens,
            "active_api_keys": active_api_keys,
            "total_tokens": len(self.tokens),
            "total_api_keys": len(self.api_keys)
        }


# 权限装饰器
def require_permission(permission: str):
    """权限要求装饰器"""
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            # 从请求中获取用户信息
            user_info = getattr(request, 'user_info', None)
            
            if not user_info:
                raise ValidationException("未授权访问")
                
            permissions = user_info.get('permissions', [])
            
            if not auth_manager.check_permission(permissions, permission):
                raise ValidationException(f"缺少权限: {permission}")
                
            return func(request, *args, **kwargs)
            
        return wrapper
    return decorator


def require_role(role: UserRole):
    """角色要求装饰器"""
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            # 从请求中获取用户信息
            user_info = getattr(request, 'user_info', None)
            
            if not user_info:
                raise ValidationException("未授权访问")
                
            user_role = user_info.get('role')
            
            if user_role != role.value and user_role != UserRole.ADMIN.value:
                raise ValidationException(f"需要角色: {role.value}")
                
            return func(request, *args, **kwargs)
            
        return wrapper
    return decorator


# 全局认证管理器实例
auth_manager = AuthManager()