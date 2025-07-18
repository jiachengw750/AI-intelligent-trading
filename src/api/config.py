"""
API配置管理
"""
import os
from typing import List, Optional, Dict, Any
from pydantic import BaseSettings, Field, validator
from pathlib import Path


class APISettings(BaseSettings):
    """API设置"""
    
    # 基本设置
    app_name: str = "AI智能交易大脑API"
    app_version: str = "1.0.0"
    description: str = "专业的量化交易平台API"
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # 服务器设置
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    reload: bool = Field(default=True, env="RELOAD")
    workers: int = Field(default=1, env="WORKERS")
    
    # 安全设置
    secret_key: str = Field(default="your-secret-key-here", env="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=30, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # CORS设置
    allowed_origins: List[str] = Field(
        default=["*"],
        env="ALLOWED_ORIGINS"
    )
    allowed_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        env="ALLOWED_METHODS"
    )
    allowed_headers: List[str] = Field(default=["*"], env="ALLOWED_HEADERS")
    
    # 限流设置
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    global_rate_limit: int = Field(default=1000, env="GLOBAL_RATE_LIMIT")
    api_rate_limit: int = Field(default=100, env="API_RATE_LIMIT")
    trading_rate_limit: int = Field(default=50, env="TRADING_RATE_LIMIT")
    
    # 数据库设置
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")
    database_pool_size: int = Field(default=5, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=10, env="DATABASE_MAX_OVERFLOW")
    
    # Redis设置
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    
    # 日志设置
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")
    log_rotation: str = Field(default="1 day", env="LOG_ROTATION")
    log_retention: str = Field(default="30 days", env="LOG_RETENTION")
    
    # 监控设置
    metrics_enabled: bool = Field(default=True, env="METRICS_ENABLED")
    metrics_port: int = Field(default=8001, env="METRICS_PORT")
    health_check_enabled: bool = Field(default=True, env="HEALTH_CHECK_ENABLED")
    
    # 文档设置
    docs_enabled: bool = Field(default=True, env="DOCS_ENABLED")
    docs_url: str = Field(default="/docs", env="DOCS_URL")
    redoc_url: str = Field(default="/redoc", env="REDOC_URL")
    openapi_url: str = Field(default="/openapi.json", env="OPENAPI_URL")
    
    # 文件上传设置
    max_file_size: int = Field(default=10 * 1024 * 1024, env="MAX_FILE_SIZE")  # 10MB
    allowed_file_types: List[str] = Field(
        default=[".jpg", ".jpeg", ".png", ".gif", ".pdf", ".xlsx", ".csv"],
        env="ALLOWED_FILE_TYPES"
    )
    upload_dir: str = Field(default="uploads", env="UPLOAD_DIR")
    
    # 外部服务设置
    okx_api_key: Optional[str] = Field(default=None, env="OKX_API_KEY")
    okx_api_secret: Optional[str] = Field(default=None, env="OKX_API_SECRET")
    okx_passphrase: Optional[str] = Field(default=None, env="OKX_PASSPHRASE")
    okx_sandbox: bool = Field(default=True, env="OKX_SANDBOX")
    
    # AI模型设置
    ai_model_provider: str = Field(default="siliconflow", env="AI_MODEL_PROVIDER")
    ai_model_api_key: Optional[str] = Field(default=None, env="AI_MODEL_API_KEY")
    ai_model_base_url: Optional[str] = Field(default=None, env="AI_MODEL_BASE_URL")
    
    # 邮件设置
    mail_server: Optional[str] = Field(default=None, env="MAIL_SERVER")
    mail_port: int = Field(default=587, env="MAIL_PORT")
    mail_username: Optional[str] = Field(default=None, env="MAIL_USERNAME")
    mail_password: Optional[str] = Field(default=None, env="MAIL_PASSWORD")
    mail_use_tls: bool = Field(default=True, env="MAIL_USE_TLS")
    
    # 缓存设置
    cache_enabled: bool = Field(default=True, env="CACHE_ENABLED")
    cache_type: str = Field(default="redis", env="CACHE_TYPE")  # redis, memory
    cache_expire_time: int = Field(default=3600, env="CACHE_EXPIRE_TIME")  # 1小时
    
    # 任务队列设置
    task_queue_enabled: bool = Field(default=True, env="TASK_QUEUE_ENABLED")
    task_queue_broker: str = Field(default="redis://localhost:6379/1", env="TASK_QUEUE_BROKER")
    task_queue_backend: str = Field(default="redis://localhost:6379/2", env="TASK_QUEUE_BACKEND")
    
    @validator('allowed_origins', pre=True)
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            return v.split(',')
        return v
    
    @validator('allowed_methods', pre=True)
    def parse_allowed_methods(cls, v):
        if isinstance(v, str):
            return v.split(',')
        return v
    
    @validator('allowed_headers', pre=True)
    def parse_allowed_headers(cls, v):
        if isinstance(v, str):
            return v.split(',')
        return v
    
    @validator('allowed_file_types', pre=True)
    def parse_allowed_file_types(cls, v):
        if isinstance(v, str):
            return v.split(',')
        return v
    
    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.environment.lower() == "development"
    
    @property
    def is_testing(self) -> bool:
        """是否为测试环境"""
        return self.environment.lower() == "testing"
    
    @property
    def database_config(self) -> Dict[str, Any]:
        """数据库配置"""
        return {
            "url": self.database_url,
            "echo": self.database_echo,
            "pool_size": self.database_pool_size,
            "max_overflow": self.database_max_overflow,
        }
    
    @property
    def redis_config(self) -> Dict[str, Any]:
        """Redis配置"""
        if self.redis_url:
            return {"url": self.redis_url}
        else:
            return {
                "host": self.redis_host,
                "port": self.redis_port,
                "db": self.redis_db,
                "password": self.redis_password,
            }
    
    @property
    def cors_config(self) -> Dict[str, Any]:
        """CORS配置"""
        return {
            "allow_origins": self.allowed_origins,
            "allow_methods": self.allowed_methods,
            "allow_headers": self.allowed_headers,
            "allow_credentials": True,
            "expose_headers": ["X-Total-Count", "X-RateLimit-*"]
        }
    
    @property
    def uvicorn_config(self) -> Dict[str, Any]:
        """Uvicorn配置"""
        config = {
            "host": self.host,
            "port": self.port,
            "log_level": self.log_level.lower(),
            "access_log": True,
            "server_header": False,
            "date_header": False,
        }
        
        if self.is_production:
            config.update({
                "workers": self.workers,
                "use_colors": False,
                "proxy_headers": True,
                "forwarded_allow_ips": "*",
                "timeout_keep_alive": 30
            })
        else:
            config.update({
                "reload": self.reload,
                "use_colors": True,
                "reload_dirs": ["src"]
            })
        
        return config
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# 创建全局设置实例
settings = APISettings()


