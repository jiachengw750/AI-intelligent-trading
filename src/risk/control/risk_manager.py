# -*- coding: utf-8 -*-
"""
风险管理器
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
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from src.utils.helpers.logger import risk_logger
from src.utils.helpers.async_utils import async_utils
from src.core.exceptions.trading_exceptions import RiskLimitException, DrawdownException
from src.core.config import trading_config


class RiskLevel(Enum):
    """风险等级"""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"
    CRITICAL = "critical"


class RiskType(Enum):
    """风险类型"""
    MARKET_RISK = "market_risk"
    CREDIT_RISK = "credit_risk"
    LIQUIDITY_RISK = "liquidity_risk"
    OPERATIONAL_RISK = "operational_risk"
    CONCENTRATION_RISK = "concentration_risk"
    VOLATILITY_RISK = "volatility_risk"
    CORRELATION_RISK = "correlation_risk"


@dataclass
class RiskMetrics:
    """风险指标"""
    var_1d: float = 0.0  # 1日风险价值
    var_5d: float = 0.0  # 5日风险价值
    var_10d: float = 0.0  # 10日风险价值
    expected_shortfall: float = 0.0  # 预期损失
    max_drawdown: float = 0.0  # 最大回撤
    current_drawdown: float = 0.0  # 当前回撤
    volatility: float = 0.0  # 波动率
    beta: float = 0.0  # 贝塔系数
    sharpe_ratio: float = 0.0  # 夏普比率
    sortino_ratio: float = 0.0  # 索提诺比率
    calmar_ratio: float = 0.0  # 卡玛比率
    skewness: float = 0.0  # 偏度
    kurtosis: float = 0.0  # 峰度
    
    def to_dict(self) -> Dict[str, float]:
        """转换为字典"""
        return {
            "var_1d": self.var_1d,
            "var_5d": self.var_5d,
            "var_10d": self.var_10d,
            "expected_shortfall": self.expected_shortfall,
            "max_drawdown": self.max_drawdown,
            "current_drawdown": self.current_drawdown,
            "volatility": self.volatility,
            "beta": self.beta,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "calmar_ratio": self.calmar_ratio,
            "skewness": self.skewness,
            "kurtosis": self.kurtosis
        }


@dataclass
class RiskLimit:
    """风险限制"""
    limit_type: str
    limit_value: float
    current_value: float
    utilization_rate: float
    is_breached: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "limit_type": self.limit_type,
            "limit_value": self.limit_value,
            "current_value": self.current_value,
            "utilization_rate": self.utilization_rate,
            "is_breached": self.is_breached
        }


@dataclass
class RiskAlert:
    """风险预警"""
    alert_id: str
    risk_type: RiskType
    risk_level: RiskLevel
    message: str
    current_value: float
    threshold_value: float
    timestamp: float
    is_resolved: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "alert_id": self.alert_id,
            "risk_type": self.risk_type.value,
            "risk_level": self.risk_level.value,
            "message": self.message,
            "current_value": self.current_value,
            "threshold_value": self.threshold_value,
            "timestamp": self.timestamp,
            "is_resolved": self.is_resolved
        }


class RiskManager:
    """风险管理器"""
    
    def __init__(self):
        # 风险限制配置（从配置加载）
        self.risk_limits = trading_config.risk_limits.copy()
        
        # 风险监控
        self.risk_alerts = deque(maxlen=500)  # 使用deque限制大小
        self.risk_metrics_history = deque(maxlen=1000)  # 使用deque限制大小
        self.is_monitoring = False
        
        # 线程池用于CPU密集型计算
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # 统计数据
        self.total_alerts = 0
        self.resolved_alerts = 0
        self.critical_alerts = 0
        
        # 回调函数
        self.alert_callbacks: List[callable] = []
        
    def add_alert_callback(self, callback: callable):
        """添加预警回调"""
        self.alert_callbacks.append(callback)
        risk_logger.info(f"添加风险预警回调: {callback.__name__}")
        
    def remove_alert_callback(self, callback: callable):
        """移除预警回调"""
        if callback in self.alert_callbacks:
            self.alert_callbacks.remove(callback)
            risk_logger.info(f"移除风险预警回调: {callback.__name__}")
            
    async def _emit_alert(self, alert: RiskAlert):
        """发出预警"""
        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                risk_logger.error(f"预警回调执行失败: {e}")
                
    def update_risk_limits(self, new_limits: Dict[str, float]):
        """更新风险限制"""
        self.risk_limits.update(new_limits)
        risk_logger.info(f"更新风险限制: {new_limits}")
        
    async def calculate_portfolio_risk(self, portfolio: Dict[str, Any]) -> RiskMetrics:
        """计算投资组合风险"""
        try:
            risk_logger.debug("开始计算投资组合风险")
            
            # 获取持仓信息
            positions = portfolio.get("positions", {})
            total_value = portfolio.get("total_value", 0)
            
            if not positions or total_value <= 0:
                return RiskMetrics()
                
            # 计算各种风险指标
            metrics = RiskMetrics()
            
            # 获取价格数据
            price_data = await self._get_price_data(list(positions.keys()))
            
            if price_data.empty:
                risk_logger.warning("无法获取价格数据")
                return metrics
                
            # 计算投资组合收益率
            portfolio_returns = self._calculate_portfolio_returns(positions, price_data, total_value)
            
            if len(portfolio_returns) < 10:
                risk_logger.warning("历史数据不足，无法计算风险指标")
                return metrics
                
            # 计算VaR
            metrics.var_1d = self._calculate_var(portfolio_returns, confidence=0.95, horizon=1)
            metrics.var_5d = self._calculate_var(portfolio_returns, confidence=0.95, horizon=5)
            metrics.var_10d = self._calculate_var(portfolio_returns, confidence=0.95, horizon=10)
            
            # 计算预期损失
            metrics.expected_shortfall = self._calculate_expected_shortfall(portfolio_returns, confidence=0.95)
            
            # 计算回撤
            metrics.max_drawdown, metrics.current_drawdown = self._calculate_drawdown(portfolio_returns)
            
            # 计算波动率
            metrics.volatility = np.std(portfolio_returns) * np.sqrt(252)  # 年化波动率
            
            # 计算夏普比率
            metrics.sharpe_ratio = self._calculate_sharpe_ratio(portfolio_returns)
            
            # 计算索提诺比率
            metrics.sortino_ratio = self._calculate_sortino_ratio(portfolio_returns)
            
            # 计算卡玛比率
            metrics.calmar_ratio = self._calculate_calmar_ratio(portfolio_returns, metrics.max_drawdown)
            
            # 计算偏度和峰度（使用线程池避免阻塞）
            loop = asyncio.get_event_loop()
            metrics.skewness = await loop.run_in_executor(
                self.executor, lambda: float(pd.Series(portfolio_returns).skew())
            )
            metrics.kurtosis = await loop.run_in_executor(
                self.executor, lambda: float(pd.Series(portfolio_returns).kurtosis())
            )
            
            # 记录历史
            self.risk_metrics_history.append(metrics)  # deque会自动限制大小
                
            risk_logger.debug(f"投资组合风险计算完成: VaR(1d)={metrics.var_1d:.4f}, 最大回撤={metrics.max_drawdown:.4f}")
            
            return metrics
            
        except Exception as e:
            risk_logger.error(f"计算投资组合风险失败: {e}")
            return RiskMetrics()
            
    async def _get_price_data(self, symbols: List[str], days: int = 252) -> pd.DataFrame:
        """获取价格数据"""
        try:
            # 从存储中获取价格数据
            from src.data import storage_manager
            
            all_data = []
            
            for symbol in symbols:
                query = {
                    "symbol": symbol,
                    "data_type": "kline",
                    "start_time": time.time() - 86400 * days,
                    "end_time": time.time(),
                    "limit": days * 24
                }
                
                data = await storage_manager.retrieve_data(query)
                
                if data:
                    for item in data:
                        if 'data' in item and 'klines' in item['data']:
                            for kline in item['data']['klines']:
                                all_data.append({
                                    'symbol': symbol,
                                    'timestamp': kline['timestamp'],
                                    'close': float(kline['close'])
                                })
                                
            if not all_data:
                return pd.DataFrame()
                
            df = pd.DataFrame(all_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # 透视表，每个交易对一列
            price_df = df.pivot(index='timestamp', columns='symbol', values='close')
            price_df = price_df.fillna(method='ffill').fillna(method='bfill')
            
            return price_df
            
        except Exception as e:
            risk_logger.error(f"获取价格数据失败: {e}")
            return pd.DataFrame()
            
    def _calculate_portfolio_returns(self, positions: Dict[str, Any], 
                                   price_data: pd.DataFrame, 
                                   total_value: float) -> List[float]:
        """计算投资组合收益率"""
        try:
            portfolio_values = []
            
            for timestamp, prices in price_data.iterrows():
                portfolio_value = 0
                
                for symbol, position in positions.items():
                    if symbol in prices:
                        position_value = position.get('amount', 0) * prices[symbol]
                        portfolio_value += position_value
                        
                portfolio_values.append(portfolio_value)
                
            # 计算收益率
            portfolio_returns = []
            for i in range(1, len(portfolio_values)):
                if portfolio_values[i-1] > 0:
                    return_rate = (portfolio_values[i] - portfolio_values[i-1]) / portfolio_values[i-1]
                    portfolio_returns.append(return_rate)
                    
            return portfolio_returns
            
        except Exception as e:
            risk_logger.error(f"计算投资组合收益率失败: {e}")
            return []
            
    def _calculate_var(self, returns: List[float], confidence: float = 0.95, horizon: int = 1) -> float:
        """计算风险价值（VaR） - 优化版"""
        try:
            if len(returns) < 10:
                return 0.0
                
            # 使用numpy向量化操作优化
            returns_array = np.array(returns)
            var_1d = abs(np.percentile(returns_array, (1 - confidence) * 100))
            
            # 时间调整
            var_horizon = var_1d * np.sqrt(horizon)
            return var_horizon
                
        except Exception as e:
            risk_logger.error(f"计算VaR失败: {e}")
            return 0.0
            
    def _calculate_expected_shortfall(self, returns: List[float], confidence: float = 0.95) -> float:
        """计算预期损失（Expected Shortfall）"""
        try:
            if len(returns) < 10:
                return 0.0
                
            # 使用numpy向量化操作优化
            returns_array = np.array(returns)
            var_threshold = np.percentile(returns_array, (1 - confidence) * 100)
            
            # 超过VaR的平均损失
            tail_losses = returns_array[returns_array <= var_threshold]
            expected_shortfall = abs(np.mean(tail_losses)) if len(tail_losses) > 0 else 0.0
            return expected_shortfall
                
        except Exception as e:
            risk_logger.error(f"计算预期损失失败: {e}")
            return 0.0
            
    def _calculate_drawdown(self, returns: List[float]) -> Tuple[float, float]:
        """计算回撤"""
        try:
            if len(returns) < 2:
                return 0.0, 0.0
                
            # 计算累计收益
            cumulative_returns = np.cumprod(1 + np.array(returns))
            
            # 计算运行最大值
            running_max = np.maximum.accumulate(cumulative_returns)
            
            # 计算回撤
            drawdown = (running_max - cumulative_returns) / running_max
            
            max_drawdown = np.max(drawdown)
            current_drawdown = drawdown[-1]
            
            return float(max_drawdown), float(current_drawdown)
            
        except Exception as e:
            risk_logger.error(f"计算回撤失败: {e}")
            return 0.0, 0.0
            
    def _calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.02) -> float:
        """计算夏普比率"""
        try:
            if len(returns) < 10:
                return 0.0
                
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            
            if std_return == 0:
                return 0.0
                
            # 年化处理
            annualized_return = mean_return * 252
            annualized_volatility = std_return * np.sqrt(252)
            
            sharpe_ratio = (annualized_return - risk_free_rate) / annualized_volatility
            
            return float(sharpe_ratio)
            
        except Exception as e:
            risk_logger.error(f"计算夏普比率失败: {e}")
            return 0.0
            
    def _calculate_sortino_ratio(self, returns: List[float], risk_free_rate: float = 0.02) -> float:
        """计算索提诺比率"""
        try:
            if len(returns) < 10:
                return 0.0
                
            mean_return = np.mean(returns)
            
            # 只计算负收益的标准差
            negative_returns = [r for r in returns if r < 0]
            
            if not negative_returns:
                return float('inf')
                
            downside_deviation = np.std(negative_returns)
            
            if downside_deviation == 0:
                return 0.0
                
            # 年化处理
            annualized_return = mean_return * 252
            annualized_downside_deviation = downside_deviation * np.sqrt(252)
            
            sortino_ratio = (annualized_return - risk_free_rate) / annualized_downside_deviation
            
            return float(sortino_ratio)
            
        except Exception as e:
            risk_logger.error(f"计算索提诺比率失败: {e}")
            return 0.0
            
    def _calculate_calmar_ratio(self, returns: List[float], max_drawdown: float) -> float:
        """计算卡玛比率"""
        try:
            if len(returns) < 10 or max_drawdown == 0:
                return 0.0
                
            annualized_return = np.mean(returns) * 252
            
            calmar_ratio = annualized_return / max_drawdown
            
            return float(calmar_ratio)
            
        except Exception as e:
            risk_logger.error(f"计算卡玛比率失败: {e}")
            return 0.0
            
    async def check_risk_limits(self, portfolio: Dict[str, Any], 
                              new_trade: Dict[str, Any] = None) -> List[RiskLimit]:
        """检查风险限制"""
        try:
            risk_limits = []
            
            # 计算当前风险指标
            metrics = await self.calculate_portfolio_risk(portfolio)
            
            # 检查投资组合风险限制
            portfolio_risk_limit = RiskLimit(
                limit_type="portfolio_risk",
                limit_value=self.risk_limits["max_portfolio_risk"],
                current_value=metrics.var_1d,
                utilization_rate=metrics.var_1d / self.risk_limits["max_portfolio_risk"]
            )
            
            if metrics.var_1d > self.risk_limits["max_portfolio_risk"]:
                portfolio_risk_limit.is_breached = True
                await self._create_alert(
                    RiskType.MARKET_RISK,
                    RiskLevel.HIGH,
                    f"投资组合风险超限: {metrics.var_1d:.4f} > {self.risk_limits['max_portfolio_risk']:.4f}",
                    metrics.var_1d,
                    self.risk_limits["max_portfolio_risk"]
                )
                
            risk_limits.append(portfolio_risk_limit)
            
            # 检查最大回撤限制
            drawdown_limit = RiskLimit(
                limit_type="max_drawdown",
                limit_value=self.risk_limits["max_drawdown"],
                current_value=metrics.max_drawdown,
                utilization_rate=metrics.max_drawdown / self.risk_limits["max_drawdown"]
            )
            
            if metrics.max_drawdown > self.risk_limits["max_drawdown"]:
                drawdown_limit.is_breached = True
                await self._create_alert(
                    RiskType.MARKET_RISK,
                    RiskLevel.CRITICAL,
                    f"最大回撤超限: {metrics.max_drawdown:.4f} > {self.risk_limits['max_drawdown']:.4f}",
                    metrics.max_drawdown,
                    self.risk_limits["max_drawdown"]
                )
                
            risk_limits.append(drawdown_limit)
            
            # 检查单笔交易限制
            if new_trade:
                single_position_limit = await self._check_single_position_limit(portfolio, new_trade)
                risk_limits.append(single_position_limit)
                
            # 检查集中度风险
            concentration_limit = await self._check_concentration_risk(portfolio)
            risk_limits.append(concentration_limit)
            
            return risk_limits
            
        except Exception as e:
            risk_logger.error(f"检查风险限制失败: {e}")
            return []
            
    async def _check_single_position_limit(self, portfolio: Dict[str, Any], 
                                         new_trade: Dict[str, Any]) -> RiskLimit:
        """检查单笔仓位限制"""
        try:
            total_value = portfolio.get("total_value", 0)
            trade_value = new_trade.get("amount", 0) * new_trade.get("price", 0)
            
            current_ratio = trade_value / total_value if total_value > 0 else 0
            
            limit = RiskLimit(
                limit_type="single_position",
                limit_value=self.risk_limits["max_single_position"],
                current_value=current_ratio,
                utilization_rate=current_ratio / self.risk_limits["max_single_position"]
            )
            
            if current_ratio > self.risk_limits["max_single_position"]:
                limit.is_breached = True
                await self._create_alert(
                    RiskType.CONCENTRATION_RISK,
                    RiskLevel.HIGH,
                    f"单笔仓位超限: {current_ratio:.4f} > {self.risk_limits['max_single_position']:.4f}",
                    current_ratio,
                    self.risk_limits["max_single_position"]
                )
                
            return limit
            
        except Exception as e:
            risk_logger.error(f"检查单笔仓位限制失败: {e}")
            return RiskLimit("single_position", 0, 0, 0)
            
    async def _check_concentration_risk(self, portfolio: Dict[str, Any]) -> RiskLimit:
        """检查集中度风险"""
        try:
            positions = portfolio.get("positions", {})
            total_value = portfolio.get("total_value", 0)
            
            if not positions or total_value <= 0:
                return RiskLimit("concentration", 0, 0, 0)
                
            # 计算最大单一持仓比例
            max_position_ratio = 0
            
            for symbol, position in positions.items():
                position_value = position.get("value", 0)
                position_ratio = position_value / total_value
                max_position_ratio = max(max_position_ratio, position_ratio)
                
            limit = RiskLimit(
                limit_type="concentration",
                limit_value=self.risk_limits["max_concentration"],
                current_value=max_position_ratio,
                utilization_rate=max_position_ratio / self.risk_limits["max_concentration"]
            )
            
            if max_position_ratio > self.risk_limits["max_concentration"]:
                limit.is_breached = True
                await self._create_alert(
                    RiskType.CONCENTRATION_RISK,
                    RiskLevel.HIGH,
                    f"集中度风险超限: {max_position_ratio:.4f} > {self.risk_limits['max_concentration']:.4f}",
                    max_position_ratio,
                    self.risk_limits["max_concentration"]
                )
                
            return limit
            
        except Exception as e:
            risk_logger.error(f"检查集中度风险失败: {e}")
            return RiskLimit("concentration", 0, 0, 0)
            
    async def _create_alert(self, risk_type: RiskType, risk_level: RiskLevel,
                          message: str, current_value: float, threshold_value: float):
        """创建风险预警"""
        try:
            alert_id = f"alert_{int(time.time())}_{len(self.risk_alerts)}"
            
            alert = RiskAlert(
                alert_id=alert_id,
                risk_type=risk_type,
                risk_level=risk_level,
                message=message,
                current_value=current_value,
                threshold_value=threshold_value,
                timestamp=time.time()
            )
            
            self.risk_alerts.append(alert)
            self.total_alerts += 1
            
            if risk_level == RiskLevel.CRITICAL:
                self.critical_alerts += 1
                
            # 发出预警
            await self._emit_alert(alert)
            
            risk_logger.warning(f"风险预警: {message}")
            
        except Exception as e:
            risk_logger.error(f"创建风险预警失败: {e}")
            
    async def validate_trade(self, trade: Dict[str, Any], 
                           portfolio: Dict[str, Any]) -> Tuple[bool, str]:
        """验证交易"""
        try:
            # 检查风险限制
            risk_limits = await self.check_risk_limits(portfolio, trade)
            
            # 检查是否有超限
            breached_limits = [limit for limit in risk_limits if limit.is_breached]
            
            if breached_limits:
                messages = []
                for limit in breached_limits:
                    messages.append(f"{limit.limit_type}: {limit.current_value:.4f} > {limit.limit_value:.4f}")
                    
                return False, f"风险超限: {', '.join(messages)}"
                
            # 检查流动性
            liquidity_check = await self._check_liquidity(trade)
            if not liquidity_check[0]:
                return False, f"流动性不足: {liquidity_check[1]}"
                
            # 检查市场风险
            market_risk_check = await self._check_market_risk(trade)
            if not market_risk_check[0]:
                return False, f"市场风险过高: {market_risk_check[1]}"
                
            return True, "交易验证通过"
            
        except Exception as e:
            risk_logger.error(f"验证交易失败: {e}")
            return False, f"验证失败: {str(e)}"
            
    async def _check_liquidity(self, trade: Dict[str, Any]) -> Tuple[bool, str]:
        """检查流动性"""
        try:
            # 简化的流动性检查
            symbol = trade.get("symbol", "")
            amount = trade.get("amount", 0)
            
            # 这里可以检查订单簿深度、成交量等
            # 暂时返回通过
            return True, "流动性充足"
            
        except Exception as e:
            risk_logger.error(f"检查流动性失败: {e}")
            return False, f"流动性检查失败: {str(e)}"
            
    async def _check_market_risk(self, trade: Dict[str, Any]) -> Tuple[bool, str]:
        """检查市场风险"""
        try:
            # 简化的市场风险检查
            symbol = trade.get("symbol", "")
            
            # 这里可以检查波动率、技术指标等
            # 暂时返回通过
            return True, "市场风险可控"
            
        except Exception as e:
            risk_logger.error(f"检查市场风险失败: {e}")
            return False, f"市场风险检查失败: {str(e)}"
            
    def get_risk_summary(self) -> Dict[str, Any]:
        """获取风险摘要"""
        try:
            latest_metrics = self.risk_metrics_history[-1] if self.risk_metrics_history else RiskMetrics()
            
            active_alerts = [alert for alert in self.risk_alerts if not alert.is_resolved]
            
            return {
                "risk_metrics": latest_metrics.to_dict(),
                "risk_limits": self.risk_limits,
                "active_alerts": len(active_alerts),
                "total_alerts": self.total_alerts,
                "critical_alerts": self.critical_alerts,
                "alert_summary": {
                    "high_risk": len([a for a in active_alerts if a.risk_level == RiskLevel.HIGH]),
                    "medium_risk": len([a for a in active_alerts if a.risk_level == RiskLevel.MEDIUM]),
                    "low_risk": len([a for a in active_alerts if a.risk_level == RiskLevel.LOW])
                }
            }
            
        except Exception as e:
            risk_logger.error(f"获取风险摘要失败: {e}")
            return {}
            
    def get_active_alerts(self) -> List[RiskAlert]:
        """获取活跃预警"""
        return [alert for alert in self.risk_alerts if not alert.is_resolved]
        
    def resolve_alert(self, alert_id: str) -> bool:
        """解决预警"""
        try:
            for alert in self.risk_alerts:
                if alert.alert_id == alert_id:
                    alert.is_resolved = True
                    self.resolved_alerts += 1
                    risk_logger.info(f"预警已解决: {alert_id}")
                    return True
                    
            return False
            
        except Exception as e:
            risk_logger.error(f"解决预警失败: {e}")
            return False
            
    def get_risk_metrics_history(self, limit: int = 100) -> List[RiskMetrics]:
        """获取风险指标历史"""
        return self.risk_metrics_history[-limit:]
        
    def clear_resolved_alerts(self):
        """清除已解决的预警"""
        self.risk_alerts = [alert for alert in self.risk_alerts if not alert.is_resolved]
        risk_logger.info("已清除已解决的预警")


# 全局风险管理器实例
risk_manager = RiskManager()