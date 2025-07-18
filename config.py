# -*- coding: utf-8 -*-
"""
AI智能交易大脑 - 配置文件
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class APIConfig:
    """API配置"""
    # SiliconFlow API配置
    SILICONFLOW_API_URL: str = "https://api.siliconflow.cn/v1/chat/completions"
    SILICONFLOW_API_KEY: str = os.getenv("SILICONFLOW_API_KEY", "your_siliconflow_api_key_here")
    
    # AI模型配置
    PRIMARY_MODEL: str = "Tongyi-Zhiwen/QwenLong-L1-32B"
    SECONDARY_MODEL: str = "deepseek-ai/DeepSeek-V3"
    
    # 模型参数
    MAX_TOKENS: int = 4096
    TEMPERATURE: float = 0.7
    TOP_P: float = 0.9
    
    # API调用配置
    REQUEST_TIMEOUT: int = 30
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.0

@dataclass
class DatabaseConfig:
    """数据库配置"""
    # PostgreSQL配置
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/trading_db")
    
    # Redis配置
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")
    
    # 连接池配置
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 30
    DB_POOL_TIMEOUT: int = 30

@dataclass
class TradingConfig:
    """交易配置"""
    # 基础交易参数
    MAX_POSITION_SIZE: float = 0.1  # 最大仓位10%
    STOP_LOSS_PERCENT: float = 0.02  # 2%止损
    MAX_DAILY_TRADES: int = 10  # 每日最大交易次数
    
    # 风险控制参数
    MAX_DRAWDOWN: float = 0.15  # 最大回撤15%
    RISK_FREE_RATE: float = 0.02  # 无风险利率2%
    
    # 交易对配置
    SUPPORTED_SYMBOLS: List[str] = None
    DEFAULT_SYMBOL: str = "BTC/USDT"
    
    # 时间框架
    PRIMARY_TIMEFRAME: str = "1h"
    SECONDARY_TIMEFRAMES: List[str] = None
    
    def __post_init__(self):
        if self.SUPPORTED_SYMBOLS is None:
            self.SUPPORTED_SYMBOLS = ["BTC/USDT", "ETH/USDT", "BNB/USDT"]
        if self.SECONDARY_TIMEFRAMES is None:
            self.SECONDARY_TIMEFRAMES = ["5m", "15m", "4h", "1d"]

@dataclass
class AIConfig:
    """AI系统配置"""
    # 决策参数
    MIN_CONFIDENCE_THRESHOLD: float = 0.75
    CONSENSUS_THRESHOLD: float = 0.8
    
    # 学习参数
    EXPERIENCE_BUFFER_SIZE: int = 10000
    BATCH_SIZE: int = 64
    LEARNING_RATE: float = 0.001
    
    # 模式识别参数
    PATTERN_SIMILARITY_THRESHOLD: float = 0.8
    MAX_PATTERN_AGE_DAYS: int = 30

@dataclass
class ExchangeConfig:
    """交易所配置"""
    # OKX配置
    OKX_API_KEY: str = os.getenv("OKX_API_KEY", "your_okx_api_key")
    OKX_SECRET: str = os.getenv("OKX_SECRET", "your_okx_secret")
    OKX_PASSPHRASE: str = os.getenv("OKX_PASSPHRASE", "your_okx_passphrase")
    
    # 其他交易所配置可以后续添加
    BINANCE_API_KEY: str = os.getenv("BINANCE_API_KEY", "")
    BINANCE_SECRET: str = os.getenv("BINANCE_SECRET", "")
    
    # 交易所选择
    PRIMARY_EXCHANGE: str = "okx"
    BACKUP_EXCHANGES: List[str] = None
    
    def __post_init__(self):
        if self.BACKUP_EXCHANGES is None:
            self.BACKUP_EXCHANGES = ["binance"]

@dataclass
class MonitoringConfig:
    """监控配置"""
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: str = "logs/trading_system.log"
    
    # 监控指标
    METRICS_COLLECTION_INTERVAL: int = 60  # 秒
    ALERT_THRESHOLDS: Dict[str, float] = None
    
    # 告警配置
    ALERT_WEBHOOK_URL: str = os.getenv("ALERT_WEBHOOK_URL", "")
    ALERT_EMAIL: str = os.getenv("ALERT_EMAIL", "")
    
    def __post_init__(self):
        if self.ALERT_THRESHOLDS is None:
            self.ALERT_THRESHOLDS = {
                "cpu_usage": 80.0,
                "memory_usage": 85.0,
                "error_rate": 0.05,
                "api_latency": 1000.0
            }

@dataclass
class SystemConfig:
    """系统配置"""
    # 系统信息
    SYSTEM_NAME: str = "AI智能交易大脑"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # 运行模式
    SIMULATION_MODE: bool = os.getenv("SIMULATION_MODE", "True").lower() == "true"
    
    # 性能配置
    MAX_WORKERS: int = 4
    ASYNC_TIMEOUT: int = 30
    
    # 安全配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your_secret_key_here")
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "your_encryption_key_here")

# 创建配置实例
api_config = APIConfig()
db_config = DatabaseConfig()
trading_config = TradingConfig()
ai_config = AIConfig()
exchange_config = ExchangeConfig()
monitoring_config = MonitoringConfig()
system_config = SystemConfig()

# 配置字典（用于动态访问）
CONFIG = {
    "api": api_config,
    "database": db_config,
    "trading": trading_config,
    "ai": ai_config,
    "exchange": exchange_config,
    "monitoring": monitoring_config,
    "system": system_config
}

def get_config(section: str = None):
    """获取配置"""
    if section:
        return CONFIG.get(section)
    return CONFIG

def update_config(section: str, **kwargs):
    """更新配置"""
    if section in CONFIG:
        config_obj = CONFIG[section]
        for key, value in kwargs.items():
            if hasattr(config_obj, key):
                setattr(config_obj, key, value)
            else:
                raise AttributeError(f"Configuration {section} has no attribute {key}")
    else:
        raise ValueError(f"Unknown configuration section: {section}")

if __name__ == "__main__":
    # 打印当前配置
    print("=== AI智能交易大脑配置信息 ===")
    for section, config in CONFIG.items():
        print(f"\n[{section.upper()}]")
        for attr, value in config.__dict__.items():
            if "key" in attr.lower() or "secret" in attr.lower() or "password" in attr.lower():
                print(f"  {attr}: {'*' * 10}")
            else:
                print(f"  {attr}: {value}")