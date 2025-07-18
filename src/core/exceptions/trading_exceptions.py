# -*- coding: utf-8 -*-
"""
交易系统异常定义
"""

from typing import Dict, Any, Optional
from enum import Enum


class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """错误分类"""
    SYSTEM = "system"
    DATA = "data"
    AI = "ai"
    TRADING = "trading"
    RISK = "risk"
    NETWORK = "network"
    VALIDATION = "validation"
    CONFIGURATION = "configuration"


class BaseTradingException(Exception):
    """交易系统基础异常"""
    
    def __init__(self, message: str, error_code: str = None, 
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 category: ErrorCategory = ErrorCategory.SYSTEM,
                 context: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.category = category
        self.context = context or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "message": self.message,
            "error_code": self.error_code,
            "severity": self.severity.value,
            "category": self.category.value,
            "context": self.context,
            "exception_type": self.__class__.__name__
        }


# 系统异常
class SystemException(BaseTradingException):
    """系统异常"""
    
    def __init__(self, message: str, error_code: str = "SYS_001", **kwargs):
        super().__init__(message, error_code, ErrorSeverity.HIGH, ErrorCategory.SYSTEM, **kwargs)


class ConfigurationException(BaseTradingException):
    """配置异常"""
    
    def __init__(self, message: str, error_code: str = "CFG_001", **kwargs):
        super().__init__(message, error_code, ErrorSeverity.HIGH, ErrorCategory.CONFIGURATION, **kwargs)


class NetworkException(BaseTradingException):
    """网络异常"""
    
    def __init__(self, message: str, error_code: str = "NET_001", **kwargs):
        super().__init__(message, error_code, ErrorSeverity.MEDIUM, ErrorCategory.NETWORK, **kwargs)


# 数据异常
class DataException(BaseTradingException):
    """数据异常"""
    
    def __init__(self, message: str, error_code: str = "DATA_001", **kwargs):
        super().__init__(message, error_code, ErrorSeverity.MEDIUM, ErrorCategory.DATA, **kwargs)


class DataValidationException(DataException):
    """数据验证异常"""
    
    def __init__(self, message: str, error_code: str = "DATA_002", **kwargs):
        super().__init__(message, error_code, ErrorSeverity.MEDIUM, ErrorCategory.VALIDATION, **kwargs)


class DataCollectionException(DataException):
    """数据采集异常"""
    
    def __init__(self, message: str, error_code: str = "DATA_003", **kwargs):
        super().__init__(message, error_code, ErrorSeverity.MEDIUM, ErrorCategory.DATA, **kwargs)


class DataProcessingException(DataException):
    """数据处理异常"""
    
    def __init__(self, message: str, error_code: str = "DATA_004", **kwargs):
        super().__init__(message, error_code, ErrorSeverity.MEDIUM, ErrorCategory.DATA, **kwargs)


class DataStorageException(DataException):
    """数据存储异常"""
    
    def __init__(self, message: str, error_code: str = "DATA_005", **kwargs):
        super().__init__(message, error_code, ErrorSeverity.HIGH, ErrorCategory.DATA, **kwargs)


# AI异常
class AIException(BaseTradingException):
    """AI异常"""
    
    def __init__(self, message: str, error_code: str = "AI_001", **kwargs):
        super().__init__(message, error_code, ErrorSeverity.HIGH, ErrorCategory.AI, **kwargs)


class AIModelException(AIException):
    """AI模型异常"""
    
    def __init__(self, message: str, error_code: str = "AI_002", **kwargs):
        super().__init__(message, error_code, ErrorSeverity.HIGH, ErrorCategory.AI, **kwargs)


class AIResponseException(AIException):
    """AI响应异常"""
    
    def __init__(self, message: str, error_code: str = "AI_003", **kwargs):
        super().__init__(message, error_code, ErrorSeverity.MEDIUM, ErrorCategory.AI, **kwargs)


class AITimeoutException(AIException):
    """AI超时异常"""
    
    def __init__(self, message: str, error_code: str = "AI_004", **kwargs):
        super().__init__(message, error_code, ErrorSeverity.MEDIUM, ErrorCategory.AI, **kwargs)


class AIRateLimitException(AIException):
    """AI速率限制异常"""
    
    def __init__(self, message: str, error_code: str = "AI_005", **kwargs):
        super().__init__(message, error_code, ErrorSeverity.LOW, ErrorCategory.AI, **kwargs)


