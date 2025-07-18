"""
安全中间件
"""
import re
import time
import hashlib
import hmac
import secrets
from typing import Dict, List, Optional, Set, Any
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from urllib.parse import urlparse
import json
import asyncio
from collections import defaultdict, deque


class SecurityConfig:
    """安全配置"""
    # CSRF设置
    CSRF_TOKEN_EXPIRE_MINUTES = 30
    CSRF_COOKIE_NAME = "csrf_token"
    CSRF_HEADER_NAME = "X-CSRF-Token"
    
    # CORS设置
    ALLOWED_ORIGINS = ["http://localhost:3000", "http://localhost:8000"]
    ALLOWED_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    ALLOWED_HEADERS = ["*"]
    EXPOSE_HEADERS = ["X-Total-Count", "X-RateLimit-*"]
    
    # 请求大小限制
    MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_HEADER_SIZE = 8 * 1024  # 8KB
    
    # 安全头设置
    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';"
    }
    
    # IP白名单（可选）
    IP_WHITELIST: Optional[List[str]] = None
    
    # 恶意请求检测
    MALICIOUS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"vbscript:",
        r"onload\s*=",
        r"onerror\s*=",
        r"onclick\s*=",
        r"union\s+select",
        r"drop\s+table",
        r"insert\s+into",
        r"delete\s+from",
        r"update\s+.*\s+set",
        r"\.\./",
        r"\.\.\\",
    ]


class CSRFProtection:
    """CSRF保护"""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.tokens: Dict[str, datetime] = {}
    
    def generate_token(self, session_id: str) -> str:
        """生成CSRF令牌"""
        # 清理过期令牌
        self.cleanup_expired_tokens()
        
        # 生成新令牌
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(minutes=SecurityConfig.CSRF_TOKEN_EXPIRE_MINUTES)
        
        # 创建签名
        message = f"{token}:{session_id}:{expires_at.timestamp()}"
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        signed_token = f"{token}:{signature}"
        self.tokens[signed_token] = expires_at
        
        return signed_token
    
    def verify_token(self, token: str, session_id: str) -> bool:
        """验证CSRF令牌"""
        if ":" not in token:
            return False
        
        try:
            token_part, signature = token.rsplit(":", 1)
            
            # 检查令牌是否存在且未过期
            if token not in self.tokens:
                return False
            
            if self.tokens[token] < datetime.utcnow():
                del self.tokens[token]
                return False
            
            # 验证签名
            expires_at = self.tokens[token]
            message = f"{token_part}:{session_id}:{expires_at.timestamp()}"
            expected_signature = hmac.new(
                self.secret_key.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception:
            return False
    
    def cleanup_expired_tokens(self):
        """清理过期令牌"""
        now = datetime.utcnow()
        expired_tokens = [token for token, expires_at in self.tokens.items() if expires_at < now]
        for token in expired_tokens:
            del self.tokens[token]


class RequestValidator:
    """请求验证器"""
    
    def __init__(self):
        self.malicious_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in SecurityConfig.MALICIOUS_PATTERNS]
    
    def validate_request_size(self, request: Request) -> bool:
        """验证请求大小"""
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                return size <= SecurityConfig.MAX_REQUEST_SIZE
            except ValueError:
                return False
        return True
    
    def validate_headers(self, request: Request) -> bool:
        """验证请求头"""
        # 检查请求头大小
        total_header_size = sum(len(k) + len(v) for k, v in request.headers.items())
        if total_header_size > SecurityConfig.MAX_HEADER_SIZE:
            return False
        
        # 检查恶意头
        for key, value in request.headers.items():
            if self.contains_malicious_content(f"{key}: {value}"):
                return False
        
        return True
    
    def validate_url(self, request: Request) -> bool:
        """验证URL"""
        url = str(request.url)
        path = request.url.path
        query = request.url.query
        
        # 检查路径遍历攻击
        if "../" in path or "..\\" in path:
            return False
        
        # 检查恶意内容
        if self.contains_malicious_content(url):
            return False
        
        if query and self.contains_malicious_content(query):
            return False
        
        return True
    
    def contains_malicious_content(self, content: str) -> bool:
        """检查是否包含恶意内容"""
        for pattern in self.malicious_patterns:
            if pattern.search(content):
                return True
        return False
    
    async def validate_json_body(self, request: Request) -> bool:
        """验证JSON请求体"""
        if request.headers.get("content-type", "").startswith("application/json"):
            try:
                body = await request.body()
                if body:
                    content = body.decode('utf-8')
                    if self.contains_malicious_content(content):
                        return False
                    
                    # 尝试解析JSON
                    json.loads(content)
                    
            except (UnicodeDecodeError, json.JSONDecodeError):
                return False
        
        return True


