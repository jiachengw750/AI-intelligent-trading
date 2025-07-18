# -*- coding: utf-8 -*-
"""
投资组合管理器
"""

import asyncio
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import time
import json
from src.utils.helpers.logger import trade_logger
from src.utils.helpers.async_utils import async_utils
from src.risk.control.risk_manager import risk_manager, RiskMetrics
from src.risk.control.position_sizer import create_position_sizer, PositionSizeMethod
from src.core.exceptions.trading_exceptions import PortfolioException, InsufficientFundsException
from config import trading_config


class PositionStatus(Enum):
    """持仓状态"""
    OPEN = "open"
    CLOSED = "closed"
    PARTIAL = "partial"
    PENDING = "pending"


class PositionType(Enum):
    """持仓类型"""
    LONG = "long"
    SHORT = "short"


@dataclass
class Position:
    """持仓信息"""
    symbol: str
    position_type: PositionType
    amount: float
    entry_price: float
    current_price: float
    entry_time: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    status: PositionStatus = PositionStatus.OPEN
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    commission: float = 0.0
    
    @property
    def market_value(self) -> float:
        """市场价值"""
        return self.amount * self.current_price
        
    @property
    def cost_basis(self) -> float:
        """成本基础"""
        return self.amount * self.entry_price
        
    @property
    def pnl_percentage(self) -> float:
        """盈亏百分比"""
        if self.cost_basis == 0:
            return 0.0
        return (self.unrealized_pnl + self.realized_pnl) / self.cost_basis * 100
        
    def update_price(self, new_price: float):
        """更新价格"""
        self.current_price = new_price
        if self.position_type == PositionType.LONG:
            self.unrealized_pnl = (new_price - self.entry_price) * self.amount
        else:
            self.unrealized_pnl = (self.entry_price - new_price) * self.amount
            
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "position_type": self.position_type.value,
            "amount": self.amount,
            "entry_price": self.entry_price,
            "current_price": self.current_price,
            "entry_time": self.entry_time,
            "unrealized_pnl": self.unrealized_pnl,
            "realized_pnl": self.realized_pnl,
            "status": self.status.value,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "commission": self.commission,
            "market_value": self.market_value,
            "cost_basis": self.cost_basis,
            "pnl_percentage": self.pnl_percentage
        }


@dataclass
class PortfolioMetrics:
    """投资组合指标"""
    total_value: float = 0.0
    cash_balance: float = 0.0
    invested_amount: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    total_pnl: float = 0.0
    pnl_percentage: float = 0.0
    num_positions: int = 0
    num_winning_positions: int = 0
    num_losing_positions: int = 0
    win_rate: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_value": self.total_value,
            "cash_balance": self.cash_balance,
            "invested_amount": self.invested_amount,
            "unrealized_pnl": self.unrealized_pnl,
            "realized_pnl": self.realized_pnl,
            "total_pnl": self.total_pnl,
            "pnl_percentage": self.pnl_percentage,
            "num_positions": self.num_positions,
            "num_winning_positions": self.num_winning_positions,
            "num_losing_positions": self.num_losing_positions,
            "win_rate": self.win_rate,
            "largest_win": self.largest_win,
            "largest_loss": self.largest_loss,
            "avg_win": self.avg_win,
            "avg_loss": self.avg_loss,
            "profit_factor": self.profit_factor
        }