# 交易异常
class TradingException(BaseTradingException):
    """交易异常"""
    
    def __init__(self, message: str, error_code: str = "TRADE_001", **kwargs):
        super().__init__(message, error_code, ErrorSeverity.HIGH, ErrorCategory.TRADING, **kwargs)


class OrderException(TradingException):
    """订单异常"""
    
    def __init__(self, message: str, error_code: str = "TRADE_002", **kwargs):
        super().__init__(message, error_code, ErrorSeverity.HIGH, ErrorCategory.TRADING, **kwargs)


class OrderValidationException(OrderException):
    """订单验证异常"""
    
    def __init__(self, message: str, error_code: str = "TRADE_003", **kwargs):
        super().__init__(message, error_code, ErrorSeverity.MEDIUM, ErrorCategory.VALIDATION, **kwargs)


class OrderExecutionException(OrderException):
    """订单执行异常"""
    
    def __init__(self, message: str, error_code: str = "TRADE_004", **kwargs):
        super().__init__(message, error_code, ErrorSeverity.HIGH, ErrorCategory.TRADING, **kwargs)


class InsufficientFundsException(TradingException):
    """资金不足异常"""
    
    def __init__(self, message: str, error_code: str = "TRADE_005", **kwargs):
        super().__init__(message, error_code, ErrorSeverity.MEDIUM, ErrorCategory.TRADING, **kwargs)


class PositionException(TradingException):
    """持仓异常"""
    
    def __init__(self, message: str, error_code: str = "TRADE_006", **kwargs):
        super().__init__(message, error_code, ErrorSeverity.MEDIUM, ErrorCategory.TRADING, **kwargs)


class MarketClosedException(TradingException):
    """市场关闭异常"""
    
    def __init__(self, message: str, error_code: str = "TRADE_007", **kwargs):
        super().__init__(message, error_code, ErrorSeverity.LOW, ErrorCategory.TRADING, **kwargs)


# 风险异常
class RiskException(BaseTradingException):
    """风险异常"""
    
    def __init__(self, message: str, error_code: str = "RISK_001", **kwargs):
        super().__init__(message, error_code, ErrorSeverity.HIGH, ErrorCategory.RISK, **kwargs)


class RiskLimitException(RiskException):
    """风险限制异常"""
    
    def __init__(self, message: str, error_code: str = "RISK_002", **kwargs):
        super().__init__(message, error_code, ErrorSeverity.CRITICAL, ErrorCategory.RISK, **kwargs)


class DrawdownException(RiskException):
    """回撤异常"""
    
    def __init__(self, message: str, error_code: str = "RISK_003", **kwargs):
        super().__init__(message, error_code, ErrorSeverity.CRITICAL, ErrorCategory.RISK, **kwargs)


class VolatilityException(RiskException):
    """波动率异常"""
    
    def __init__(self, message: str, error_code: str = "RISK_004", **kwargs):
        super().__init__(message, error_code, ErrorSeverity.HIGH, ErrorCategory.RISK, **kwargs)


class CorrelationException(RiskException):
    """相关性异常"""
    
    def __init__(self, message: str, error_code: str = "RISK_005", **kwargs):
        super().__init__(message, error_code, ErrorSeverity.MEDIUM, ErrorCategory.RISK, **kwargs)


class LiquidityException(RiskException):
    """流动性异常"""
    
    def __init__(self, message: str, error_code: str = "RISK_006", **kwargs):
        super().__init__(message, error_code, ErrorSeverity.HIGH, ErrorCategory.RISK, **kwargs)


# 验证异常
class ValidationException(BaseTradingException):
    """验证异常"""
    
    def __init__(self, message: str, error_code: str = "VAL_001", **kwargs):
        super().__init__(message, error_code, ErrorSeverity.MEDIUM, ErrorCategory.VALIDATION, **kwargs)


class ParameterValidationException(ValidationException):
    """参数验证异常"""
    
    def __init__(self, message: str, error_code: str = "VAL_002", **kwargs):
        super().__init__(message, error_code, ErrorSeverity.MEDIUM, ErrorCategory.VALIDATION, **kwargs)


