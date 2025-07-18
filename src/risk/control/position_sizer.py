# -*- coding: utf-8 -*-
"""
仓位规模计算器
"""

import numpy as np
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import time
from src.utils.helpers.logger import risk_logger
from src.risk.control.risk_manager import RiskManager
from config import trading_config


class PositionSizeMethod(Enum):
    """仓位规模计算方法"""
    FIXED_AMOUNT = "fixed_amount"
    FIXED_PERCENTAGE = "fixed_percentage"
    KELLY_CRITERION = "kelly_criterion"
    VOLATILITY_ADJUSTED = "volatility_adjusted"
    RISK_PARITY = "risk_parity"
    OPTIMAL_F = "optimal_f"


@dataclass
class PositionSizeResult:
    """仓位规模计算结果"""
    recommended_size: float
    max_size: float
    min_size: float
    confidence: float
    method: PositionSizeMethod
    risk_amount: float
    reasoning: str
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "recommended_size": self.recommended_size,
            "max_size": self.max_size,
            "min_size": self.min_size,
            "confidence": self.confidence,
            "method": self.method.value,
            "risk_amount": self.risk_amount,
            "reasoning": self.reasoning
        }


class PositionSizer:
    """仓位规模计算器"""
    
    def __init__(self, risk_manager: RiskManager):
        self.risk_manager = risk_manager
        
        # 默认参数
        self.default_risk_per_trade = 0.02  # 2%
        self.max_position_size = 0.1  # 10%
        self.min_position_size = 0.001  # 0.1%
        self.volatility_lookback = 30  # 30天
        
    def calculate_position_size(self, 
                              method: PositionSizeMethod,
                              account_balance: float,
                              trade_params: Dict[str, Any],
                              market_data: Dict[str, Any] = None) -> PositionSizeResult:
        """计算仓位规模"""
        try:
            risk_logger.debug(f"计算仓位规模: {method.value}")
            
            if method == PositionSizeMethod.FIXED_AMOUNT:
                return self._calculate_fixed_amount(account_balance, trade_params)
            elif method == PositionSizeMethod.FIXED_PERCENTAGE:
                return self._calculate_fixed_percentage(account_balance, trade_params)
            elif method == PositionSizeMethod.KELLY_CRITERION:
                return self._calculate_kelly_criterion(account_balance, trade_params, market_data)
            elif method == PositionSizeMethod.VOLATILITY_ADJUSTED:
                return self._calculate_volatility_adjusted(account_balance, trade_params, market_data)
            elif method == PositionSizeMethod.RISK_PARITY:
                return self._calculate_risk_parity(account_balance, trade_params, market_data)
            elif method == PositionSizeMethod.OPTIMAL_F:
                return self._calculate_optimal_f(account_balance, trade_params, market_data)
            else:
                return self._calculate_fixed_percentage(account_balance, trade_params)
                
        except Exception as e:
            risk_logger.error(f"计算仓位规模失败: {e}")
            return PositionSizeResult(
                recommended_size=self.min_position_size,
                max_size=self.max_position_size,
                min_size=self.min_position_size,
                confidence=0.0,
                method=method,
                risk_amount=0.0,
                reasoning=f"计算失败: {str(e)}"
            )
            
    def _calculate_fixed_amount(self, account_balance: float, 
                              trade_params: Dict[str, Any]) -> PositionSizeResult:
        """固定金额法"""
        try:
            fixed_amount = trade_params.get("fixed_amount", 1000)
            current_price = trade_params.get("entry_price", 0)
            
            if current_price <= 0:
                raise ValueError("价格必须大于0")
                
            position_size = fixed_amount / current_price
            position_percentage = fixed_amount / account_balance
            
            # 应用限制
            position_percentage = max(self.min_position_size, 
                                    min(self.max_position_size, position_percentage))
            
            final_size = position_percentage * account_balance / current_price
            
            return PositionSizeResult(
                recommended_size=final_size,
                max_size=self.max_position_size * account_balance / current_price,
                min_size=self.min_position_size * account_balance / current_price,
                confidence=1.0,
                method=PositionSizeMethod.FIXED_AMOUNT,
                risk_amount=fixed_amount,
                reasoning=f"固定金额 {fixed_amount} 计算的仓位"
            )
            
        except Exception as e:
            risk_logger.error(f"固定金额法计算失败: {e}")
            raise
            
    def _calculate_fixed_percentage(self, account_balance: float, 
                                  trade_params: Dict[str, Any]) -> PositionSizeResult:
        """固定百分比法"""
        try:
            fixed_percentage = trade_params.get("fixed_percentage", 0.05)  # 5%
            current_price = trade_params.get("entry_price", 0)
            
            if current_price <= 0:
                raise ValueError("价格必须大于0")
                
            # 应用限制
            position_percentage = max(self.min_position_size, 
                                    min(self.max_position_size, fixed_percentage))
            
            position_amount = position_percentage * account_balance
            position_size = position_amount / current_price
            
            return PositionSizeResult(
                recommended_size=position_size,
                max_size=self.max_position_size * account_balance / current_price,
                min_size=self.min_position_size * account_balance / current_price,
                confidence=1.0,
                method=PositionSizeMethod.FIXED_PERCENTAGE,
                risk_amount=position_amount,
                reasoning=f"固定百分比 {position_percentage:.2%} 计算的仓位"
            )
            
        except Exception as e:
            risk_logger.error(f"固定百分比法计算失败: {e}")
            raise
            
    def _calculate_kelly_criterion(self, account_balance: float, 
                                 trade_params: Dict[str, Any],
                                 market_data: Dict[str, Any] = None) -> PositionSizeResult:
        """凯利公式法"""
        try:
            # 需要胜率和平均盈亏比
            win_rate = trade_params.get("win_rate", 0.5)
            avg_win = trade_params.get("avg_win", 0.02)
            avg_loss = trade_params.get("avg_loss", 0.01)
            current_price = trade_params.get("entry_price", 0)
            
            if current_price <= 0:
                raise ValueError("价格必须大于0")
                
            if avg_loss <= 0:
                raise ValueError("平均损失必须大于0")
                
            # 计算赔率
            odds = avg_win / avg_loss
            
            # 凯利公式: f = (bp - q) / b
            # 其中 b = 赔率, p = 胜率, q = 败率
            kelly_fraction = (odds * win_rate - (1 - win_rate)) / odds
            
            # 凯利公式可能给出负值或过大值，需要调整
            kelly_fraction = max(0, min(kelly_fraction, 0.25))  # 限制最大25%
            
            # 保守调整（通常使用1/4 Kelly）
            conservative_kelly = kelly_fraction * 0.25
            
            # 应用整体限制
            position_percentage = max(self.min_position_size, 
                                    min(self.max_position_size, conservative_kelly))
            
            position_amount = position_percentage * account_balance
            position_size = position_amount / current_price
            
            return PositionSizeResult(
                recommended_size=position_size,
                max_size=self.max_position_size * account_balance / current_price,
                min_size=self.min_position_size * account_balance / current_price,
                confidence=0.8,
                method=PositionSizeMethod.KELLY_CRITERION,
                risk_amount=position_amount,
                reasoning=f"凯利公式计算: 胜率={win_rate:.2%}, 赔率={odds:.2f}, 凯利比例={kelly_fraction:.2%}"
            )
            
        except Exception as e:
            risk_logger.error(f"凯利公式法计算失败: {e}")
            raise
            
    def _calculate_volatility_adjusted(self, account_balance: float, 
                                     trade_params: Dict[str, Any],
                                     market_data: Dict[str, Any] = None) -> PositionSizeResult:
        """波动率调整法"""
        try:
            current_price = trade_params.get("entry_price", 0)
            target_volatility = trade_params.get("target_volatility", 0.15)  # 15%
            
            if current_price <= 0:
                raise ValueError("价格必须大于0")
                
            # 获取历史波动率
            historical_volatility = self._get_historical_volatility(
                trade_params.get("symbol", ""),
                market_data
            )
            
            if historical_volatility <= 0:
                historical_volatility = 0.2  # 默认20%
                
            # 波动率调整因子
            volatility_adjustment = target_volatility / historical_volatility
            
            # 基础仓位（基于风险预算）
            risk_amount = account_balance * self.default_risk_per_trade
            base_position_percentage = risk_amount / account_balance
            
            # 波动率调整后的仓位
            adjusted_percentage = base_position_percentage * volatility_adjustment
            
            # 应用限制
            position_percentage = max(self.min_position_size, 
                                    min(self.max_position_size, adjusted_percentage))
            
            position_amount = position_percentage * account_balance
            position_size = position_amount / current_price
            
            return PositionSizeResult(
                recommended_size=position_size,
                max_size=self.max_position_size * account_balance / current_price,
                min_size=self.min_position_size * account_balance / current_price,
                confidence=0.7,
                method=PositionSizeMethod.VOLATILITY_ADJUSTED,
                risk_amount=position_amount,
                reasoning=f"波动率调整: 历史波动率={historical_volatility:.2%}, 目标波动率={target_volatility:.2%}, 调整因子={volatility_adjustment:.2f}"
            )
            
        except Exception as e:
            risk_logger.error(f"波动率调整法计算失败: {e}")
            raise
            
    def _calculate_risk_parity(self, account_balance: float, 
                             trade_params: Dict[str, Any],
                             market_data: Dict[str, Any] = None) -> PositionSizeResult:
        """风险平价法"""
        try:
            current_price = trade_params.get("entry_price", 0)
            stop_loss = trade_params.get("stop_loss", 0)
            
            if current_price <= 0:
                raise ValueError("价格必须大于0")
                
            # 计算每股风险
            if stop_loss > 0:
                risk_per_share = abs(current_price - stop_loss)
            else:
                # 如果没有止损，使用ATR或波动率估算
                historical_volatility = self._get_historical_volatility(
                    trade_params.get("symbol", ""),
                    market_data
                )
                risk_per_share = current_price * historical_volatility * 0.1  # 10%的日波动
                
            if risk_per_share <= 0:
                risk_per_share = current_price * 0.02  # 默认2%
                
            # 风险预算
            risk_budget = account_balance * self.default_risk_per_trade
            
            # 计算仓位大小
            position_size = risk_budget / risk_per_share
            
            # 转换为百分比
            position_amount = position_size * current_price
            position_percentage = position_amount / account_balance
            
            # 应用限制
            position_percentage = max(self.min_position_size, 
                                    min(self.max_position_size, position_percentage))
            
            final_size = position_percentage * account_balance / current_price
            
            return PositionSizeResult(
                recommended_size=final_size,
                max_size=self.max_position_size * account_balance / current_price,
                min_size=self.min_position_size * account_balance / current_price,
                confidence=0.9,
                method=PositionSizeMethod.RISK_PARITY,
                risk_amount=risk_budget,
                reasoning=f"风险平价法: 每股风险={risk_per_share:.4f}, 风险预算={risk_budget:.2f}"
            )
            
        except Exception as e:
            risk_logger.error(f"风险平价法计算失败: {e}")
            raise
            
    def _calculate_optimal_f(self, account_balance: float, 
                           trade_params: Dict[str, Any],
                           market_data: Dict[str, Any] = None) -> PositionSizeResult:
        """最优F法"""
        try:
            # 需要历史交易结果
            historical_returns = trade_params.get("historical_returns", [])
            current_price = trade_params.get("entry_price", 0)
            
            if current_price <= 0:
                raise ValueError("价格必须大于0")
                
            if not historical_returns or len(historical_returns) < 10:
                # 如果没有足够的历史数据，回退到固定百分比
                return self._calculate_fixed_percentage(account_balance, trade_params)
                
            # 计算最优F
            optimal_f = self._calculate_optimal_f_value(historical_returns)
            
            # 保守调整
            conservative_f = optimal_f * 0.5
            
            # 应用限制
            position_percentage = max(self.min_position_size, 
                                    min(self.max_position_size, conservative_f))
            
            position_amount = position_percentage * account_balance
            position_size = position_amount / current_price
            
            return PositionSizeResult(
                recommended_size=position_size,
                max_size=self.max_position_size * account_balance / current_price,
                min_size=self.min_position_size * account_balance / current_price,
                confidence=0.6,
                method=PositionSizeMethod.OPTIMAL_F,
                risk_amount=position_amount,
                reasoning=f"最优F法: 最优F={optimal_f:.2%}, 保守调整后={conservative_f:.2%}"
            )
            
        except Exception as e:
            risk_logger.error(f"最优F法计算失败: {e}")
            raise
            
    def _calculate_optimal_f_value(self, returns: list) -> float:
        """计算最优F值"""
        try:
            if not returns:
                return 0.05  # 默认5%
                
            # 简化的最优F计算
            # 在实际应用中，这需要更复杂的数值优化
            
            # 计算几何平均收益
            geometric_mean = np.prod(1 + np.array(returns)) ** (1/len(returns)) - 1
            
            # 计算方差
            variance = np.var(returns)
            
            if variance <= 0:
                return 0.05
                
            # 简化的最优F公式
            optimal_f = max(0, min(0.25, geometric_mean / variance))
            
            return optimal_f
            
        except Exception as e:
            risk_logger.error(f"计算最优F值失败: {e}")
            return 0.05
            
    def _get_historical_volatility(self, symbol: str, 
                                 market_data: Dict[str, Any] = None) -> float:
        """获取历史波动率"""
        try:
            if market_data and "volatility" in market_data:
                return market_data["volatility"]
                
            # 这里可以从数据库或其他数据源获取历史波动率
            # 暂时返回默认值
            return 0.2  # 20%
            
        except Exception as e:
            risk_logger.error(f"获取历史波动率失败: {e}")
            return 0.2
            
    def calculate_optimal_position_size(self, account_balance: float,
                                      trade_params: Dict[str, Any],
                                      market_data: Dict[str, Any] = None) -> PositionSizeResult:
        """计算最优仓位大小（综合多种方法）"""
        try:
            # 计算多种方法的结果
            methods = [
                PositionSizeMethod.RISK_PARITY,
                PositionSizeMethod.VOLATILITY_ADJUSTED,
                PositionSizeMethod.KELLY_CRITERION
            ]
            
            results = []
            
            for method in methods:
                try:
                    result = self.calculate_position_size(method, account_balance, trade_params, market_data)
                    results.append(result)
                except Exception as e:
                    risk_logger.warning(f"方法 {method.value} 计算失败: {e}")
                    
            if not results:
                # 如果所有方法都失败，使用固定百分比
                return self.calculate_position_size(
                    PositionSizeMethod.FIXED_PERCENTAGE,
                    account_balance,
                    trade_params,
                    market_data
                )
                
            # 加权平均
            weights = [0.4, 0.3, 0.3]  # 风险平价权重更高
            
            weighted_size = 0
            weighted_confidence = 0
            
            for i, result in enumerate(results):
                if i < len(weights):
                    weighted_size += result.recommended_size * weights[i]
                    weighted_confidence += result.confidence * weights[i]
                    
            # 应用整体限制
            current_price = trade_params.get("entry_price", 0)
            if current_price > 0:
                position_amount = weighted_size * current_price
                position_percentage = position_amount / account_balance
                
                position_percentage = max(self.min_position_size, 
                                        min(self.max_position_size, position_percentage))
                
                final_size = position_percentage * account_balance / current_price
            else:
                final_size = weighted_size
                
            return PositionSizeResult(
                recommended_size=final_size,
                max_size=self.max_position_size * account_balance / current_price if current_price > 0 else 0,
                min_size=self.min_position_size * account_balance / current_price if current_price > 0 else 0,
                confidence=weighted_confidence,
                method=PositionSizeMethod.RISK_PARITY,  # 主要方法
                risk_amount=final_size * current_price if current_price > 0 else 0,
                reasoning="综合多种方法的加权平均结果"
            )
            
        except Exception as e:
            risk_logger.error(f"计算最优仓位大小失败: {e}")
            return self.calculate_position_size(
                PositionSizeMethod.FIXED_PERCENTAGE,
                account_balance,
                trade_params,
                market_data
            )
            
    def validate_position_size(self, position_size: float, 
                             account_balance: float,
                             trade_params: Dict[str, Any]) -> Tuple[bool, str]:
        """验证仓位大小"""
        try:
            current_price = trade_params.get("entry_price", 0)
            
            if current_price <= 0:
                return False, "价格必须大于0"
                
            position_amount = position_size * current_price
            position_percentage = position_amount / account_balance
            
            # 检查最小仓位
            if position_percentage < self.min_position_size:
                return False, f"仓位过小: {position_percentage:.2%} < {self.min_position_size:.2%}"
                
            # 检查最大仓位
            if position_percentage > self.max_position_size:
                return False, f"仓位过大: {position_percentage:.2%} > {self.max_position_size:.2%}"
                
            # 检查资金充足性
            if position_amount > account_balance:
                return False, f"资金不足: 需要 {position_amount:.2f}, 可用 {account_balance:.2f}"
                
            return True, "仓位大小验证通过"
            
        except Exception as e:
            risk_logger.error(f"验证仓位大小失败: {e}")
            return False, f"验证失败: {str(e)}"
            
    def get_position_size_recommendation(self, account_balance: float,
                                       trade_params: Dict[str, Any],
                                       market_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """获取仓位大小推荐"""
        try:
            # 计算最优仓位
            optimal_result = self.calculate_optimal_position_size(
                account_balance, trade_params, market_data
            )
            
            # 计算各种方法的结果作为参考
            methods = [
                PositionSizeMethod.FIXED_PERCENTAGE,
                PositionSizeMethod.RISK_PARITY,
                PositionSizeMethod.VOLATILITY_ADJUSTED,
                PositionSizeMethod.KELLY_CRITERION
            ]
            
            method_results = {}
            
            for method in methods:
                try:
                    result = self.calculate_position_size(method, account_balance, trade_params, market_data)
                    method_results[method.value] = result.to_dict()
                except Exception as e:
                    risk_logger.warning(f"方法 {method.value} 计算失败: {e}")
                    
            return {
                "optimal_result": optimal_result.to_dict(),
                "method_results": method_results,
                "recommendation": {
                    "position_size": optimal_result.recommended_size,
                    "confidence": optimal_result.confidence,
                    "risk_amount": optimal_result.risk_amount,
                    "reasoning": optimal_result.reasoning
                }
            }
            
        except Exception as e:
            risk_logger.error(f"获取仓位大小推荐失败: {e}")
            return {
                "error": str(e),
                "recommendation": {
                    "position_size": 0,
                    "confidence": 0,
                    "risk_amount": 0,
                    "reasoning": "计算失败"
                }
            }


# 创建仓位规模计算器工厂函数
def create_position_sizer(risk_manager: RiskManager) -> PositionSizer:
    """创建仓位规模计算器"""
    return PositionSizer(risk_manager)