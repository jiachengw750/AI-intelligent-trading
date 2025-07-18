"""
限流中间件
"""
import time
import asyncio
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from collections import defaultdict, deque
import hashlib
import json


@dataclass
class RateLimitRule:
    """限流规则"""
    requests: int  # 请求数量
    window: int    # 时间窗口（秒）
    burst: int     # 突发请求数量
    
    def __post_init__(self):
        if self.burst <= 0:
            self.burst = self.requests


class RateLimitError(Exception):
    """限流错误"""
    def __init__(self, message: str, retry_after: int, limit: int, remaining: int):
        self.message = message
        self.retry_after = retry_after
        self.limit = limit
        self.remaining = remaining
        super().__init__(message)


class TokenBucket:
    """令牌桶算法实现"""
    
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.time()
        self.lock = asyncio.Lock()
    
    async def consume(self, tokens: int = 1) -> bool:
        """消费令牌"""
        async with self.lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def _refill(self):
        """补充令牌"""
        now = time.time()
        elapsed = now - self.last_refill
        
        # 计算应该补充的令牌数
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    async def get_tokens(self) -> int:
        """获取当前令牌数"""
        async with self.lock:
            self._refill()
            return int(self.tokens)


class SlidingWindowCounter:
    """滑动窗口计数器"""
    
    def __init__(self, window_size: int):
        self.window_size = window_size
        self.requests = deque()
        self.lock = asyncio.Lock()
    
    async def add_request(self, timestamp: float = None) -> int:
        """添加请求记录"""
        if timestamp is None:
            timestamp = time.time()
        
        async with self.lock:
            # 移除过期请求
            self._cleanup(timestamp)
            
            # 添加新请求
            self.requests.append(timestamp)
            
            return len(self.requests)
    
    async def get_count(self, timestamp: float = None) -> int:
        """获取窗口内请求数"""
        if timestamp is None:
            timestamp = time.time()
        
        async with self.lock:
            self._cleanup(timestamp)
            return len(self.requests)
    
    def _cleanup(self, current_time: float):
        """清理过期请求"""
        cutoff_time = current_time - self.window_size
        while self.requests and self.requests[0] < cutoff_time:
            self.requests.popleft()


class RateLimiter:
    """限流器"""
    
    def __init__(self):
        self.token_buckets: Dict[str, TokenBucket] = {}
        self.sliding_windows: Dict[str, SlidingWindowCounter] = {}
        self.rules: Dict[str, RateLimitRule] = {}
    
    def add_rule(self, key: str, rule: RateLimitRule):
        """添加限流规则"""
        self.rules[key] = rule
        
        # 创建令牌桶
        refill_rate = rule.requests / rule.window
        self.token_buckets[key] = TokenBucket(rule.burst, refill_rate)
        
        # 创建滑动窗口
        self.sliding_windows[key] = SlidingWindowCounter(rule.window)
    
    async def check_limit(self, key: str, tokens: int = 1) -> Dict[str, Any]:
        """检查限流"""
        if key not in self.rules:
            return {"allowed": True, "remaining": float('inf'), "reset_time": 0}
        
        rule = self.rules[key]
        bucket = self.token_buckets[key]
        window = self.sliding_windows[key]
        
        # 检查令牌桶
        if not await bucket.consume(tokens):
            remaining_tokens = await bucket.get_tokens()
            return {
                "allowed": False,
                "remaining": remaining_tokens,
                "reset_time": int(time.time() + rule.window),
                "retry_after": rule.window
            }
        
        # 检查滑动窗口
        current_count = await window.add_request()
        if current_count > rule.requests:
            return {
                "allowed": False,
                "remaining": max(0, rule.requests - current_count),
                "reset_time": int(time.time() + rule.window),
                "retry_after": rule.window
            }
        
        return {
            "allowed": True,
            "remaining": rule.requests - current_count,
            "reset_time": int(time.time() + rule.window)
        }


