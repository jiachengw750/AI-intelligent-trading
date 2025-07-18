"""
认证中间件
"""
import jwt
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from passlib.hash import bcrypt
import secrets
import hashlib
from dataclasses import dataclass
from enum import Enum


class TokenType(str, Enum):
    """令牌类型枚举"""
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"


@dataclass
class TokenPayload:
    """令牌载荷"""
    user_id: str
    username: str
    role: str
    permissions: List[str]
    token_type: TokenType
    exp: int
    iat: int
    jti: str


class AuthConfig:
    """认证配置"""
    SECRET_KEY = "your-secret-key-here"  # 在生产环境中应使用环境变量
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    REFRESH_TOKEN_EXPIRE_DAYS = 30
    PASSWORD_RESET_EXPIRE_MINUTES = 15
    API_KEY_EXPIRE_DAYS = 365


class PasswordManager:
    """密码管理器"""
    
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    def hash_password(self, password: str) -> str:
        """哈希密码"""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def generate_reset_token(self, user_id: str) -> str:
        """生成重置密码令牌"""
        payload = {
            "user_id": user_id,
            "type": "password_reset",
            "exp": datetime.utcnow() + timedelta(minutes=AuthConfig.PASSWORD_RESET_EXPIRE_MINUTES)
        }
        return jwt.encode(payload, AuthConfig.SECRET_KEY, algorithm=AuthConfig.ALGORITHM)
    
    def verify_reset_token(self, token: str) -> Optional[str]:
        """验证重置密码令牌"""
        try:
            payload = jwt.decode(token, AuthConfig.SECRET_KEY, algorithms=[AuthConfig.ALGORITHM])
            if payload.get("type") != "password_reset":
                return None
            return payload.get("user_id")
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None


class TokenManager:
    """令牌管理器"""
    
    def __init__(self):
        self.active_tokens: Dict[str, Dict[str, Any]] = {}
        self.blacklisted_tokens: set = set()
    
    def create_access_token(self, user_id: str, username: str, role: str, permissions: List[str]) -> str:
        """创建访问令牌"""
        now = datetime.utcnow()
        exp = now + timedelta(minutes=AuthConfig.ACCESS_TOKEN_EXPIRE_MINUTES)
        jti = secrets.token_hex(16)
        
        payload = {
            "user_id": user_id,
            "username": username,
            "role": role,
            "permissions": permissions,
            "token_type": TokenType.ACCESS,
            "exp": int(exp.timestamp()),
            "iat": int(now.timestamp()),
            "jti": jti
        }
        
        token = jwt.encode(payload, AuthConfig.SECRET_KEY, algorithm=AuthConfig.ALGORITHM)
        
        # 存储活跃令牌
        self.active_tokens[jti] = {
            "user_id": user_id,
            "token_type": TokenType.ACCESS,
            "created_at": now,
            "expires_at": exp
        }
        
        return token
    
    def create_refresh_token(self, user_id: str, username: str) -> str:
        """创建刷新令牌"""
        now = datetime.utcnow()
        exp = now + timedelta(days=AuthConfig.REFRESH_TOKEN_EXPIRE_DAYS)
        jti = secrets.token_hex(16)
        
        payload = {
            "user_id": user_id,
            "username": username,
            "token_type": TokenType.REFRESH,
            "exp": int(exp.timestamp()),
            "iat": int(now.timestamp()),
            "jti": jti
        }
        
        token = jwt.encode(payload, AuthConfig.SECRET_KEY, algorithm=AuthConfig.ALGORITHM)
        
        # 存储活跃令牌
        self.active_tokens[jti] = {
            "user_id": user_id,
            "token_type": TokenType.REFRESH,
            "created_at": now,
            "expires_at": exp
        }
        
        return token
    
    def verify_token(self, token: str) -> Optional[TokenPayload]:
        """验证令牌"""
        try:
            payload = jwt.decode(token, AuthConfig.SECRET_KEY, algorithms=[AuthConfig.ALGORITHM])
            
            # 检查令牌是否在黑名单中
            jti = payload.get("jti")
            if jti in self.blacklisted_tokens:
                return None
            
            # 检查令牌是否存在于活跃令牌列表中
            if jti not in self.active_tokens:
                return None
            
            return TokenPayload(
                user_id=payload.get("user_id"),
                username=payload.get("username"),
                role=payload.get("role"),
                permissions=payload.get("permissions", []),
                token_type=payload.get("token_type"),
                exp=payload.get("exp"),
                iat=payload.get("iat"),
                jti=jti
            )
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def revoke_token(self, token: str) -> bool:
        """撤销令牌"""
        try:
            payload = jwt.decode(token, AuthConfig.SECRET_KEY, algorithms=[AuthConfig.ALGORITHM])
            jti = payload.get("jti")
            
            if jti:
                self.blacklisted_tokens.add(jti)
                if jti in self.active_tokens:
                    del self.active_tokens[jti]
                return True
            return False
        except jwt.InvalidTokenError:
            return False
    
    def revoke_all_user_tokens(self, user_id: str) -> int:
        """撤销用户所有令牌"""
        count = 0
        tokens_to_remove = []
        
        for jti, token_info in self.active_tokens.items():
            if token_info["user_id"] == user_id:
                self.blacklisted_tokens.add(jti)
                tokens_to_remove.append(jti)
                count += 1
        
        for jti in tokens_to_remove:
            del self.active_tokens[jti]
        
        return count
    
    def cleanup_expired_tokens(self):
        """清理过期令牌"""
        now = datetime.utcnow()
        expired_tokens = []
        
        for jti, token_info in self.active_tokens.items():
            if token_info["expires_at"] < now:
                expired_tokens.append(jti)
        
        for jti in expired_tokens:
            del self.active_tokens[jti]
            # 过期的令牌也不需要保留在黑名单中
            self.blacklisted_tokens.discard(jti)


