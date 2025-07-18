"""
AI智能交易大脑 - FastAPI主应用程序
"""
import os
import sys
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException, status, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from .endpoints import (
    auth_router,
    trading_router,
    monitoring_router,
    risk_router,
    portfolio_router
)
from .websocket import ws_manager, market_broadcaster, handle_websocket_connection
from .middleware import (
    create_security_middleware,
    cors_middleware,
    rate_limit_middleware,
    auth_manager
)
from .schemas import BaseResponse, ErrorResponse, ResponseStatus


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用程序生命周期管理"""
    # 启动时执行
    logger.info("AI智能交易大脑API启动中...")
    
    # 初始化数据库连接（如果需要）
    # await init_database()
    
    # 启动定时任务
    # await start_scheduled_tasks()
    
    # 清理过期令牌的定时任务
    import asyncio
    
    async def cleanup_expired_tokens():
        while True:
            auth_manager.token_manager.cleanup_expired_tokens()
            await asyncio.sleep(3600)  # 每小时清理一次
    
    # 启动清理任务
    cleanup_task = asyncio.create_task(cleanup_expired_tokens())
    
    logger.info("AI智能交易大脑API启动完成")
    
    yield
    
    # 关闭时执行
    logger.info("AI智能交易大脑API关闭中...")
    
    # 取消定时任务
    cleanup_task.cancel()
    
    # 关闭数据库连接
    # await close_database()
    
    logger.info("AI智能交易大脑API关闭完成")


# 创建FastAPI应用实例
app = FastAPI(
    title="AI智能交易大脑API",
    description="""
    AI智能交易大脑是一个专业的量化交易平台，提供以下核心功能：
    
    ## 主要功能
    
    * **交易管理** - 订单创建、修改、取消，交易记录查询
    * **投资组合** - 投资组合管理、资产配置、再平衡
    * **风险管理** - 风险指标监控、限制设置、压力测试
    * **系统监控** - 系统健康检查、性能指标、告警管理
    * **用户管理** - 用户认证、权限管理、API密钥管理
    
    ## 技术特性
    
    * **高性能** - 基于FastAPI构建，支持异步处理
    * **安全性** - 完整的认证授权体系，多层安全防护
    * **可扩展** - 模块化设计，易于扩展和维护
    * **监控** - 完整的监控和告警体系
    
    ## 开发者信息
    
    * **版本**: 1.0.0
    * **作者**: AI智能交易大脑开发团队
    * **许可**: MIT License
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    contact={
        "name": "AI智能交易大脑开发团队",
        "email": "support@ai-trading-brain.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    servers=[
        {"url": "http://localhost:8000", "description": "开发环境"},
        {"url": "https://api.ai-trading-brain.com", "description": "生产环境"}
    ]
)


# 添加中间件
# 1. 信任主机中间件
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # 生产环境中应该限制为特定域名
)

# 2. GZIP压缩中间件
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 3. CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该限制为特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count", "X-RateLimit-*"]
)

# 4. 安全中间件
security_middleware = create_security_middleware("your-secret-key-here")
app.add_middleware(type(security_middleware), security_middleware)

# 5. 限流中间件
app.add_middleware(type(rate_limit_middleware), rate_limit_middleware)


# 全局异常处理
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            status=ResponseStatus.ERROR,
            message=exc.detail,
            error_code=str(exc.status_code)
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理器"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            status=ResponseStatus.ERROR,
            message="内部服务器错误",
            error_code="INTERNAL_SERVER_ERROR",
            error_details={"type": str(type(exc).__name__), "message": str(exc)}
        ).dict()
    )