class IPFilter:
    """IP过滤器"""
    
    def __init__(self, whitelist: Optional[List[str]] = None, blacklist: Optional[List[str]] = None):
        self.whitelist = set(whitelist) if whitelist else None
        self.blacklist = set(blacklist) if blacklist else set()
        self.suspicious_ips: Dict[str, List[datetime]] = defaultdict(list)
    
    def get_client_ip(self, request: Request) -> str:
        """获取客户端IP"""
        # 检查代理头
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host
    
    def is_ip_allowed(self, ip: str) -> bool:
        """检查IP是否被允许"""
        # 检查黑名单
        if ip in self.blacklist:
            return False
        
        # 检查白名单
        if self.whitelist:
            return ip in self.whitelist
        
        return True
    
    def record_suspicious_activity(self, ip: str):
        """记录可疑活动"""
        now = datetime.utcnow()
        self.suspicious_ips[ip].append(now)
        
        # 清理1小时前的记录
        cutoff_time = now - timedelta(hours=1)
        self.suspicious_ips[ip] = [
            timestamp for timestamp in self.suspicious_ips[ip] 
            if timestamp > cutoff_time
        ]
    
    def is_ip_suspicious(self, ip: str, threshold: int = 10) -> bool:
        """检查IP是否可疑"""
        if ip not in self.suspicious_ips:
            return False
        
        return len(self.suspicious_ips[ip]) > threshold
    
    def block_ip(self, ip: str, duration_minutes: int = 60):
        """临时封锁IP"""
        unblock_time = datetime.utcnow() + timedelta(minutes=duration_minutes)
        self.blacklist.add(ip)
        
        # 设置自动解封（简单实现，生产环境可能需要更复杂的机制）
        asyncio.create_task(self._auto_unblock_ip(ip, duration_minutes * 60))
    
    async def _auto_unblock_ip(self, ip: str, delay_seconds: int):
        """自动解封IP"""
        await asyncio.sleep(delay_seconds)
        self.blacklist.discard(ip)


class BruteForceProtection:
    """暴力破解保护"""
    
    def __init__(self):
        self.failed_attempts: Dict[str, List[datetime]] = defaultdict(list)
        self.blocked_identifiers: Dict[str, datetime] = {}
    
    def record_failed_attempt(self, identifier: str):
        """记录失败尝试"""
        now = datetime.utcnow()
        self.failed_attempts[identifier].append(now)
        
        # 清理1小时前的记录
        cutoff_time = now - timedelta(hours=1)
        self.failed_attempts[identifier] = [
            timestamp for timestamp in self.failed_attempts[identifier] 
            if timestamp > cutoff_time
        ]
    
    def is_blocked(self, identifier: str) -> bool:
        """检查是否被封锁"""
        if identifier in self.blocked_identifiers:
            unblock_time = self.blocked_identifiers[identifier]
            if datetime.utcnow() < unblock_time:
                return True
            else:
                del self.blocked_identifiers[identifier]
        
        return False
    
    def should_block(self, identifier: str, max_attempts: int = 5) -> bool:
        """检查是否应该封锁"""
        if identifier not in self.failed_attempts:
            return False
        
        # 检查最近15分钟内的失败次数
        recent_cutoff = datetime.utcnow() - timedelta(minutes=15)
        recent_failures = [
            timestamp for timestamp in self.failed_attempts[identifier] 
            if timestamp > recent_cutoff
        ]
        
        return len(recent_failures) >= max_attempts
    
    def block_identifier(self, identifier: str, duration_minutes: int = 15):
        """封锁标识符"""
        unblock_time = datetime.utcnow() + timedelta(minutes=duration_minutes)
        self.blocked_identifiers[identifier] = unblock_time
    
    def clear_failed_attempts(self, identifier: str):
        """清除失败尝试记录"""
        if identifier in self.failed_attempts:
            del self.failed_attempts[identifier]