class ApiKeyManager:
    """API密钥管理器"""
    
    def __init__(self):
        self.api_keys: Dict[str, Dict[str, Any]] = {}
    
    def generate_api_key(self, user_id: str, name: str, permissions: List[str], 
                        expires_at: Optional[datetime] = None) -> tuple[str, str]:
        """生成API密钥"""
        key_id = secrets.token_hex(16)
        api_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        if expires_at is None:
            expires_at = datetime.utcnow() + timedelta(days=AuthConfig.API_KEY_EXPIRE_DAYS)
        
        self.api_keys[key_id] = {
            "user_id": user_id,
            "name": name,
            "key_hash": key_hash,
            "permissions": permissions,
            "created_at": datetime.utcnow(),
            "expires_at": expires_at,
            "last_used": None,
            "is_active": True
        }
        
        return key_id, api_key
    
    def verify_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """验证API密钥"""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        for key_id, key_info in self.api_keys.items():
            if (key_info["key_hash"] == key_hash and 
                key_info["is_active"] and 
                key_info["expires_at"] > datetime.utcnow()):
                
                # 更新最后使用时间
                key_info["last_used"] = datetime.utcnow()
                
                return {
                    "key_id": key_id,
                    "user_id": key_info["user_id"],
                    "permissions": key_info["permissions"],
                    "name": key_info["name"]
                }
        
        return None
    
    def revoke_api_key(self, key_id: str) -> bool:
        """撤销API密钥"""
        if key_id in self.api_keys:
            self.api_keys[key_id]["is_active"] = False
            return True
        return False
    
    def get_user_api_keys(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的API密钥"""
        keys = []
        for key_id, key_info in self.api_keys.items():
            if key_info["user_id"] == user_id:
                keys.append({
                    "key_id": key_id,
                    "name": key_info["name"],
                    "permissions": key_info["permissions"],
                    "created_at": key_info["created_at"],
                    "expires_at": key_info["expires_at"],
                    "last_used": key_info["last_used"],
                    "is_active": key_info["is_active"]
                })
        return keys


class AuthManager:
    """认证管理器"""
    
    def __init__(self):
        self.password_manager = PasswordManager()
        self.token_manager = TokenManager()
        self.api_key_manager = ApiKeyManager()
        self.security = HTTPBearer()
    
    async def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
        """获取当前用户"""
        token = credentials.credentials
        
        # 首先尝试作为访问令牌验证
        token_payload = self.token_manager.verify_token(token)
        if token_payload and token_payload.token_type == TokenType.ACCESS:
            return {
                "user_id": token_payload.user_id,
                "username": token_payload.username,
                "role": token_payload.role,
                "permissions": token_payload.permissions,
                "auth_type": "token"
            }
        
        # 尝试作为API密钥验证
        api_key_info = self.api_key_manager.verify_api_key(token)
        if api_key_info:
            return {
                "user_id": api_key_info["user_id"],
                "username": None,
                "role": None,
                "permissions": api_key_info["permissions"],
                "auth_type": "api_key",
                "api_key_name": api_key_info["name"]
            }
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    def require_permission(self, permission: str):
        """权限依赖装饰器"""
        async def permission_checker(current_user: dict = Depends(self.get_current_user)):
            if permission not in current_user.get("permissions", []):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission '{permission}' required"
                )
            return current_user
        return permission_checker
    
    def require_role(self, role: str):
        """角色依赖装饰器"""
        async def role_checker(current_user: dict = Depends(self.get_current_user)):
            if current_user.get("role") != role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role '{role}' required"
                )
            return current_user
        return role_checker
    
    def require_permissions(self, permissions: List[str]):
        """多权限依赖装饰器"""
        async def permissions_checker(current_user: dict = Depends(self.get_current_user)):
            user_permissions = current_user.get("permissions", [])
            missing_permissions = [p for p in permissions if p not in user_permissions]
            
            if missing_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing permissions: {', '.join(missing_permissions)}"
                )
            return current_user
        return permissions_checker


# 全局认证管理器实例
auth_manager = AuthManager()


# 便捷的依赖函数
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    """获取当前用户的便捷函数"""
    return await auth_manager.get_current_user(credentials)


def require_permission(permission: str):
    """权限要求装饰器"""
    return auth_manager.require_permission(permission)


def require_role(role: str):
    """角色要求装饰器"""
    return auth_manager.require_role(role)


def require_permissions(permissions: List[str]):
    """多权限要求装饰器"""
    return auth_manager.require_permissions(permissions)


# 权限常量
class Permissions:
    """权限常量"""
    # 交易权限
    TRADING_READ = "trading:read"
    TRADING_CREATE = "trading:create"
    TRADING_UPDATE = "trading:update"
    TRADING_DELETE = "trading:delete"
    
    # 投资组合权限
    PORTFOLIO_READ = "portfolio:read"
    PORTFOLIO_CREATE = "portfolio:create"
    PORTFOLIO_UPDATE = "portfolio:update"
    PORTFOLIO_DELETE = "portfolio:delete"
    
    # 风险管理权限
    RISK_READ = "risk:read"
    RISK_CREATE = "risk:create"
    RISK_UPDATE = "risk:update"
    RISK_DELETE = "risk:delete"
    
    # 监控权限
    MONITORING_READ = "monitoring:read"
    MONITORING_CREATE = "monitoring:create"
    MONITORING_UPDATE = "monitoring:update"
    MONITORING_DELETE = "monitoring:delete"
    
    # 用户管理权限
    USER_READ = "user:read"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    
    # 系统管理权限
    SYSTEM_READ = "system:read"
    SYSTEM_UPDATE = "system:update"
    SYSTEM_DELETE = "system:delete"


# 角色权限映射
ROLE_PERMISSIONS = {
    "admin": [
        Permissions.TRADING_READ, Permissions.TRADING_CREATE, Permissions.TRADING_UPDATE, Permissions.TRADING_DELETE,
        Permissions.PORTFOLIO_READ, Permissions.PORTFOLIO_CREATE, Permissions.PORTFOLIO_UPDATE, Permissions.PORTFOLIO_DELETE,
        Permissions.RISK_READ, Permissions.RISK_CREATE, Permissions.RISK_UPDATE, Permissions.RISK_DELETE,
        Permissions.MONITORING_READ, Permissions.MONITORING_CREATE, Permissions.MONITORING_UPDATE, Permissions.MONITORING_DELETE,
        Permissions.USER_READ, Permissions.USER_CREATE, Permissions.USER_UPDATE, Permissions.USER_DELETE,
        Permissions.SYSTEM_READ, Permissions.SYSTEM_UPDATE, Permissions.SYSTEM_DELETE,
    ],
    "trader": [
        Permissions.TRADING_READ, Permissions.TRADING_CREATE, Permissions.TRADING_UPDATE,
        Permissions.PORTFOLIO_READ, Permissions.PORTFOLIO_CREATE, Permissions.PORTFOLIO_UPDATE,
        Permissions.RISK_READ,
        Permissions.MONITORING_READ,
    ],
    "viewer": [
        Permissions.TRADING_READ,
        Permissions.PORTFOLIO_READ,
        Permissions.RISK_READ,
        Permissions.MONITORING_READ,
    ]
}