# 添加自定义中间件
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """添加请求处理时间头"""
    import time
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录请求日志"""
    import time
    start_time = time.time()
    
    # 记录请求信息
    logger.info(f"Request: {request.method} {request.url}")
    
    response = await call_next(request)
    
    # 记录响应信息
    process_time = time.time() - start_time
    logger.info(f"Response: {response.status_code} - {process_time:.4f}s")
    
    return response


# 注册路由
app.include_router(auth_router)
app.include_router(trading_router)
app.include_router(monitoring_router)
app.include_router(risk_router)
app.include_router(portfolio_router)


# WebSocket端点
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket连接端点
    
    支持的消息类型:
    - ping/pong: 心跳检测
    - subscribe/unsubscribe: 订阅/取消订阅频道
    - market: 市场数据请求
    - trading: 交易相关请求
    - portfolio: 投资组合请求
    - system: 系统状态请求
    
    订阅频道:
    - ticker:{symbol}: 行情数据
    - orderbook:{symbol}: 订单簿数据
    - trades:{symbol}: 成交数据
    - kline:{symbol}:{interval}: K线数据
    - trading:{event_type}: 交易事件
    - portfolio:{user_id}: 投资组合更新
    - system:alerts: 系统告警
    """
    await handle_websocket_connection(websocket, client_id)


# 根路径
@app.get("/", response_model=BaseResponse)
async def root():
    """根路径 - API信息"""
    return BaseResponse(
        message="欢迎使用AI智能交易大脑API",
        data={
            "name": "AI智能交易大脑API",
            "version": "1.0.0",
            "description": "专业的量化交易平台API",
            "docs_url": "/docs",
            "redoc_url": "/redoc",
            "openapi_url": "/openapi.json",
            "status": "running",
            "endpoints": {
                "auth": "/api/v1/auth",
                "trading": "/api/v1/trading",
                "monitoring": "/api/v1/monitoring",
                "risk": "/api/v1/risk",
                "portfolio": "/api/v1/portfolio"
            }
        }
    )


# 健康检查
@app.get("/health", response_model=BaseResponse)
async def health_check():
    """健康检查"""
    return BaseResponse(
        message="API服务正常运行",
        data={
            "status": "healthy",
            "timestamp": "2024-01-01T00:00:00Z",
            "version": "1.0.0",
            "uptime": "1h 30m 45s",
            "memory_usage": "256MB",
            "cpu_usage": "15%"
        }
    )


# API版本信息
@app.get("/version", response_model=BaseResponse)
async def get_version():
    """获取API版本信息"""
    return BaseResponse(
        message="API版本信息",
        data={
            "version": "1.0.0",
            "build_time": "2024-01-01T00:00:00Z",
            "commit_hash": "abc123def456",
            "branch": "main",
            "environment": "development"
        }
    )


# 自定义OpenAPI文档
def custom_openapi():
    """自定义OpenAPI文档"""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="AI智能交易大脑API",
        version="1.0.0",
        description="专业的量化交易平台API",
        routes=app.routes,
    )
    
    # 添加安全方案
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "输入格式: Bearer {token}"
        },
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API密钥认证"
        }
    }
    
    # 添加全局安全要求
    openapi_schema["security"] = [
        {"BearerAuth": []},
        {"ApiKeyAuth": []}
    ]
    
    # 添加标签描述
    openapi_schema["tags"] = [
        {
            "name": "auth",
            "description": "用户认证和授权管理"
        },
        {
            "name": "trading",
            "description": "交易相关功能"
        },
        {
            "name": "monitoring",
            "description": "系统监控和告警"
        },
        {
            "name": "risk",
            "description": "风险管理和控制"
        },
        {
            "name": "portfolio",
            "description": "投资组合管理"
        }
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# 自定义Swagger UI
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """自定义Swagger UI"""
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui.css",
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
    )


# 启动配置
if __name__ == "__main__":
    import uvicorn
    
    # 开发环境配置
    config = {
        "host": "0.0.0.0",
        "port": 8000,
        "reload": True,
        "log_level": "info",
        "access_log": True,
        "use_colors": True,
        "server_header": False,
        "date_header": False
    }
    
    logger.info("启动AI智能交易大脑API服务...")
    uvicorn.run("main:app", **config)