class PortfolioManager:
    """投资组合管理器"""
    
    def __init__(self, initial_cash: float = 100000.0):
        self.initial_cash = initial_cash
        self.cash_balance = initial_cash
        self.positions: Dict[str, Position] = {}
        self.closed_positions: List[Position] = []
        self.transaction_history: List[Dict[str, Any]] = []
        
        # 风险管理
        self.position_sizer = create_position_sizer(risk_manager)
        
        # 性能追踪
        self.value_history: List[Dict[str, Any]] = []
        self.last_update_time = time.time()
        
        # 配置
        self.max_positions = 20
        self.commission_rate = 0.001  # 0.1%
        
    async def update_positions_price(self, price_data: Dict[str, float]):
        """更新持仓价格"""
        try:
            for symbol, position in self.positions.items():
                if symbol in price_data:
                    position.update_price(price_data[symbol])
                    
            # 记录投资组合价值历史
            await self._record_portfolio_value()
            
        except Exception as e:
            trade_logger.error(f"更新持仓价格失败: {e}")
            
    async def _record_portfolio_value(self):
        """记录投资组合价值"""
        try:
            metrics = await self.get_portfolio_metrics()
            
            value_record = {
                "timestamp": time.time(),
                "total_value": metrics.total_value,
                "cash_balance": metrics.cash_balance,
                "invested_amount": metrics.invested_amount,
                "unrealized_pnl": metrics.unrealized_pnl,
                "realized_pnl": metrics.realized_pnl
            }
            
            self.value_history.append(value_record)
            
            # 限制历史记录大小
            if len(self.value_history) > 10000:
                self.value_history = self.value_history[-10000:]
                
        except Exception as e:
            trade_logger.error(f"记录投资组合价值失败: {e}")
            
    async def open_position(self, symbol: str, position_type: PositionType,
                          entry_price: float, amount: float,
                          stop_loss: Optional[float] = None,
                          take_profit: Optional[float] = None) -> Optional[str]:
        """开仓"""
        try:
            trade_logger.info(f"尝试开仓: {symbol} {position_type.value} {amount} @ {entry_price}")
            
            # 检查是否已有相同交易对的持仓
            if symbol in self.positions:
                existing_position = self.positions[symbol]
                if existing_position.position_type == position_type:
                    # 增加持仓
                    return await self._increase_position(symbol, amount, entry_price)
                else:
                    # 相反方向，可能是平仓或反向操作
                    return await self._handle_opposite_position(symbol, position_type, amount, entry_price)
                    
            # 检查资金充足性
            required_amount = amount * entry_price
            commission = required_amount * self.commission_rate
            total_cost = required_amount + commission
            
            if total_cost > self.cash_balance:
                raise InsufficientFundsException(f"资金不足: 需要 {total_cost:.2f}, 可用 {self.cash_balance:.2f}")
                
            # 检查最大持仓数量
            if len(self.positions) >= self.max_positions:
                raise PortfolioException(f"已达到最大持仓数量: {self.max_positions}")
                
            # 风险检查
            trade_params = {
                "symbol": symbol,
                "amount": amount,
                "price": entry_price,
                "stop_loss": stop_loss
            }
            
            portfolio_data = await self._get_portfolio_data()
            validation_result = await risk_manager.validate_trade(trade_params, portfolio_data)
            
            if not validation_result[0]:
                raise PortfolioException(f"风险检查失败: {validation_result[1]}")
                
            # 创建持仓
            position = Position(
                symbol=symbol,
                position_type=position_type,
                amount=amount,
                entry_price=entry_price,
                current_price=entry_price,
                entry_time=time.time(),
                stop_loss=stop_loss,
                take_profit=take_profit,
                commission=commission
            )
            
            # 更新现金余额
            self.cash_balance -= total_cost
            
            # 添加到持仓
            self.positions[symbol] = position
            
            # 记录交易历史
            transaction = {
                "timestamp": time.time(),
                "type": "open_position",
                "symbol": symbol,
                "position_type": position_type.value,
                "amount": amount,
                "price": entry_price,
                "commission": commission,
                "stop_loss": stop_loss,
                "take_profit": take_profit
            }
            
            self.transaction_history.append(transaction)
            
            trade_logger.info(f"开仓成功: {symbol} {position_type.value} {amount} @ {entry_price}")
            
            return symbol
            
        except Exception as e:
            trade_logger.error(f"开仓失败: {e}")
            raise
            
    async def _increase_position(self, symbol: str, additional_amount: float, 
                               entry_price: float) -> str:
        """增加持仓"""
        try:
            position = self.positions[symbol]
            
            # 计算加权平均价格
            total_amount = position.amount + additional_amount
            weighted_price = (position.entry_price * position.amount + 
                            entry_price * additional_amount) / total_amount
            
            # 检查资金充足性
            required_amount = additional_amount * entry_price
            commission = required_amount * self.commission_rate
            total_cost = required_amount + commission
            
            if total_cost > self.cash_balance:
                raise InsufficientFundsException(f"资金不足: 需要 {total_cost:.2f}, 可用 {self.cash_balance:.2f}")
                
            # 更新持仓
            position.amount = total_amount
            position.entry_price = weighted_price
            position.commission += commission
            
            # 更新现金余额
            self.cash_balance -= total_cost
            
            # 记录交易历史
            transaction = {
                "timestamp": time.time(),
                "type": "increase_position",
                "symbol": symbol,
                "amount": additional_amount,
                "price": entry_price,
                "commission": commission,
                "new_total_amount": total_amount,
                "new_avg_price": weighted_price
            }
            
            self.transaction_history.append(transaction)
            
            trade_logger.info(f"增加持仓成功: {symbol} +{additional_amount} @ {entry_price}")
            
            return symbol
            
        except Exception as e:
            trade_logger.error(f"增加持仓失败: {e}")
            raise
            
    async def _handle_opposite_position(self, symbol: str, position_type: PositionType,
                                      amount: float, price: float) -> str:
        """处理相反方向的持仓"""
        try:
            existing_position = self.positions[symbol]
            
            if amount >= existing_position.amount:
                # 完全平仓或反向
                await self.close_position(symbol, price, "opposite_trade")
                
                remaining_amount = amount - existing_position.amount
                if remaining_amount > 0:
                    # 开相反方向的新仓
                    await self.open_position(symbol, position_type, price, remaining_amount)
            else:
                # 部分平仓
                await self.close_position(symbol, price, "partial_close", amount)
                
            return symbol
            
        except Exception as e:
            trade_logger.error(f"处理相反持仓失败: {e}")
            raise
            
    async def close_position(self, symbol: str, exit_price: float, 
                           reason: str = "manual", close_amount: Optional[float] = None) -> bool:
        """平仓"""
        try:
            if symbol not in self.positions:
                raise PortfolioException(f"持仓不存在: {symbol}")
                
            position = self.positions[symbol]
            
            # 确定平仓数量
            actual_close_amount = close_amount if close_amount else position.amount
            actual_close_amount = min(actual_close_amount, position.amount)
            
            # 计算盈亏
            if position.position_type == PositionType.LONG:
                pnl = (exit_price - position.entry_price) * actual_close_amount
            else:
                pnl = (position.entry_price - exit_price) * actual_close_amount
                
            # 计算手续费
            close_value = actual_close_amount * exit_price
            commission = close_value * self.commission_rate
            net_pnl = pnl - commission
            
            # 更新现金余额
            self.cash_balance += close_value - commission
            
            # 更新持仓
            if actual_close_amount >= position.amount:
                # 完全平仓
                position.realized_pnl += net_pnl
                position.status = PositionStatus.CLOSED
                
                # 移动到已平仓列表
                self.closed_positions.append(position)
                del self.positions[symbol]
                
                trade_logger.info(f"完全平仓: {symbol} {actual_close_amount} @ {exit_price}, PnL: {net_pnl:.2f}")
                
            else:
                # 部分平仓
                close_ratio = actual_close_amount / position.amount
                position.realized_pnl += net_pnl
                position.amount -= actual_close_amount
                position.commission *= (1 - close_ratio)
                position.status = PositionStatus.PARTIAL
                
                trade_logger.info(f"部分平仓: {symbol} {actual_close_amount} @ {exit_price}, PnL: {net_pnl:.2f}")
                
            # 记录交易历史
            transaction = {
                "timestamp": time.time(),
                "type": "close_position",
                "symbol": symbol,
                "amount": actual_close_amount,
                "price": exit_price,
                "pnl": net_pnl,
                "commission": commission,
                "reason": reason
            }
            
            self.transaction_history.append(transaction)
            
            return True
            
        except Exception as e:
            trade_logger.error(f"平仓失败: {e}")
            raise
            
    async def close_all_positions(self, current_prices: Dict[str, float], 
                                reason: str = "close_all") -> bool:
        """平仓所有持仓"""
        try:
            symbols_to_close = list(self.positions.keys())
            
            for symbol in symbols_to_close:
                if symbol in current_prices:
                    await self.close_position(symbol, current_prices[symbol], reason)
                else:
                    trade_logger.warning(f"无法获取 {symbol} 的当前价格，跳过平仓")
                    
            trade_logger.info(f"已平仓所有持仓，原因: {reason}")
            return True
            
        except Exception as e:
            trade_logger.error(f"平仓所有持仓失败: {e}")
            return False
            
    async def get_portfolio_metrics(self) -> PortfolioMetrics:
        """获取投资组合指标"""
        try:
            metrics = PortfolioMetrics()
            
            # 基础指标
            metrics.cash_balance = self.cash_balance
            
            # 计算持仓价值和盈亏
            invested_amount = 0
            unrealized_pnl = 0
            
            for position in self.positions.values():
                invested_amount += position.cost_basis
                unrealized_pnl += position.unrealized_pnl
                
            metrics.invested_amount = invested_amount
            metrics.unrealized_pnl = unrealized_pnl
            
            # 计算已实现盈亏
            realized_pnl = sum(pos.realized_pnl for pos in self.closed_positions)
            realized_pnl += sum(pos.realized_pnl for pos in self.positions.values())
            metrics.realized_pnl = realized_pnl
            
            # 总盈亏
            metrics.total_pnl = unrealized_pnl + realized_pnl
            metrics.total_value = self.cash_balance + invested_amount + unrealized_pnl
            
            # 盈亏百分比
            if self.initial_cash > 0:
                metrics.pnl_percentage = metrics.total_pnl / self.initial_cash * 100
                
            # 持仓统计
            metrics.num_positions = len(self.positions)
            
            # 交易统计
            all_closed_positions = [pos for pos in self.closed_positions if pos.status == PositionStatus.CLOSED]
            
            winning_positions = [pos for pos in all_closed_positions if pos.realized_pnl > 0]
            losing_positions = [pos for pos in all_closed_positions if pos.realized_pnl < 0]
            
            metrics.num_winning_positions = len(winning_positions)
            metrics.num_losing_positions = len(losing_positions)
            
            total_trades = len(all_closed_positions)
            if total_trades > 0:
                metrics.win_rate = len(winning_positions) / total_trades * 100
                
                if winning_positions:
                    metrics.largest_win = max(pos.realized_pnl for pos in winning_positions)
                    metrics.avg_win = sum(pos.realized_pnl for pos in winning_positions) / len(winning_positions)
                    
                if losing_positions:
                    metrics.largest_loss = min(pos.realized_pnl for pos in losing_positions)
                    metrics.avg_loss = sum(pos.realized_pnl for pos in losing_positions) / len(losing_positions)
                    
                # 盈亏比
                total_wins = sum(pos.realized_pnl for pos in winning_positions)
                total_losses = abs(sum(pos.realized_pnl for pos in losing_positions))
                
                if total_losses > 0:
                    metrics.profit_factor = total_wins / total_losses
                    
            return metrics
            
        except Exception as e:
            trade_logger.error(f"获取投资组合指标失败: {e}")
            return PortfolioMetrics()
            
    async def _get_portfolio_data(self) -> Dict[str, Any]:
        """获取投资组合数据（用于风险检查）"""
        try:
            metrics = await self.get_portfolio_metrics()
            
            positions_data = {}
            for symbol, position in self.positions.items():
                positions_data[symbol] = {
                    "amount": position.amount,
                    "value": position.market_value,
                    "entry_price": position.entry_price,
                    "current_price": position.current_price,
                    "unrealized_pnl": position.unrealized_pnl
                }
                
            return {
                "total_value": metrics.total_value,
                "cash_balance": metrics.cash_balance,
                "invested_amount": metrics.invested_amount,
                "positions": positions_data
            }
            
        except Exception as e:
            trade_logger.error(f"获取投资组合数据失败: {e}")
            return {}
            
    def get_position(self, symbol: str) -> Optional[Position]:
        """获取持仓"""
        return self.positions.get(symbol)
        
    def get_all_positions(self) -> Dict[str, Position]:
        """获取所有持仓"""
        return self.positions.copy()
        
    def get_closed_positions(self, limit: int = 100) -> List[Position]:
        """获取已平仓列表"""
        return self.closed_positions[-limit:]
        
    def get_transaction_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取交易历史"""
        return self.transaction_history[-limit:]
        
    def get_value_history(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """获取价值历史"""
        return self.value_history[-limit:]
        
    async def calculate_position_size(self, symbol: str, entry_price: float,
                                    method: PositionSizeMethod = PositionSizeMethod.RISK_PARITY,
                                    trade_params: Dict[str, Any] = None) -> float:
        """计算建议仓位大小"""
        try:
            if not trade_params:
                trade_params = {}
                
            trade_params.update({
                "symbol": symbol,
                "entry_price": entry_price
            })
            
            # 获取当前投资组合价值
            metrics = await self.get_portfolio_metrics()
            account_balance = metrics.total_value
            
            # 计算仓位大小
            result = self.position_sizer.calculate_position_size(
                method, account_balance, trade_params
            )
            
            trade_logger.debug(f"计算仓位大小: {symbol} @ {entry_price}, 建议: {result.recommended_size}")
            
            return result.recommended_size
            
        except Exception as e:
            trade_logger.error(f"计算仓位大小失败: {e}")
            return 0.0
            
    def reset_portfolio(self, initial_cash: float = None):
        """重置投资组合"""
        try:
            if initial_cash is not None:
                self.initial_cash = initial_cash
                
            self.cash_balance = self.initial_cash
            self.positions.clear()
            self.closed_positions.clear()
            self.transaction_history.clear()
            self.value_history.clear()
            
            trade_logger.info(f"投资组合已重置，初始资金: {self.initial_cash}")
            
        except Exception as e:
            trade_logger.error(f"重置投资组合失败: {e}")
            
    def export_portfolio_summary(self) -> Dict[str, Any]:
        """导出投资组合摘要"""
        try:
            metrics = asyncio.run(self.get_portfolio_metrics())
            
            return {
                "portfolio_metrics": metrics.to_dict(),
                "positions": {symbol: pos.to_dict() for symbol, pos in self.positions.items()},
                "recent_transactions": self.get_transaction_history(20),
                "performance_summary": {
                    "initial_cash": self.initial_cash,
                    "current_value": metrics.total_value,
                    "total_return": metrics.total_pnl,
                    "return_percentage": metrics.pnl_percentage,
                    "num_trades": len(self.closed_positions),
                    "win_rate": metrics.win_rate,
                    "profit_factor": metrics.profit_factor
                }
            }
            
        except Exception as e:
            trade_logger.error(f"导出投资组合摘要失败: {e}")
            return {}


# 创建全局投资组合管理器
portfolio_manager = PortfolioManager()