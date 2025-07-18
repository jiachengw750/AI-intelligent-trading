# -*- coding: utf-8 -*-
"""
交易配置
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import os
import json


@dataclass
class TradingConfig:
    """交易系统配置"""
    
    # AI决策配置
    min_confidence_threshold: float = 0.6
    max_risk_per_trade: float = 0.02  # 2%
    max_portfolio_risk: float = 0.1   # 10%
    ai_request_timeout: float = 30.0  # 秒
    
    # 风险管理配置
    risk_limits: Dict[str, float] = field(default_factory=lambda: {
        "max_portfolio_risk": 0.1,    # 最大投资组合风险10%
        "max_single_position": 0.05,   # 单笔最大仓位5%
        "max_drawdown": 0.15,         # 最大回撤15%
        "max_daily_loss": 0.03,       # 日最大损失3%
        "max_var_1d": 0.02,           # 1日VaR 2%
        "max_correlation": 0.7,       # 最大相关性0.7
        "min_liquidity_ratio": 0.2,   # 最小流动性比例20%
        "max_concentration": 0.3      # 最大集中度30%
    })
    
    # 订单执行配置
    min_order_amount: float = 10.0    # 最小订单金额
    max_order_amount: float = 100000.0  # 最大订单金额
    execution_delay_ms: int = 100     # 执行延迟（毫秒）
    slippage_rate: float = 0.001      # 滑点率
    commission_rate: float = 0.001    # 手续费率
    
    # 监控配置
    monitoring_interval: float = 5.0   # 监控间隔（秒）
    alert_retention_days: int = 30     # 告警保留天数
    metrics_retention_days: int = 7    # 指标保留天数
    
    # 缓存配置
    price_cache_ttl: int = 5          # 价格缓存TTL（秒）
    orderbook_cache_ttl: int = 2      # 订单簿缓存TTL（秒）
    kline_cache_ttl: int = 60         # K线缓存TTL（秒）
    
    # 重试配置
    max_retry_attempts: int = 3       # 最大重试次数
    retry_delay: float = 1.0          # 重试延迟（秒）
    retry_backoff: float = 2.0        # 重试退避因子
    
    # 历史数据配置
    max_history_size: int = 1000      # 最大历史记录数
    max_alert_history: int = 500      # 最大告警历史数
    
    # API限流配置
    api_rate_limit: int = 100         # API速率限制（请求/分钟）
    api_burst_limit: int = 20         # API突发限制
    
    @classmethod
    def from_env(cls) -> "TradingConfig":
        """从环境变量加载配置"""
        config = cls()
        
        # 加载环境变量
        if os.getenv("MIN_CONFIDENCE_THRESHOLD"):
            config.min_confidence_threshold = float(os.getenv("MIN_CONFIDENCE_THRESHOLD"))
            
        if os.getenv("MAX_RISK_PER_TRADE"):
            config.max_risk_per_trade = float(os.getenv("MAX_RISK_PER_TRADE"))
            
        if os.getenv("MAX_PORTFOLIO_RISK"):
            config.max_portfolio_risk = float(os.getenv("MAX_PORTFOLIO_RISK"))
            
        # 加载风险限制
        risk_limits_json = os.getenv("RISK_LIMITS")
        if risk_limits_json:
            try:
                config.risk_limits = json.loads(risk_limits_json)
            except Exception:
                pass
                
        return config
        
    @classmethod
    def from_file(cls, file_path: str) -> "TradingConfig":
        """从文件加载配置"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        config = cls()
        for key, value in data.items():
            if hasattr(config, key):
                setattr(config, key, value)
                
        return config
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "min_confidence_threshold": self.min_confidence_threshold,
            "max_risk_per_trade": self.max_risk_per_trade,
            "max_portfolio_risk": self.max_portfolio_risk,
            "ai_request_timeout": self.ai_request_timeout,
            "risk_limits": self.risk_limits,
            "min_order_amount": self.min_order_amount,
            "max_order_amount": self.max_order_amount,
            "execution_delay_ms": self.execution_delay_ms,
            "slippage_rate": self.slippage_rate,
            "commission_rate": self.commission_rate,
            "monitoring_interval": self.monitoring_interval,
            "alert_retention_days": self.alert_retention_days,
            "metrics_retention_days": self.metrics_retention_days,
            "price_cache_ttl": self.price_cache_ttl,
            "orderbook_cache_ttl": self.orderbook_cache_ttl,
            "kline_cache_ttl": self.kline_cache_ttl,
            "max_retry_attempts": self.max_retry_attempts,
            "retry_delay": self.retry_delay,
            "retry_backoff": self.retry_backoff,
            "max_history_size": self.max_history_size,
            "max_alert_history": self.max_alert_history,
            "api_rate_limit": self.api_rate_limit,
            "api_burst_limit": self.api_burst_limit
        }


# 创建全局配置实例
trading_config = TradingConfig.from_env()