class SecurityMiddleware:
    """安全中间件"""
    
    def __init__(self, secret_key: str):
        self.csrf_protection = CSRFProtection(secret_key)
        self.request_validator = RequestValidator()
        self.ip_filter = IPFilter(SecurityConfig.IP_WHITELIST)
        self.brute_force_protection = BruteForceProtection()
    
    async def __call__(self, request: Request, call_next):
        """中间件处理"""
        try:
            # 1. IP过滤
            client_ip = self.ip_filter.get_client_ip(request)
            if not self.ip_filter.is_ip_allowed(client_ip):
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"error": "IP not allowed"}
                )
            
            # 2. 检查IP是否可疑
            if self.ip_filter.is_ip_suspicious(client_ip):
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"error": "Too many suspicious requests"}
                )
            
            # 3. 验证请求大小
            if not self.request_validator.validate_request_size(request):
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={"error": "Request too large"}
                )
            
            # 4. 验证请求头
            if not self.request_validator.validate_headers(request):
                self.ip_filter.record_suspicious_activity(client_ip)
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"error": "Invalid headers"}
                )
            
            # 5. 验证URL
            if not self.request_validator.validate_url(request):
                self.ip_filter.record_suspicious_activity(client_ip)
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"error": "Invalid URL"}
                )
            
            # 6. 验证JSON请求体
            if not await self.request_validator.validate_json_body(request):
                self.ip_filter.record_suspicious_activity(client_ip)
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"error": "Invalid request body"}
                )
            
            # 7. CSRF保护（对于状态改变的请求）
            if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
                if not self.validate_csrf_token(request):
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={"error": "CSRF token invalid"}
                    )
            
            # 处理请求
            response = await call_next(request)
            
            # 8. 添加安全头
            self.add_security_headers(response)
            
            return response
            
        except Exception as e:
            # 记录可疑活动
            self.ip_filter.record_suspicious_activity(client_ip)
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "Internal server error"}
            )
    
    def validate_csrf_token(self, request: Request) -> bool:
        """验证CSRF令牌"""
        # 获取令牌
        token = request.headers.get(SecurityConfig.CSRF_HEADER_NAME)
        if not token:
            token = request.cookies.get(SecurityConfig.CSRF_COOKIE_NAME)
        
        if not token:
            return False
        
        # 获取会话ID（简化实现）
        session_id = request.headers.get("X-Session-ID", "")
        
        return self.csrf_protection.verify_token(token, session_id)
    
    def add_security_headers(self, response: Response):
        """添加安全头"""
        for header, value in SecurityConfig.SECURITY_HEADERS.items():
            response.headers[header] = value
    
    def handle_authentication_failure(self, request: Request, identifier: str):
        """处理认证失败"""
        client_ip = self.ip_filter.get_client_ip(request)
        
        # 记录失败尝试
        self.brute_force_protection.record_failed_attempt(identifier)
        self.brute_force_protection.record_failed_attempt(client_ip)
        
        # 检查是否需要封锁
        if self.brute_force_protection.should_block(identifier):
            self.brute_force_protection.block_identifier(identifier)
        
        if self.brute_force_protection.should_block(client_ip):
            self.ip_filter.block_ip(client_ip)
    
    def handle_authentication_success(self, request: Request, identifier: str):
        """处理认证成功"""
        # 清除失败尝试记录
        self.brute_force_protection.clear_failed_attempts(identifier)
        
        client_ip = self.ip_filter.get_client_ip(request)
        self.brute_force_protection.clear_failed_attempts(client_ip)


class CORSMiddleware:
    """CORS中间件"""
    
    def __init__(self):
        self.allowed_origins = SecurityConfig.ALLOWED_ORIGINS
        self.allowed_methods = SecurityConfig.ALLOWED_METHODS
        self.allowed_headers = SecurityConfig.ALLOWED_HEADERS
        self.expose_headers = SecurityConfig.EXPOSE_HEADERS
    
    async def __call__(self, request: Request, call_next):
        """CORS处理"""
        origin = request.headers.get("origin")
        
        # 处理预检请求
        if request.method == "OPTIONS":
            response = Response()
            self.add_cors_headers(response, origin)
            return response
        
        # 处理正常请求
        response = await call_next(request)
        self.add_cors_headers(response, origin)
        
        return response
    
    def add_cors_headers(self, response: Response, origin: Optional[str]):
        """添加CORS头"""
        if origin and (origin in self.allowed_origins or "*" in self.allowed_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allowed_methods)
            response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allowed_headers)
            response.headers["Access-Control-Expose-Headers"] = ", ".join(self.expose_headers)
            response.headers["Access-Control-Allow-Credentials"] = "true"


# 创建中间件实例
def create_security_middleware(secret_key: str) -> SecurityMiddleware:
    """创建安全中间件"""
    return SecurityMiddleware(secret_key)


cors_middleware = CORSMiddleware()


# 安全装饰器
def require_csrf_token(func):
    """CSRF令牌装饰器"""
    async def wrapper(request: Request, *args, **kwargs):
        security_middleware = create_security_middleware("your-secret-key")
        
        if not security_middleware.validate_csrf_token(request):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token required"
            )
        
        return await func(request, *args, **kwargs)
    
    return wrapper


def require_secure_connection(func):
    """安全连接装饰器"""
    async def wrapper(request: Request, *args, **kwargs):
        if not request.url.scheme == "https":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="HTTPS required"
            )
        
        return await func(request, *args, **kwargs)
    
    return wrapper