def get_settings() -> APISettings:
    """获取设置实例"""
    return settings


# 环境特定设置
class DevelopmentSettings(APISettings):
    """开发环境设置"""
    debug: bool = True
    environment: str = "development"
    reload: bool = True
    log_level: str = "DEBUG"
    docs_enabled: bool = True


class ProductionSettings(APISettings):
    """生产环境设置"""
    debug: bool = False
    environment: str = "production"
    reload: bool = False
    log_level: str = "INFO"
    docs_enabled: bool = False
    workers: int = 4


class TestingSettings(APISettings):
    """测试环境设置"""
    debug: bool = True
    environment: str = "testing"
    database_url: str = "sqlite:///./test.db"
    cache_enabled: bool = False
    task_queue_enabled: bool = False


def get_settings_by_env(env: str) -> APISettings:
    """根据环境获取设置"""
    if env.lower() == "production":
        return ProductionSettings()
    elif env.lower() == "testing":
        return TestingSettings()
    else:
        return DevelopmentSettings()


# 验证配置
def validate_settings(settings: APISettings) -> None:
    """验证设置"""
    errors = []
    
    # 验证必要的设置
    if settings.is_production and settings.secret_key == "your-secret-key-here":
        errors.append("生产环境必须设置自定义的SECRET_KEY")
    
    if settings.database_url and not settings.database_url.startswith(("sqlite://", "postgresql://", "mysql://")):
        errors.append("数据库URL格式不正确")
    
    if settings.redis_url and not settings.redis_url.startswith("redis://"):
        errors.append("Redis URL格式不正确")
    
    if settings.port < 1 or settings.port > 65535:
        errors.append("端口号必须在1-65535之间")
    
    if settings.workers < 1:
        errors.append("工作进程数必须大于0")
    
    if errors:
        raise ValueError("配置验证失败：\n" + "\n".join(errors))


# 初始化时验证设置
try:
    validate_settings(settings)
except ValueError as e:
    print(f"警告：{e}")


# 导出常用的设置值
API_TITLE = settings.app_name
API_VERSION = settings.app_version
API_DESCRIPTION = settings.description
DEBUG = settings.debug
ENVIRONMENT = settings.environment
SECRET_KEY = settings.secret_key