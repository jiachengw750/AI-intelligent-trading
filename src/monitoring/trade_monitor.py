# -*- coding: utf-8 -*-
"""
交易监控器
"""

import asyncio
import time
import statistics
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, deque
import numpy as np
from src.utils.helpers.logger import trading_logger
from src.utils.helpers.async_utils import async_utils
from src.trading.orders.order_manager import OrderEvent, ManagedOrder


class AlertLevel(Enum):
    """告警级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TradeEventType(Enum):
    """交易事件类型"""
    TRADE_EXECUTION = "trade_execution"
    POSITION_CHANGE = "position_change"
    RISK_ALERT = "risk_alert"
    PROFIT_LOSS = "profit_loss"
    DRAWDOWN = "drawdown"
    PERFORMANCE = "performance"
    SYSTEM_STATUS = "system_status"


@dataclass
class TradeMetrics:
    """交易指标"""
    timestamp: float
    symbol: str
    # 基础指标
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_volume: float = 0.0
    total_pnl: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    
    # 性能指标
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    
    # 风险指标
    position_size: float = 0.0
    exposure: float = 0.0
    var_95: float = 0.0  # 95% VaR
    var_99: float = 0.0  # 99% VaR
    
    # 执行指标
    avg_execution_time: float = 0.0
    avg_slippage: float = 0.0
    order_fill_rate: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp,
            "symbol": self.symbol,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "total_volume": self.total_volume,
            "total_pnl": self.total_pnl,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "win_rate": self.win_rate,
            "avg_win": self.avg_win,
            "avg_loss": self.avg_loss,
            "profit_factor": self.profit_factor,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "current_drawdown": self.current_drawdown,
            "position_size": self.position_size,
            "exposure": self.exposure,
            "var_95": self.var_95,
            "var_99": self.var_99,
            "avg_execution_time": self.avg_execution_time,
            "avg_slippage": self.avg_slippage,
            "order_fill_rate": self.order_fill_rate
        }


@dataclass
class TradeAlert:
    """交易告警"""
    alert_id: str
    alert_type: str
    level: AlertLevel
    message: str
    symbol: str
    timestamp: float
    data: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type,
            "level": self.level.value,
            "message": self.message,
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "data": self.data,
            "is_active": self.is_active
        }


@dataclass
class TradeEvent:
    """交易事件"""
    event_id: str
    event_type: TradeEventType
    symbol: str
    timestamp: float
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "data": self.data
        }


@dataclass
class TradeExecution:
    """交易执行记录"""
    execution_id: str
    symbol: str
    side: str
    amount: float
    price: float
    execution_time: float
    timestamp: float
    order_id: str
    pnl: float = 0.0
    slippage: float = 0.0
    fees: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "execution_id": self.execution_id,
            "symbol": self.symbol,
            "side": self.side,
            "amount": self.amount,
            "price": self.price,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp,
            "order_id": self.order_id,
            "pnl": self.pnl,
            "slippage": self.slippage,
            "fees": self.fees
        }


@dataclass
class PositionInfo:
    """持仓信息"""
    symbol: str
    side: str
    size: float
    avg_price: float
    unrealized_pnl: float
    realized_pnl: float
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "side": self.side,
            "size": self.size,
            "avg_price": self.avg_price,
            "unrealized_pnl": self.unrealized_pnl,
            "realized_pnl": self.realized_pnl,
            "timestamp": self.timestamp
        }


class TradeMonitor:
    """交易监控器"""
    
    def __init__(self, monitoring_interval: float = 1.0):
        self.monitoring_interval = monitoring_interval
        self.is_monitoring = False
        
        # 数据存储
        self.trade_executions: Dict[str, List[TradeExecution]] = defaultdict(list)
        self.position_info: Dict[str, PositionInfo] = {}
        self.trade_metrics: Dict[str, TradeMetrics] = {}
        self.active_alerts: Dict[str, TradeAlert] = {}
        self.trade_events: deque = deque(maxlen=1000)
        
        # 历史数据
        self.metrics_history: Dict[str, List[TradeMetrics]] = defaultdict(list)
        self.pnl_history: Dict[str, List[float]] = defaultdict(list)
        self.drawdown_history: Dict[str, List[float]] = defaultdict(list)
        
        # 统计数据
        self.execution_times: Dict[str, List[float]] = defaultdict(list)
        self.slippage_data: Dict[str, List[float]] = defaultdict(list)
        self.order_fill_rates: Dict[str, List[float]] = defaultdict(list)
        
        # 风险阈值
        self.risk_thresholds = {
            "max_drawdown": 0.10,        # 最大回撤10%
            "position_size_limit": 0.05,  # 单个持仓5%
            "total_exposure_limit": 0.20, # 总敞口20%
            "daily_loss_limit": 0.02,    # 日损失2%
            "var_95_limit": 0.03,        # 95% VaR 3%
            "consecutive_losses": 5,      # 连续亏损次数
            "execution_time_limit": 5.0,  # 执行时间限制5秒
            "slippage_limit": 0.01       # 滑点限制1%
        }
        
        # 性能阈值
        self.performance_thresholds = {
            "min_win_rate": 0.35,         # 最小胜率35%
            "min_profit_factor": 1.2,     # 最小盈利因子1.2
            "min_sharpe_ratio": 0.5,      # 最小夏普比率0.5
            "max_trade_frequency": 1000,  # 最大交易频率
            "min_avg_win": 0.001         # 最小平均盈利
        }
        
        # 回调函数
        self.alert_callbacks: List[Callable] = []
        self.event_callbacks: List[Callable] = []
        
        # 交易统计
        self.start_time = time.time()
        self.daily_stats = self._reset_daily_stats()
        self.total_trades = 0
        self.total_volume = 0.0
        self.total_pnl = 0.0
        
    def _reset_daily_stats(self) -> Dict[str, Any]:
        """重置每日统计"""
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "trades": 0,
            "volume": 0.0,
            "pnl": 0.0,
            "wins": 0,
            "losses": 0,
            "max_drawdown": 0.0,
            "start_balance": 0.0,
            "end_balance": 0.0
        }
        
    def add_alert_callback(self, callback: Callable):
        """添加告警回调"""
        self.alert_callbacks.append(callback)
        trading_logger.info(f"添加交易监控告警回调: {callback.__name__}")
        
    def add_event_callback(self, callback: Callable):
        """添加事件回调"""
        self.event_callbacks.append(callback)
        trading_logger.info(f"添加交易监控事件回调: {callback.__name__}")
        
    async def start_monitoring(self):
        """开始监控"""
        try:
            if self.is_monitoring:
                trading_logger.warning("交易监控已在运行")
                return
                
            self.is_monitoring = True
            self.start_time = time.time()
            
            # 启动监控任务
            asyncio.create_task(self._monitor_trades())
            asyncio.create_task(self._monitor_positions())
            asyncio.create_task(self._monitor_performance())
            asyncio.create_task(self._monitor_risk())
            
            trading_logger.info("交易监控已启动")
            
        except Exception as e:
            trading_logger.error(f"启动交易监控失败: {e}")
            self.is_monitoring = False
            
    async def stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False
        trading_logger.info("交易监控已停止")
        
    async def _monitor_trades(self):
        """监控交易活动"""
        while self.is_monitoring:
            try:
                # 更新交易指标
                await self._update_trade_metrics()
                
                # 检查交易告警
                await self._check_trade_alerts()
                
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                trading_logger.error(f"监控交易活动失败: {e}")
                await asyncio.sleep(self.monitoring_interval)
                
    async def _monitor_positions(self):
        """监控持仓状态"""
        while self.is_monitoring:
            try:
                # 更新持仓信息
                await self._update_position_info()
                
                # 检查持仓告警
                await self._check_position_alerts()
                
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                trading_logger.error(f"监控持仓状态失败: {e}")
                await asyncio.sleep(self.monitoring_interval)
                
    async def _monitor_performance(self):
        """监控性能指标"""
        while self.is_monitoring:
            try:
                # 更新性能指标
                await self._update_performance_metrics()
                
                # 检查性能告警
                await self._check_performance_alerts()
                
                await asyncio.sleep(self.monitoring_interval * 5)  # 性能监控频率较低
                
            except Exception as e:
                trading_logger.error(f"监控性能指标失败: {e}")
                await asyncio.sleep(self.monitoring_interval * 5)
                
    async def _monitor_risk(self):
        """监控风险指标"""
        while self.is_monitoring:
            try:
                # 更新风险指标
                await self._update_risk_metrics()
                
                # 检查风险告警
                await self._check_risk_alerts()
                
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                trading_logger.error(f"监控风险指标失败: {e}")
                await asyncio.sleep(self.monitoring_interval)
                
    async def _update_trade_metrics(self):
        """更新交易指标"""
        try:
            for symbol in self.trade_executions:
                executions = self.trade_executions[symbol]
                
                if not executions:
                    continue
                    
                metrics = self._calculate_trade_metrics(symbol, executions)
                self.trade_metrics[symbol] = metrics
                
                # 更新历史记录
                self.metrics_history[symbol].append(metrics)
                if len(self.metrics_history[symbol]) > 1000:
                    self.metrics_history[symbol] = self.metrics_history[symbol][-1000:]
                    
        except Exception as e:
            trading_logger.error(f"更新交易指标失败: {e}")
            
    def _calculate_trade_metrics(self, symbol: str, executions: List[TradeExecution]) -> TradeMetrics:
        """计算交易指标"""
        try:
            if not executions:
                return TradeMetrics(timestamp=time.time(), symbol=symbol)
                
            # 基础统计
            total_trades = len(executions)
            total_volume = sum(exec.amount for exec in executions)
            total_pnl = sum(exec.pnl for exec in executions)
            
            # 盈亏统计
            winning_trades = sum(1 for exec in executions if exec.pnl > 0)
            losing_trades = sum(1 for exec in executions if exec.pnl < 0)
            
            # 胜率和平均盈亏
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            winning_pnls = [exec.pnl for exec in executions if exec.pnl > 0]
            losing_pnls = [exec.pnl for exec in executions if exec.pnl < 0]
            
            avg_win = statistics.mean(winning_pnls) if winning_pnls else 0
            avg_loss = statistics.mean(losing_pnls) if losing_pnls else 0
            
            # 盈利因子
            total_wins = sum(winning_pnls)
            total_losses = abs(sum(losing_pnls))
            profit_factor = (total_wins / total_losses) if total_losses > 0 else 0
            
            # 夏普比率
            returns = [exec.pnl for exec in executions]
            sharpe_ratio = self._calculate_sharpe_ratio(returns)
            
            # 回撤
            max_drawdown, current_drawdown = self._calculate_drawdown(symbol, returns)
            
            # 执行指标
            execution_times = [exec.execution_time for exec in executions]
            slippages = [exec.slippage for exec in executions]
            
            avg_execution_time = statistics.mean(execution_times) if execution_times else 0
            avg_slippage = statistics.mean(slippages) if slippages else 0
            
            # 持仓信息
            position = self.position_info.get(symbol)
            position_size = position.size if position else 0
            unrealized_pnl = position.unrealized_pnl if position else 0
            
            # 创建指标对象
            metrics = TradeMetrics(
                timestamp=time.time(),
                symbol=symbol,
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                total_volume=total_volume,
                total_pnl=total_pnl,
                realized_pnl=total_pnl,
                unrealized_pnl=unrealized_pnl,
                win_rate=win_rate,
                avg_win=avg_win,
                avg_loss=avg_loss,
                profit_factor=profit_factor,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                current_drawdown=current_drawdown,
                position_size=position_size,
                avg_execution_time=avg_execution_time,
                avg_slippage=avg_slippage
            )
            
            return metrics
            
        except Exception as e:
            trading_logger.error(f"计算交易指标失败: {e}")
            return TradeMetrics(timestamp=time.time(), symbol=symbol)
            
    def _calculate_sharpe_ratio(self, returns: List[float]) -> float:
        """计算夏普比率"""
        try:
            if len(returns) < 2:
                return 0.0
                
            mean_return = statistics.mean(returns)
            std_return = statistics.stdev(returns)
            
            if std_return == 0:
                return 0.0
                
            return mean_return / std_return
            
        except Exception as e:
            trading_logger.error(f"计算夏普比率失败: {e}")
            return 0.0
            
    def _calculate_drawdown(self, symbol: str, returns: List[float]) -> tuple[float, float]:
        """计算回撤"""
        try:
            if len(returns) < 2:
                return 0.0, 0.0
                
            # 计算累计收益
            cumulative_returns = np.cumsum(returns)
            
            # 计算运行最大值
            running_max = np.maximum.accumulate(cumulative_returns)
            
            # 计算回撤
            drawdown = (running_max - cumulative_returns) / (running_max + 1e-8)
            
            max_drawdown = float(np.max(drawdown))
            current_drawdown = float(drawdown[-1])
            
            # 更新回撤历史
            self.drawdown_history[symbol].append(current_drawdown)
            if len(self.drawdown_history[symbol]) > 1000:
                self.drawdown_history[symbol] = self.drawdown_history[symbol][-1000:]
                
            return max_drawdown, current_drawdown
            
        except Exception as e:
            trading_logger.error(f"计算回撤失败: {e}")
            return 0.0, 0.0
            
    async def _update_position_info(self):
        """更新持仓信息"""
        try:
            # 这里应该从交易所或者持仓管理器获取最新持仓信息
            # 暂时使用模拟数据
            pass
            
        except Exception as e:
            trading_logger.error(f"更新持仓信息失败: {e}")
            
    async def _update_performance_metrics(self):
        """更新性能指标"""
        try:
            # 更新每日统计
            current_date = datetime.now().strftime("%Y-%m-%d")
            if self.daily_stats["date"] != current_date:
                self.daily_stats = self._reset_daily_stats()
                
            # 计算整体性能
            all_executions = []
            for symbol_executions in self.trade_executions.values():
                all_executions.extend(symbol_executions)
                
            if all_executions:
                self.total_trades = len(all_executions)
                self.total_volume = sum(exec.amount for exec in all_executions)
                self.total_pnl = sum(exec.pnl for exec in all_executions)
                
                # 更新每日统计
                today_executions = [
                    exec for exec in all_executions 
                    if datetime.fromtimestamp(exec.timestamp).strftime("%Y-%m-%d") == current_date
                ]
                
                if today_executions:
                    self.daily_stats["trades"] = len(today_executions)
                    self.daily_stats["volume"] = sum(exec.amount for exec in today_executions)
                    self.daily_stats["pnl"] = sum(exec.pnl for exec in today_executions)
                    self.daily_stats["wins"] = sum(1 for exec in today_executions if exec.pnl > 0)
                    self.daily_stats["losses"] = sum(1 for exec in today_executions if exec.pnl < 0)
                    
        except Exception as e:
            trading_logger.error(f"更新性能指标失败: {e}")
            
    async def _update_risk_metrics(self):
        """更新风险指标"""
        try:
            for symbol, metrics in self.trade_metrics.items():
                # 计算VaR
                executions = self.trade_executions[symbol]
                if len(executions) >= 30:  # 至少30个交易记录
                    returns = [exec.pnl for exec in executions[-100:]]  # 使用最近100个交易
                    metrics.var_95 = np.percentile(returns, 5)
                    metrics.var_99 = np.percentile(returns, 1)
                    
                # 计算敞口
                position = self.position_info.get(symbol)
                if position:
                    metrics.exposure = abs(position.size * position.avg_price)
                    
        except Exception as e:
            trading_logger.error(f"更新风险指标失败: {e}")
            
    async def _check_trade_alerts(self):
        """检查交易告警"""
        try:
            for symbol, metrics in self.trade_metrics.items():
                alerts = []
                
                # 检查胜率
                if metrics.win_rate < self.performance_thresholds["min_win_rate"] * 100:
                    alerts.append(("low_win_rate", AlertLevel.MEDIUM, 
                                 f"胜率过低: {metrics.win_rate:.1f}%"))
                
                # 检查盈利因子
                if metrics.profit_factor < self.performance_thresholds["min_profit_factor"]:
                    alerts.append(("low_profit_factor", AlertLevel.MEDIUM,
                                 f"盈利因子过低: {metrics.profit_factor:.2f}"))
                
                # 检查夏普比率
                if metrics.sharpe_ratio < self.performance_thresholds["min_sharpe_ratio"]:
                    alerts.append(("low_sharpe_ratio", AlertLevel.LOW,
                                 f"夏普比率过低: {metrics.sharpe_ratio:.2f}"))
                
                # 发送告警
                for alert_type, level, message in alerts:
                    await self._send_alert(alert_type, level, message, symbol, metrics.to_dict())
                    
        except Exception as e:
            trading_logger.error(f"检查交易告警失败: {e}")
            
    async def _check_position_alerts(self):
        """检查持仓告警"""
        try:
            total_exposure = 0.0
            
            for symbol, position in self.position_info.items():
                exposure = abs(position.size * position.avg_price)
                total_exposure += exposure
                
                # 检查单个持仓大小
                if exposure > self.risk_thresholds["position_size_limit"]:
                    await self._send_alert(
                        "large_position", AlertLevel.HIGH,
                        f"持仓过大: {exposure:.2f}",
                        symbol, position.to_dict()
                    )
                    
                # 检查未实现亏损
                if position.unrealized_pnl < -self.risk_thresholds["daily_loss_limit"]:
                    await self._send_alert(
                        "large_unrealized_loss", AlertLevel.HIGH,
                        f"未实现亏损过大: {position.unrealized_pnl:.2f}",
                        symbol, position.to_dict()
                    )
                    
            # 检查总敞口
            if total_exposure > self.risk_thresholds["total_exposure_limit"]:
                await self._send_alert(
                    "high_total_exposure", AlertLevel.CRITICAL,
                    f"总敞口过大: {total_exposure:.2f}",
                    "ALL", {"total_exposure": total_exposure}
                )
                
        except Exception as e:
            trading_logger.error(f"检查持仓告警失败: {e}")
            
    async def _check_performance_alerts(self):
        """检查性能告警"""
        try:
            # 检查每日亏损
            if self.daily_stats["pnl"] < -self.risk_thresholds["daily_loss_limit"]:
                await self._send_alert(
                    "daily_loss_limit", AlertLevel.CRITICAL,
                    f"每日亏损超限: {self.daily_stats['pnl']:.2f}",
                    "ALL", self.daily_stats
                )
                
            # 检查交易频率
            if self.daily_stats["trades"] > self.performance_thresholds["max_trade_frequency"]:
                await self._send_alert(
                    "high_trade_frequency", AlertLevel.MEDIUM,
                    f"交易频率过高: {self.daily_stats['trades']}",
                    "ALL", self.daily_stats
                )
                
        except Exception as e:
            trading_logger.error(f"检查性能告警失败: {e}")
            
    async def _check_risk_alerts(self):
        """检查风险告警"""
        try:
            for symbol, metrics in self.trade_metrics.items():
                # 检查最大回撤
                if metrics.max_drawdown > self.risk_thresholds["max_drawdown"]:
                    await self._send_alert(
                        "max_drawdown_exceeded", AlertLevel.CRITICAL,
                        f"最大回撤超限: {metrics.max_drawdown:.2%}",
                        symbol, metrics.to_dict()
                    )
                    
                # 检查VaR
                if metrics.var_95 < -self.risk_thresholds["var_95_limit"]:
                    await self._send_alert(
                        "var_95_exceeded", AlertLevel.HIGH,
                        f"VaR 95%超限: {metrics.var_95:.2%}",
                        symbol, metrics.to_dict()
                    )
                    
                # 检查执行时间
                if metrics.avg_execution_time > self.risk_thresholds["execution_time_limit"]:
                    await self._send_alert(
                        "slow_execution", AlertLevel.MEDIUM,
                        f"执行时间过长: {metrics.avg_execution_time:.2f}秒",
                        symbol, metrics.to_dict()
                    )
                    
                # 检查滑点
                if abs(metrics.avg_slippage) > self.risk_thresholds["slippage_limit"]:
                    await self._send_alert(
                        "high_slippage", AlertLevel.MEDIUM,
                        f"滑点过大: {metrics.avg_slippage:.2%}",
                        symbol, metrics.to_dict()
                    )
                    
        except Exception as e:
            trading_logger.error(f"检查风险告警失败: {e}")
            
    async def _send_alert(self, alert_type: str, level: AlertLevel, message: str, 
                         symbol: str, data: Dict[str, Any]):
        """发送告警"""
        try:
            alert_id = f"{alert_type}_{symbol}_{int(time.time())}"
            
            # 检查是否已存在相同类型的活跃告警
            existing_alert_key = f"{alert_type}_{symbol}"
            if existing_alert_key in self.active_alerts:
                return
                
            alert = TradeAlert(
                alert_id=alert_id,
                alert_type=alert_type,
                level=level,
                message=message,
                symbol=symbol,
                timestamp=time.time(),
                data=data
            )
            
            self.active_alerts[existing_alert_key] = alert
            
            # 调用告警回调
            for callback in self.alert_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(alert)
                    else:
                        callback(alert)
                except Exception as e:
                    trading_logger.error(f"告警回调执行失败: {e}")
                    
            # 记录告警事件
            await self._record_event(
                TradeEventType.RISK_ALERT,
                symbol,
                {
                    "alert_type": alert_type,
                    "level": level.value,
                    "message": message,
                    "data": data
                }
            )
            
            trading_logger.warning(f"交易告警: {message}")
            
        except Exception as e:
            trading_logger.error(f"发送告警失败: {e}")
            
    async def _record_event(self, event_type: TradeEventType, symbol: str, data: Dict[str, Any]):
        """记录交易事件"""
        try:
            event_id = f"{event_type.value}_{symbol}_{int(time.time())}"
            
            event = TradeEvent(
                event_id=event_id,
                event_type=event_type,
                symbol=symbol,
                timestamp=time.time(),
                data=data
            )
            
            self.trade_events.append(event)
            
            # 调用事件回调
            for callback in self.event_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    trading_logger.error(f"事件回调执行失败: {e}")
                    
        except Exception as e:
            trading_logger.error(f"记录交易事件失败: {e}")
            
    async def record_trade_execution(self, execution: TradeExecution):
        """记录交易执行"""
        try:
            symbol = execution.symbol
            self.trade_executions[symbol].append(execution)
            
            # 限制历史记录大小
            if len(self.trade_executions[symbol]) > 1000:
                self.trade_executions[symbol] = self.trade_executions[symbol][-1000:]
                
            # 更新统计
            self.execution_times[symbol].append(execution.execution_time)
            self.slippage_data[symbol].append(execution.slippage)
            
            # 记录事件
            await self._record_event(
                TradeEventType.TRADE_EXECUTION,
                symbol,
                execution.to_dict()
            )
            
            trading_logger.info(f"记录交易执行: {execution.symbol} {execution.side} {execution.amount}")
            
        except Exception as e:
            trading_logger.error(f"记录交易执行失败: {e}")
            
    async def update_position(self, position: PositionInfo):
        """更新持仓信息"""
        try:
            old_position = self.position_info.get(position.symbol)
            self.position_info[position.symbol] = position
            
            # 记录持仓变化事件
            await self._record_event(
                TradeEventType.POSITION_CHANGE,
                position.symbol,
                {
                    "old_position": old_position.to_dict() if old_position else None,
                    "new_position": position.to_dict()
                }
            )
            
        except Exception as e:
            trading_logger.error(f"更新持仓信息失败: {e}")
            
    def get_trade_metrics(self, symbol: Optional[str] = None) -> Union[Dict[str, TradeMetrics], TradeMetrics]:
        """获取交易指标"""
        if symbol:
            return self.trade_metrics.get(symbol)
        return self.trade_metrics
        
    def get_active_alerts(self, symbol: Optional[str] = None) -> List[TradeAlert]:
        """获取活跃告警"""
        alerts = list(self.active_alerts.values())
        
        if symbol:
            alerts = [alert for alert in alerts if alert.symbol == symbol]
            
        return alerts
        
    def get_trade_events(self, limit: int = 100) -> List[TradeEvent]:
        """获取交易事件"""
        return list(self.trade_events)[-limit:]
        
    def get_position_info(self, symbol: Optional[str] = None) -> Union[Dict[str, PositionInfo], PositionInfo]:
        """获取持仓信息"""
        if symbol:
            return self.position_info.get(symbol)
        return self.position_info
        
    def get_trade_executions(self, symbol: str, limit: int = 100) -> List[TradeExecution]:
        """获取交易执行记录"""
        executions = self.trade_executions.get(symbol, [])
        return executions[-limit:]
        
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        current_time = time.time()
        uptime = current_time - self.start_time
        
        # 计算整体统计
        total_symbols = len(self.trade_metrics)
        total_active_alerts = len(self.active_alerts)
        total_positions = len(self.position_info)
        
        # 计算整体PnL
        total_realized_pnl = sum(metrics.realized_pnl for metrics in self.trade_metrics.values())
        total_unrealized_pnl = sum(metrics.unrealized_pnl for metrics in self.trade_metrics.values())
        
        # 计算平均胜率
        win_rates = [metrics.win_rate for metrics in self.trade_metrics.values() if metrics.total_trades > 0]
        avg_win_rate = statistics.mean(win_rates) if win_rates else 0
        
        return {
            "uptime": uptime,
            "monitoring_status": self.is_monitoring,
            "total_symbols": total_symbols,
            "total_trades": self.total_trades,
            "total_volume": self.total_volume,
            "total_realized_pnl": total_realized_pnl,
            "total_unrealized_pnl": total_unrealized_pnl,
            "total_pnl": total_realized_pnl + total_unrealized_pnl,
            "avg_win_rate": avg_win_rate,
            "active_alerts": total_active_alerts,
            "active_positions": total_positions,
            "daily_stats": self.daily_stats.copy()
        }
        
    def get_risk_summary(self) -> Dict[str, Any]:
        """获取风险摘要"""
        total_exposure = sum(
            abs(pos.size * pos.avg_price) for pos in self.position_info.values()
        )
        
        max_drawdowns = [metrics.max_drawdown for metrics in self.trade_metrics.values()]
        overall_max_drawdown = max(max_drawdowns) if max_drawdowns else 0
        
        current_drawdowns = [metrics.current_drawdown for metrics in self.trade_metrics.values()]
        overall_current_drawdown = max(current_drawdowns) if current_drawdowns else 0
        
        return {
            "total_exposure": total_exposure,
            "max_drawdown": overall_max_drawdown,
            "current_drawdown": overall_current_drawdown,
            "active_alerts": len(self.active_alerts),
            "risk_thresholds": self.risk_thresholds.copy(),
            "performance_thresholds": self.performance_thresholds.copy()
        }
        
    def clear_alert(self, alert_key: str):
        """清除告警"""
        if alert_key in self.active_alerts:
            self.active_alerts[alert_key].is_active = False
            del self.active_alerts[alert_key]
            trading_logger.info(f"已清除告警: {alert_key}")
            
    def clear_all_alerts(self):
        """清除所有告警"""
        for alert in self.active_alerts.values():
            alert.is_active = False
        self.active_alerts.clear()
        trading_logger.info("已清除所有告警")
        
    def update_risk_thresholds(self, thresholds: Dict[str, float]):
        """更新风险阈值"""
        self.risk_thresholds.update(thresholds)
        trading_logger.info(f"更新风险阈值: {thresholds}")
        
    def update_performance_thresholds(self, thresholds: Dict[str, float]):
        """更新性能阈值"""
        self.performance_thresholds.update(thresholds)
        trading_logger.info(f"更新性能阈值: {thresholds}")
        
    def reset_statistics(self):
        """重置统计信息"""
        self.trade_executions.clear()
        self.trade_metrics.clear()
        self.metrics_history.clear()
        self.pnl_history.clear()
        self.drawdown_history.clear()
        self.execution_times.clear()
        self.slippage_data.clear()
        self.order_fill_rates.clear()
        
        self.daily_stats = self._reset_daily_stats()
        self.total_trades = 0
        self.total_volume = 0.0
        self.total_pnl = 0.0
        self.start_time = time.time()
        
        trading_logger.info("交易监控统计信息已重置")


# 创建全局交易监控器
trade_monitor = TradeMonitor()