class SchemaValidationException(ValidationException):
    """模式验证异常"""
    
    def __init__(self, message: str, error_code: str = "VAL_003", **kwargs):
        super().__init__(message, error_code, ErrorSeverity.MEDIUM, ErrorCategory.VALIDATION, **kwargs)


# 异常处理器
class ExceptionHandler:
    """异常处理器"""
    
    def __init__(self):
        self.handlers = {}
        self.default_handler = None
        
    def register_handler(self, exception_class: type, handler: callable):
        """注册异常处理器"""
        self.handlers[exception_class] = handler
        
    def set_default_handler(self, handler: callable):
        """设置默认异常处理器"""
        self.default_handler = handler
        
    def handle(self, exception: Exception) -> bool:
        """处理异常"""
        try:
            # 查找特定处理器
            handler = self.handlers.get(type(exception))
            
            if handler:
                return handler(exception)
            
            # 查找父类处理器
            for exception_class, handler in self.handlers.items():
                if isinstance(exception, exception_class):
                    return handler(exception)
                    
            # 使用默认处理器
            if self.default_handler:
                return self.default_handler(exception)
                
            return False
            
        except Exception as e:
            # 处理器本身出错
            print(f"异常处理器出错: {e}")
            return False
            
    def get_error_info(self, exception: Exception) -> Dict[str, Any]:
        """获取错误信息"""
        if isinstance(exception, BaseTradingException):
            return exception.to_dict()
        else:
            return {
                "message": str(exception),
                "error_code": "UNKNOWN_001",
                "severity": ErrorSeverity.MEDIUM.value,
                "category": ErrorCategory.SYSTEM.value,
                "context": {},
                "exception_type": exception.__class__.__name__
            }


# 全局异常处理器实例
global_exception_handler = ExceptionHandler()


# 异常装饰器
def handle_exceptions(exception_handler: ExceptionHandler = None):
    """异常处理装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                handler = exception_handler or global_exception_handler
                if not handler.handle(e):
                    raise
                    
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                handler = exception_handler or global_exception_handler
                if not handler.handle(e):
                    raise
                    
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return wrapper
            
    return decorator


# 异常工具函数
def create_exception_from_dict(error_dict: Dict[str, Any]) -> BaseTradingException:
    """从字典创建异常"""
    exception_type = error_dict.get("exception_type", "BaseTradingException")
    message = error_dict.get("message", "Unknown error")
    error_code = error_dict.get("error_code")
    severity = ErrorSeverity(error_dict.get("severity", "medium"))
    category = ErrorCategory(error_dict.get("category", "system"))
    context = error_dict.get("context", {})
    
    # 根据异常类型创建相应的异常实例
    exception_classes = {
        "SystemException": SystemException,
        "ConfigurationException": ConfigurationException,
        "NetworkException": NetworkException,
        "DataException": DataException,
        "DataValidationException": DataValidationException,
        "DataCollectionException": DataCollectionException,
        "DataProcessingException": DataProcessingException,
        "DataStorageException": DataStorageException,
        "AIException": AIException,
        "AIModelException": AIModelException,
        "AIResponseException": AIResponseException,
        "AITimeoutException": AITimeoutException,
        "AIRateLimitException": AIRateLimitException,
        "TradingException": TradingException,
        "OrderException": OrderException,
        "OrderValidationException": OrderValidationException,
        "OrderExecutionException": OrderExecutionException,
        "InsufficientFundsException": InsufficientFundsException,
        "PositionException": PositionException,
        "MarketClosedException": MarketClosedException,
        "RiskException": RiskException,
        "RiskLimitException": RiskLimitException,
        "DrawdownException": DrawdownException,
        "VolatilityException": VolatilityException,
        "CorrelationException": CorrelationException,
        "LiquidityException": LiquidityException,
        "ValidationException": ValidationException,
        "ParameterValidationException": ParameterValidationException,
        "SchemaValidationException": SchemaValidationException,
    }
    
    exception_class = exception_classes.get(exception_type, BaseTradingException)
    
    return exception_class(
        message=message,
        error_code=error_code,
        severity=severity,
        category=category,
        context=context
    )


def format_exception_message(exception: Exception) -> str:
    """格式化异常消息"""
    if isinstance(exception, BaseTradingException):
        return f"[{exception.error_code}] {exception.message}"
    else:
        return f"[UNKNOWN] {str(exception)}"