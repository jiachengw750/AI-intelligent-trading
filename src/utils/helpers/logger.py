# -*- coding: utf-8 -*-
"""
日志工具模块
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
import json
from pythonjsonlogger import jsonlogger


class TradingSystemLogger:
    """交易系统日志记录器"""
    
    def __init__(self, name: str = "trading_system"):
        self.name = name
        self.logger = logging.getLogger(name)
        self.formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s'
        )
        
    def setup_handlers(self, 
                      console_level: str = "INFO",
                      file_level: str = "DEBUG",
                      log_file: Optional[str] = None):
        """设置日志处理器"""
        
        # 清除现有处理器
        self.logger.handlers.clear()
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, console_level))
        console_handler.setFormatter(self.formatter)
        self.logger.addHandler(console_handler)
        
        # 文件处理器
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(getattr(logging, file_level))
            file_handler.setFormatter(self.formatter)
            self.logger.addHandler(file_handler)
            
        self.logger.setLevel(logging.DEBUG)
        
    def log_trade_decision(self, decision_data: dict):
        """记录交易决策"""
        self.logger.info(
            "AI交易决策",
            extra={
                "event_type": "ai_decision",
                "symbol": decision_data.get("symbol"),
                "decision": decision_data.get("decision"),
                "confidence": decision_data.get("confidence"),
                "reasoning": decision_data.get("reasoning")
            }
        )
        
    def log_trade_execution(self, trade_data: dict):
        """记录交易执行"""
        self.logger.info(
            "交易执行",
            extra={
                "event_type": "trade_execution",
                "trade_id": trade_data.get("trade_id"),
                "symbol": trade_data.get("symbol"),
                "side": trade_data.get("side"),
                "amount": trade_data.get("amount"),
                "price": trade_data.get("price"),
                "status": trade_data.get("status")
            }
        )
        
    def log_risk_event(self, risk_data: dict):
        """记录风险事件"""
        self.logger.warning(
            "风险事件",
            extra={
                "event_type": "risk_event",
                "risk_type": risk_data.get("type"),
                "severity": risk_data.get("severity"),
                "message": risk_data.get("message"),
                "action": risk_data.get("action")
            }
        )
        
    def log_system_event(self, event_type: str, message: str, extra_data: dict = None):
        """记录系统事件"""
        log_data = {
            "event_type": event_type,
            "message": message
        }
        if extra_data:
            log_data.update(extra_data)
            
        self.logger.info("系统事件", extra=log_data)


def setup_logger(name: str = "trading_system", 
                level: str = "INFO",
                debug: bool = False,
                log_file: Optional[str] = None) -> logging.Logger:
    """设置日志记录器"""
    
    # 创建日志目录
    if not log_file:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
    
    trading_logger = TradingSystemLogger(name)
    
    # 设置处理器
    console_level = "DEBUG" if debug else level
    trading_logger.setup_handlers(
        console_level=console_level,
        file_level="DEBUG",
        log_file=str(log_file)
    )
    
    return trading_logger.logger


# 全局日志实例
main_logger = setup_logger("main")
ai_logger = setup_logger("ai")
trading_logger = setup_logger("trading")
risk_logger = setup_logger("risk")
data_logger = setup_logger("data")