class RateLimitMiddleware:
    """限流中间件"""
    
    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.setup_default_rules()
    
    def setup_default_rules(self):
        """设置默认限流规则"""
        # 全局限流
        self.rate_limiter.add_rule("global", RateLimitRule(1000, 60, 100))
        
        # API限流
        self.rate_limiter.add_rule("api", RateLimitRule(100, 60, 20))
        
        # 交易API限流
        self.rate_limiter.add_rule("trading", RateLimitRule(50, 60, 10))
        
        # 登录限流
        self.rate_limiter.add_rule("login", RateLimitRule(5, 300, 1))
        
        # 密码重置限流
        self.rate_limiter.add_rule("password_reset", RateLimitRule(3, 3600, 1))
    
    def get_client_identifier(self, request: Request) -> str:
        """获取客户端标识"""
        # 优先使用认证用户ID
        if hasattr(request.state, 'user_id'):
            return f"user:{request.state.user_id}"
        
        # 使用IP地址
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host
        
        return f"ip:{client_ip}"
    
    def get_rate_limit_key(self, request: Request, limit_type: str) -> str:
        """获取限流键"""
        client_id = self.get_client_identifier(request)
        return f"{limit_type}:{client_id}"
    
    async def __call__(self, request: Request, call_next: Callable):
        """中间件处理"""
        # 获取请求路径
        path = request.url.path
        
        # 确定限流类型
        limit_type = self.get_limit_type(path)
        
        # 检查限流
        rate_limit_key = self.get_rate_limit_key(request, limit_type)
        
        try:
            result = await self.rate_limiter.check_limit(rate_limit_key)
            
            if not result["allowed"]:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "Rate limit exceeded",
                        "message": "Too many requests",
                        "retry_after": result.get("retry_after", 60)
                    },
                    headers={
                        "X-RateLimit-Limit": str(self.rate_limiter.rules[limit_type].requests),
                        "X-RateLimit-Remaining": str(result["remaining"]),
                        "X-RateLimit-Reset": str(result["reset_time"]),
                        "Retry-After": str(result.get("retry_after", 60))
                    }
                )
            
            # 处理请求
            response = await call_next(request)
            
            # 添加限流头
            response.headers["X-RateLimit-Limit"] = str(self.rate_limiter.rules[limit_type].requests)
            response.headers["X-RateLimit-Remaining"] = str(result["remaining"])
            response.headers["X-RateLimit-Reset"] = str(result["reset_time"])
            
            return response
            
        except Exception as e:
            # 限流中间件异常不应该影响正常请求
            print(f"Rate limit middleware error: {e}")
            return await call_next(request)
    
    def get_limit_type(self, path: str) -> str:
        """根据路径获取限流类型"""
        if path.startswith("/api/v1/auth/login"):
            return "login"
        elif path.startswith("/api/v1/auth/password/reset"):
            return "password_reset"
        elif path.startswith("/api/v1/trading"):
            return "trading"
        elif path.startswith("/api/v1/"):
            return "api"
        else:
            return "global"


class DynamicRateLimitMiddleware:
    """动态限流中间件"""
    
    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.user_rules: Dict[str, Dict[str, RateLimitRule]] = {}
        self.setup_default_rules()
    
    def setup_default_rules(self):
        """设置默认限流规则"""
        # 根据用户角色设置不同的限流规则
        self.user_rules["admin"] = {
            "api": RateLimitRule(1000, 60, 100),
            "trading": RateLimitRule(200, 60, 50),
        }
        
        self.user_rules["trader"] = {
            "api": RateLimitRule(500, 60, 50),
            "trading": RateLimitRule(100, 60, 20),
        }
        
        self.user_rules["viewer"] = {
            "api": RateLimitRule(100, 60, 20),
            "trading": RateLimitRule(10, 60, 5),
        }
    
    def get_user_rule(self, user_role: str, limit_type: str) -> Optional[RateLimitRule]:
        """获取用户限流规则"""
        if user_role in self.user_rules:
            return self.user_rules[user_role].get(limit_type)
        return None
    
    async def apply_user_limits(self, request: Request, user_info: Dict[str, Any]):
        """应用用户限流"""
        user_id = user_info.get("user_id")
        user_role = user_info.get("role", "viewer")
        
        path = request.url.path
        limit_type = self.get_limit_type(path)
        
        # 获取用户规则
        user_rule = self.get_user_rule(user_role, limit_type)
        if not user_rule:
            return True
        
        # 动态添加规则
        rule_key = f"{limit_type}:{user_id}"
        if rule_key not in self.rate_limiter.rules:
            self.rate_limiter.add_rule(rule_key, user_rule)
        
        # 检查限流
        result = await self.rate_limiter.check_limit(rule_key)
        
        if not result["allowed"]:
            raise RateLimitError(
                "User rate limit exceeded",
                result.get("retry_after", 60),
                user_rule.requests,
                result["remaining"]
            )
        
        return True
    
    def get_limit_type(self, path: str) -> str:
        """根据路径获取限流类型"""
        if path.startswith("/api/v1/trading"):
            return "trading"
        elif path.startswith("/api/v1/"):
            return "api"
        else:
            return "global"


# 创建中间件实例
rate_limit_middleware = RateLimitMiddleware()
dynamic_rate_limit_middleware = DynamicRateLimitMiddleware()


def create_rate_limit_decorator(limit_type: str, requests: int, window: int, burst: int = None):
    """创建限流装饰器"""
    if burst is None:
        burst = requests
    
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 这里需要从请求上下文中获取客户端信息
            # 实际实现可能需要根据具体的框架调整
            request = kwargs.get('request')
            if request:
                client_id = rate_limit_middleware.get_client_identifier(request)
                rate_limit_key = f"{limit_type}:{client_id}"
                
                # 动态添加规则
                if rate_limit_key not in rate_limit_middleware.rate_limiter.rules:
                    rule = RateLimitRule(requests, window, burst)
                    rate_limit_middleware.rate_limiter.add_rule(rate_limit_key, rule)
                
                # 检查限流
                result = await rate_limit_middleware.rate_limiter.check_limit(rate_limit_key)
                
                if not result["allowed"]:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Rate limit exceeded"
                    )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# 常用限流装饰器
def rate_limit_strict(requests: int, window: int):
    """严格限流装饰器"""
    return create_rate_limit_decorator("strict", requests, window, 1)


def rate_limit_burst(requests: int, window: int, burst: int):
    """突发限流装饰器"""
    return create_rate_limit_decorator("burst", requests, window, burst)


def rate_limit_api(requests: int = 100, window: int = 60):
    """API限流装饰器"""
    return create_rate_limit_decorator("api", requests, window)


def rate_limit_trading(requests: int = 50, window: int = 60):
    """交易限流装饰器"""
    return create_rate_limit_decorator("trading", requests, window)