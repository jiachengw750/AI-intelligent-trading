# -*- coding: utf-8 -*-
"""
数据验证器模块
"""

import re
from typing import Any, Dict, List, Optional, Union
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, validator
from src.utils.helpers.logger import main_logger


class MarketDataValidator:
    """市场数据验证器"""
    
    @staticmethod
    def validate_symbol(symbol: str) -> bool:
        """验证交易对符号"""
        if not isinstance(symbol, str):
            return False
            
        # 检查格式 (例如: BTC/USDT, ETH/BTC)
        pattern = r'^[A-Z]{2,10}/[A-Z]{2,10}$'
        return bool(re.match(pattern, symbol))
        
    @staticmethod
    def validate_price(price: Union[float, str, Decimal]) -> bool:
        """验证价格"""
        try:
            price_decimal = Decimal(str(price))
            return price_decimal > 0
        except (ValueError, TypeError):
            return False
            
    @staticmethod
    def validate_volume(volume: Union[float, str, Decimal]) -> bool:
        """验证成交量"""
        try:
            volume_decimal = Decimal(str(volume))
            return volume_decimal >= 0
        except (ValueError, TypeError):
            return False
            
    @staticmethod
    def validate_timestamp(timestamp: Union[int, float, datetime]) -> bool:
        """验证时间戳"""
        try:
            if isinstance(timestamp, datetime):
                return True
            elif isinstance(timestamp, (int, float)):
                # 检查是否为合理的Unix时间戳
                if timestamp < 0:
                    return False
                # 检查是否在合理范围内（1970-2050年）
                return 0 < timestamp < 2524608000  # 2050年的时间戳
            return False
        except (ValueError, TypeError):
            return False
            
    @staticmethod
    def validate_ohlcv(ohlcv_data: Dict[str, Any]) -> bool:
        """验证OHLCV数据"""
        required_fields = ['open', 'high', 'low', 'close', 'volume']
        
        for field in required_fields:
            if field not in ohlcv_data:
                return False
                
        # 验证价格关系
        try:
            open_price = Decimal(str(ohlcv_data['open']))
            high_price = Decimal(str(ohlcv_data['high']))
            low_price = Decimal(str(ohlcv_data['low']))
            close_price = Decimal(str(ohlcv_data['close']))
            
            # 高价应该是最高的
            if high_price < max(open_price, close_price, low_price):
                return False
                
            # 低价应该是最低的
            if low_price > min(open_price, close_price, high_price):
                return False
                
            # 验证成交量
            if not MarketDataValidator.validate_volume(ohlcv_data['volume']):
                return False
                
            return True
            
        except (ValueError, TypeError):
            return False


class TradingDataValidator:
    """交易数据验证器"""
    
    @staticmethod
    def validate_order_side(side: str) -> bool:
        """验证订单方向"""
        return side.lower() in ['buy', 'sell']
        
    @staticmethod
    def validate_order_type(order_type: str) -> bool:
        """验证订单类型"""
        valid_types = ['market', 'limit', 'stop', 'stop_limit']
        return order_type.lower() in valid_types
        
    @staticmethod
    def validate_order_amount(amount: Union[float, str, Decimal]) -> bool:
        """验证订单数量"""
        try:
            amount_decimal = Decimal(str(amount))
            return amount_decimal > 0
        except (ValueError, TypeError):
            return False
            
    @staticmethod
    def validate_order_data(order_data: Dict[str, Any]) -> bool:
        """验证订单数据"""
        required_fields = ['symbol', 'side', 'amount', 'type']
        
        for field in required_fields:
            if field not in order_data:
                return False
                
        # 验证各字段
        if not MarketDataValidator.validate_symbol(order_data['symbol']):
            return False
            
        if not TradingDataValidator.validate_order_side(order_data['side']):
            return False
            
        if not TradingDataValidator.validate_order_amount(order_data['amount']):
            return False
            
        if not TradingDataValidator.validate_order_type(order_data['type']):
            return False
            
        # 限价单需要价格
        if order_data['type'].lower() in ['limit', 'stop_limit']:
            if 'price' not in order_data:
                return False
            if not MarketDataValidator.validate_price(order_data['price']):
                return False
                
        return True


class AIDataValidator:
    """AI数据验证器"""
    
    @staticmethod
    def validate_confidence(confidence: Union[float, int]) -> bool:
        """验证置信度"""
        try:
            conf_float = float(confidence)
            return 0 <= conf_float <= 1
        except (ValueError, TypeError):
            return False
            
    @staticmethod
    def validate_decision(decision: str) -> bool:
        """验证AI决策"""
        valid_decisions = ['buy', 'sell', 'hold']
        return decision.lower() in valid_decisions
        
    @staticmethod
    def validate_ai_output(ai_output: Dict[str, Any]) -> bool:
        """验证AI输出"""
        required_fields = ['decision', 'confidence', 'reasoning']
        
        for field in required_fields:
            if field not in ai_output:
                return False
                
        if not AIDataValidator.validate_decision(ai_output['decision']):
            return False
            
        if not AIDataValidator.validate_confidence(ai_output['confidence']):
            return False
            
        if not isinstance(ai_output['reasoning'], str):
            return False
            
        return True


class RiskDataValidator:
    """风险数据验证器"""
    
    @staticmethod
    def validate_risk_level(risk_level: str) -> bool:
        """验证风险等级"""
        valid_levels = ['low', 'medium', 'high', 'critical']
        return risk_level.lower() in valid_levels
        
    @staticmethod
    def validate_risk_score(risk_score: Union[float, int]) -> bool:
        """验证风险评分"""
        try:
            score_float = float(risk_score)
            return 0 <= score_float <= 1
        except (ValueError, TypeError):
            return False
            
    @staticmethod
    def validate_position_size(position_size: Union[float, str, Decimal]) -> bool:
        """验证仓位大小"""
        try:
            size_decimal = Decimal(str(position_size))
            return 0 <= size_decimal <= 1  # 假设仓位以百分比表示
        except (ValueError, TypeError):
            return False


class DataValidationError(Exception):
    """数据验证错误"""
    pass


class DataValidator:
    """统一数据验证器"""
    
    def __init__(self):
        self.market_validator = MarketDataValidator()
        self.trading_validator = TradingDataValidator()
        self.ai_validator = AIDataValidator()
        self.risk_validator = RiskDataValidator()
        
    def validate_data(self, data: Dict[str, Any], data_type: str) -> bool:
        """验证数据"""
        try:
            if data_type == 'market':
                return self.market_validator.validate_ohlcv(data)
            elif data_type == 'order':
                return self.trading_validator.validate_order_data(data)
            elif data_type == 'ai_output':
                return self.ai_validator.validate_ai_output(data)
            elif data_type == 'risk':
                return self.risk_validator.validate_risk_score(data.get('risk_score', 0))
            else:
                main_logger.warning(f"未知的数据类型: {data_type}")
                return False
                
        except Exception as e:
            main_logger.error(f"数据验证异常: {e}")
            return False
            
    def validate_and_raise(self, data: Dict[str, Any], data_type: str) -> None:
        """验证数据，失败时抛出异常"""
        if not self.validate_data(data, data_type):
            raise DataValidationError(f"数据验证失败: {data_type}")


# 全局验证器实例
data_validator = DataValidator()