# -*- coding: utf-8 -*-
"""
策略优化器
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
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from src.ai.reasoning.decision_maker import DecisionMaker, TradingDecision
from src.ai.reasoning.market_analyzer import MarketAnalyzer
from src.utils.helpers.logger import ai_logger
from src.utils.helpers.async_utils import async_utils
from config import ai_config, system_config


class OptimizationObjective(Enum):
    """优化目标"""
    MAXIMIZE_PROFIT = "maximize_profit"
    MINIMIZE_RISK = "minimize_risk"
    MAXIMIZE_SHARPE = "maximize_sharpe"
    MINIMIZE_DRAWDOWN = "minimize_drawdown"
    MAXIMIZE_WIN_RATE = "maximize_win_rate"


class StrategyType(Enum):
    """策略类型"""
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM = "momentum"
    ARBITRAGE = "arbitrage"
    SCALPING = "scalping"
    SWING = "swing"
    POSITION = "position"


@dataclass
class StrategyParameter:
    """策略参数"""
    name: str
    value: Any
    min_value: Any
    max_value: Any
    step: Any
    description: str
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "value": self.value,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "step": self.step,
            "description": self.description
        }


@dataclass
class StrategyPerformance:
    """策略性能"""
    total_return: float = 0.0
    annualized_return: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    average_win: float = 0.0
    average_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_return": self.total_return,
            "annualized_return": self.annualized_return,
            "volatility": self.volatility,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "average_win": self.average_win,
            "average_loss": self.average_loss,
            "largest_win": self.largest_win,
            "largest_loss": self.largest_loss
        }


@dataclass
class TradingStrategy:
    """交易策略"""
    strategy_id: str
    name: str
    strategy_type: StrategyType
    parameters: Dict[str, StrategyParameter]
    performance: StrategyPerformance
    is_active: bool = True
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "strategy_type": self.strategy_type.value,
            "parameters": {k: v.to_dict() for k, v in self.parameters.items()},
            "performance": self.performance.to_dict(),
            "is_active": self.is_active,
            "created_at": self.created_at,
            "last_updated": self.last_updated
        }


class StrategyOptimizer:
    """策略优化器"""
    
    def __init__(self):
        self.decision_maker = DecisionMaker()
        self.market_analyzer = MarketAnalyzer()
        self.strategies: Dict[str, TradingStrategy] = {}
        self.optimization_history: List[Dict[str, Any]] = []
        
        # 优化参数
        self.optimization_iterations = 100
        self.cross_validation_folds = 5
        self.min_trade_count = 30
        self.optimization_period_days = 90
        
        # 机器学习模型
        self.performance_predictor = RandomForestRegressor(n_estimators=100, random_state=42)
        self.feature_scaler = StandardScaler()
        self.is_model_trained = False
        
        # 默认策略参数
        self._initialize_default_strategies()
        
    def _initialize_default_strategies(self):
        """初始化默认策略"""
        # 趋势跟踪策略
        trend_strategy = TradingStrategy(
            strategy_id="trend_following_001",
            name="趋势跟踪策略",
            strategy_type=StrategyType.TREND_FOLLOWING,
            parameters={
                "ma_short_period": StrategyParameter(
                    name="ma_short_period",
                    value=10,
                    min_value=5,
                    max_value=20,
                    step=1,
                    description="短期移动平均周期"
                ),
                "ma_long_period": StrategyParameter(
                    name="ma_long_period",
                    value=30,
                    min_value=20,
                    max_value=50,
                    step=1,
                    description="长期移动平均周期"
                ),
                "rsi_overbought": StrategyParameter(
                    name="rsi_overbought",
                    value=70,
                    min_value=60,
                    max_value=80,
                    step=1,
                    description="RSI超买阈值"
                ),
                "rsi_oversold": StrategyParameter(
                    name="rsi_oversold",
                    value=30,
                    min_value=20,
                    max_value=40,
                    step=1,
                    description="RSI超卖阈值"
                ),
                "stop_loss_pct": StrategyParameter(
                    name="stop_loss_pct",
                    value=0.02,
                    min_value=0.01,
                    max_value=0.05,
                    step=0.001,
                    description="止损百分比"
                ),
                "take_profit_pct": StrategyParameter(
                    name="take_profit_pct",
                    value=0.04,
                    min_value=0.02,
                    max_value=0.08,
                    step=0.001,
                    description="止盈百分比"
                )
            },
            performance=StrategyPerformance()
        )
        
        self.strategies[trend_strategy.strategy_id] = trend_strategy
        
        # 均值回归策略
        reversion_strategy = TradingStrategy(
            strategy_id="mean_reversion_001",
            name="均值回归策略",
            strategy_type=StrategyType.MEAN_REVERSION,
            parameters={
                "bollinger_period": StrategyParameter(
                    name="bollinger_period",
                    value=20,
                    min_value=10,
                    max_value=30,
                    step=1,
                    description="布林带周期"
                ),
                "bollinger_std": StrategyParameter(
                    name="bollinger_std",
                    value=2.0,
                    min_value=1.5,
                    max_value=2.5,
                    step=0.1,
                    description="布林带标准差倍数"
                ),
                "rsi_period": StrategyParameter(
                    name="rsi_period",
                    value=14,
                    min_value=10,
                    max_value=20,
                    step=1,
                    description="RSI周期"
                ),
                "oversold_threshold": StrategyParameter(
                    name="oversold_threshold",
                    value=25,
                    min_value=20,
                    max_value=35,
                    step=1,
                    description="超卖阈值"
                ),
                "overbought_threshold": StrategyParameter(
                    name="overbought_threshold",
                    value=75,
                    min_value=65,
                    max_value=80,
                    step=1,
                    description="超买阈值"
                )
            },
            performance=StrategyPerformance()
        )
        
        self.strategies[reversion_strategy.strategy_id] = reversion_strategy
        
        ai_logger.info(f"初始化了 {len(self.strategies)} 个默认策略")
        
    async def optimize_strategy(self, strategy_id: str, symbol: str, 
                              objective: OptimizationObjective = OptimizationObjective.MAXIMIZE_SHARPE) -> Optional[TradingStrategy]:
        """优化策略"""
        try:
            if strategy_id not in self.strategies:
                ai_logger.error(f"策略 {strategy_id} 不存在")
                return None
                
            strategy = self.strategies[strategy_id]
            ai_logger.info(f"开始优化策略: {strategy.name} ({symbol})")
            
            # 获取历史数据
            historical_data = await self._get_historical_data(symbol)
            if not historical_data:
                ai_logger.error(f"无法获取 {symbol} 的历史数据")
                return None
                
            # 生成参数组合
            parameter_combinations = self._generate_parameter_combinations(strategy)
            
            # 并行测试参数组合
            best_parameters = await self._parallel_optimization(
                strategy, historical_data, parameter_combinations, objective
            )
            
            if not best_parameters:
                ai_logger.error("优化失败，无法找到最优参数")
                return None
                
            # 更新策略参数
            optimized_strategy = self._update_strategy_parameters(strategy, best_parameters)
            
            # 验证优化结果
            validation_performance = await self._validate_strategy(optimized_strategy, historical_data)
            optimized_strategy.performance = validation_performance
            
            # 记录优化历史
            self._record_optimization_history(strategy_id, symbol, objective, optimized_strategy)
            
            ai_logger.info(f"策略优化完成: {strategy.name}, 夏普比率: {optimized_strategy.performance.sharpe_ratio:.4f}")
            
            return optimized_strategy
            
        except Exception as e:
            ai_logger.error(f"策略优化失败: {e}")
            return None
            
    async def _get_historical_data(self, symbol: str, days: int = None) -> Optional[pd.DataFrame]:
        """获取历史数据"""
        try:
            if days is None:
                days = self.optimization_period_days
                
            # 从存储中获取历史数据
            from src.data import storage_manager
            
            query = {
                "symbol": symbol,
                "data_type": "kline",
                "start_time": time.time() - 86400 * days,
                "end_time": time.time(),
                "limit": days * 24  # 假设1小时K线
            }
            
            data = await storage_manager.retrieve_data(query)
            
            if not data:
                return None
                
            # 转换为DataFrame
            records = []
            for item in data:
                if 'data' in item and 'klines' in item['data']:
                    records.extend(item['data']['klines'])
                    
            if not records:
                return None
                
            df = pd.DataFrame(records)
            df = df.sort_values('timestamp').drop_duplicates(subset=['timestamp'])
            
            return df
            
        except Exception as e:
            ai_logger.error(f"获取历史数据失败: {e}")
            return None
            
    def _generate_parameter_combinations(self, strategy: TradingStrategy) -> List[Dict[str, Any]]:
        """生成参数组合"""
        try:
            # 网格搜索生成参数组合
            parameter_grids = {}
            
            for param_name, param in strategy.parameters.items():
                if isinstance(param.value, (int, float)):
                    if isinstance(param.step, (int, float)):
                        # 数值参数
                        values = np.arange(param.min_value, param.max_value + param.step, param.step)
                        parameter_grids[param_name] = values.tolist()
                    else:
                        # 离散值
                        parameter_grids[param_name] = [param.min_value, param.value, param.max_value]
                else:
                    # 分类参数
                    parameter_grids[param_name] = [param.value]
                    
            # 生成组合
            combinations = []
            
            # 简化版本：随机采样而非完整网格搜索
            for _ in range(min(self.optimization_iterations, 1000)):
                combination = {}
                for param_name, values in parameter_grids.items():
                    combination[param_name] = np.random.choice(values)
                combinations.append(combination)
                
            # 确保包含原始参数
            original_params = {name: param.value for name, param in strategy.parameters.items()}
            combinations.append(original_params)
            
            return combinations
            
        except Exception as e:
            ai_logger.error(f"生成参数组合失败: {e}")
            return []
            
    async def _parallel_optimization(self, strategy: TradingStrategy, 
                                   historical_data: pd.DataFrame,
                                   parameter_combinations: List[Dict[str, Any]],
                                   objective: OptimizationObjective) -> Optional[Dict[str, Any]]:
        """并行优化"""
        try:
            # 创建并行任务
            tasks = []
            
            for params in parameter_combinations:
                task = asyncio.create_task(
                    self._evaluate_parameter_combination(strategy, historical_data, params, objective)
                )
                tasks.append(task)
                
            # 等待所有任务完成
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            valid_results = []
            for i, result in enumerate(results):
                if isinstance(result, tuple) and len(result) == 2:
                    params, performance = result
                    valid_results.append((params, performance))
                elif isinstance(result, Exception):
                    ai_logger.error(f"参数组合 {i} 评估失败: {result}")
                    
            if not valid_results:
                return None
                
            # 选择最佳参数
            best_params, best_performance = self._select_best_parameters(valid_results, objective)
            
            return best_params
            
        except Exception as e:
            ai_logger.error(f"并行优化失败: {e}")
            return None
            
    async def _evaluate_parameter_combination(self, strategy: TradingStrategy,
                                           historical_data: pd.DataFrame,
                                           params: Dict[str, Any],
                                           objective: OptimizationObjective) -> Optional[Tuple[Dict[str, Any], StrategyPerformance]]:
        """评估参数组合"""
        try:
            # 应用参数创建临时策略
            temp_strategy = self._create_temp_strategy(strategy, params)
            
            # 回测策略
            performance = await self._backtest_strategy(temp_strategy, historical_data)
            
            if not performance:
                return None
                
            return params, performance
            
        except Exception as e:
            ai_logger.error(f"评估参数组合失败: {e}")
            return None
            
    def _create_temp_strategy(self, original_strategy: TradingStrategy, 
                            params: Dict[str, Any]) -> TradingStrategy:
        """创建临时策略"""
        temp_strategy = TradingStrategy(
            strategy_id=f"{original_strategy.strategy_id}_temp",
            name=f"{original_strategy.name}_temp",
            strategy_type=original_strategy.strategy_type,
            parameters=original_strategy.parameters.copy(),
            performance=StrategyPerformance()
        )
        
        # 更新参数值
        for param_name, value in params.items():
            if param_name in temp_strategy.parameters:
                temp_strategy.parameters[param_name].value = value
                
        return temp_strategy
        
    async def _backtest_strategy(self, strategy: TradingStrategy, 
                               historical_data: pd.DataFrame) -> Optional[StrategyPerformance]:
        """回测策略"""
        try:
            # 简化的回测逻辑
            trades = []
            balance = 10000  # 初始资金
            position = 0
            
            # 计算技术指标
            data_with_indicators = self._calculate_strategy_indicators(historical_data, strategy)
            
            for i in range(len(data_with_indicators)):
                current_data = data_with_indicators.iloc[i]
                
                # 生成交易信号
                signal = self._generate_trading_signal(current_data, strategy)
                
                # 执行交易
                if signal == "buy" and position <= 0:
                    position = balance / current_data['close']
                    trades.append({
                        'type': 'buy',
                        'price': current_data['close'],
                        'timestamp': current_data['timestamp'],
                        'position': position
                    })
                elif signal == "sell" and position > 0:
                    balance = position * current_data['close']
                    trades.append({
                        'type': 'sell',
                        'price': current_data['close'],
                        'timestamp': current_data['timestamp'],
                        'position': position,
                        'pnl': balance - 10000
                    })
                    position = 0
                    
            # 计算性能指标
            performance = self._calculate_performance_metrics(trades, historical_data)
            
            return performance
            
        except Exception as e:
            ai_logger.error(f"回测策略失败: {e}")
            return None
            
    def _calculate_strategy_indicators(self, data: pd.DataFrame, 
                                     strategy: TradingStrategy) -> pd.DataFrame:
        """计算策略指标"""
        try:
            df = data.copy()
            
            # 确保数据类型正确
            df['close'] = pd.to_numeric(df['close'], errors='coerce')
            df['high'] = pd.to_numeric(df['high'], errors='coerce')
            df['low'] = pd.to_numeric(df['low'], errors='coerce')
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
            
            # 根据策略类型计算不同指标
            if strategy.strategy_type == StrategyType.TREND_FOLLOWING:
                # 移动平均线
                ma_short = strategy.parameters['ma_short_period'].value
                ma_long = strategy.parameters['ma_long_period'].value
                
                df['ma_short'] = df['close'].rolling(window=ma_short).mean()
                df['ma_long'] = df['close'].rolling(window=ma_long).mean()
                
                # RSI
                df['rsi'] = self._calculate_rsi(df['close'])
                
            elif strategy.strategy_type == StrategyType.MEAN_REVERSION:
                # 布林带
                bb_period = strategy.parameters['bollinger_period'].value
                bb_std = strategy.parameters['bollinger_std'].value
                
                df['bb_middle'] = df['close'].rolling(window=bb_period).mean()
                bb_std_dev = df['close'].rolling(window=bb_period).std()
                df['bb_upper'] = df['bb_middle'] + (bb_std_dev * bb_std)
                df['bb_lower'] = df['bb_middle'] - (bb_std_dev * bb_std)
                
                # RSI
                rsi_period = strategy.parameters['rsi_period'].value
                df['rsi'] = self._calculate_rsi(df['close'], rsi_period)
                
            return df
            
        except Exception as e:
            ai_logger.error(f"计算策略指标失败: {e}")
            return data
            
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """计算RSI"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        except:
            return pd.Series([50] * len(prices))
            
    def _generate_trading_signal(self, data: pd.Series, strategy: TradingStrategy) -> str:
        """生成交易信号"""
        try:
            if strategy.strategy_type == StrategyType.TREND_FOLLOWING:
                # 趋势跟踪信号
                if (data['ma_short'] > data['ma_long'] and 
                    data['rsi'] < strategy.parameters['rsi_overbought'].value):
                    return "buy"
                elif (data['ma_short'] < data['ma_long'] and 
                      data['rsi'] > strategy.parameters['rsi_oversold'].value):
                    return "sell"
                    
            elif strategy.strategy_type == StrategyType.MEAN_REVERSION:
                # 均值回归信号
                if (data['close'] < data['bb_lower'] and 
                    data['rsi'] < strategy.parameters['oversold_threshold'].value):
                    return "buy"
                elif (data['close'] > data['bb_upper'] and 
                      data['rsi'] > strategy.parameters['overbought_threshold'].value):
                    return "sell"
                    
            return "hold"
            
        except Exception as e:
            ai_logger.error(f"生成交易信号失败: {e}")
            return "hold"
            
    def _calculate_performance_metrics(self, trades: List[Dict[str, Any]], 
                                     historical_data: pd.DataFrame) -> StrategyPerformance:
        """计算性能指标"""
        try:
            if not trades:
                return StrategyPerformance()
                
            # 计算收益
            pnl_trades = [trade for trade in trades if 'pnl' in trade]
            
            if not pnl_trades:
                return StrategyPerformance()
                
            # 基本统计
            total_trades = len(pnl_trades)
            winning_trades = len([t for t in pnl_trades if t['pnl'] > 0])
            losing_trades = len([t for t in pnl_trades if t['pnl'] < 0])
            
            # 收益统计
            all_pnl = [t['pnl'] for t in pnl_trades]
            winning_pnl = [t['pnl'] for t in pnl_trades if t['pnl'] > 0]
            losing_pnl = [t['pnl'] for t in pnl_trades if t['pnl'] < 0]
            
            total_return = sum(all_pnl)
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            
            average_win = sum(winning_pnl) / len(winning_pnl) if winning_pnl else 0
            average_loss = sum(losing_pnl) / len(losing_pnl) if losing_pnl else 0
            
            largest_win = max(winning_pnl) if winning_pnl else 0
            largest_loss = min(losing_pnl) if losing_pnl else 0
            
            # 计算夏普比率
            if len(all_pnl) > 1:
                returns_std = np.std(all_pnl)
                sharpe_ratio = (np.mean(all_pnl) / returns_std) if returns_std > 0 else 0
            else:
                sharpe_ratio = 0
                
            # 计算最大回撤
            max_drawdown = self._calculate_max_drawdown(all_pnl)
            
            # 计算利润因子
            total_wins = sum(winning_pnl) if winning_pnl else 0
            total_losses = abs(sum(losing_pnl)) if losing_pnl else 0
            profit_factor = total_wins / total_losses if total_losses > 0 else 0
            
            return StrategyPerformance(
                total_return=total_return,
                win_rate=win_rate,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                profit_factor=profit_factor,
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                average_win=average_win,
                average_loss=average_loss,
                largest_win=largest_win,
                largest_loss=largest_loss
            )
            
        except Exception as e:
            ai_logger.error(f"计算性能指标失败: {e}")
            return StrategyPerformance()
            
    def _calculate_max_drawdown(self, pnl_series: List[float]) -> float:
        """计算最大回撤"""
        try:
            if not pnl_series:
                return 0.0
                
            cumulative = np.cumsum(pnl_series)
            running_max = np.maximum.accumulate(cumulative)
            drawdown = running_max - cumulative
            
            return float(np.max(drawdown))
            
        except Exception as e:
            ai_logger.error(f"计算最大回撤失败: {e}")
            return 0.0
            
    def _select_best_parameters(self, results: List[Tuple[Dict[str, Any], StrategyPerformance]], 
                              objective: OptimizationObjective) -> Tuple[Dict[str, Any], StrategyPerformance]:
        """选择最佳参数"""
        try:
            if not results:
                return {}, StrategyPerformance()
                
            # 根据优化目标选择最佳参数
            if objective == OptimizationObjective.MAXIMIZE_PROFIT:
                best_params, best_performance = max(results, key=lambda x: x[1].total_return)
            elif objective == OptimizationObjective.MAXIMIZE_SHARPE:
                best_params, best_performance = max(results, key=lambda x: x[1].sharpe_ratio)
            elif objective == OptimizationObjective.MINIMIZE_DRAWDOWN:
                best_params, best_performance = min(results, key=lambda x: x[1].max_drawdown)
            elif objective == OptimizationObjective.MAXIMIZE_WIN_RATE:
                best_params, best_performance = max(results, key=lambda x: x[1].win_rate)
            else:
                best_params, best_performance = max(results, key=lambda x: x[1].sharpe_ratio)
                
            return best_params, best_performance
            
        except Exception as e:
            ai_logger.error(f"选择最佳参数失败: {e}")
            return {}, StrategyPerformance()
            
    def _update_strategy_parameters(self, strategy: TradingStrategy, 
                                  best_params: Dict[str, Any]) -> TradingStrategy:
        """更新策略参数"""
        try:
            updated_strategy = TradingStrategy(
                strategy_id=strategy.strategy_id,
                name=strategy.name,
                strategy_type=strategy.strategy_type,
                parameters=strategy.parameters.copy(),
                performance=StrategyPerformance(),
                is_active=strategy.is_active
            )
            
            # 更新参数值
            for param_name, value in best_params.items():
                if param_name in updated_strategy.parameters:
                    updated_strategy.parameters[param_name].value = value
                    
            updated_strategy.last_updated = time.time()
            
            return updated_strategy
            
        except Exception as e:
            ai_logger.error(f"更新策略参数失败: {e}")
            return strategy
            
    async def _validate_strategy(self, strategy: TradingStrategy, 
                               historical_data: pd.DataFrame) -> StrategyPerformance:
        """验证策略"""
        try:
            # 使用交叉验证
            total_data_points = len(historical_data)
            fold_size = total_data_points // self.cross_validation_folds
            
            performances = []
            
            for fold in range(self.cross_validation_folds):
                start_idx = fold * fold_size
                end_idx = (fold + 1) * fold_size if fold < self.cross_validation_folds - 1 else total_data_points
                
                fold_data = historical_data.iloc[start_idx:end_idx]
                
                if len(fold_data) < self.min_trade_count:
                    continue
                    
                fold_performance = await self._backtest_strategy(strategy, fold_data)
                
                if fold_performance:
                    performances.append(fold_performance)
                    
            # 平均性能
            if performances:
                avg_performance = self._average_performances(performances)
                return avg_performance
            else:
                return StrategyPerformance()
                
        except Exception as e:
            ai_logger.error(f"验证策略失败: {e}")
            return StrategyPerformance()
            
    def _average_performances(self, performances: List[StrategyPerformance]) -> StrategyPerformance:
        """平均性能"""
        try:
            if not performances:
                return StrategyPerformance()
                
            n = len(performances)
            
            return StrategyPerformance(
                total_return=sum(p.total_return for p in performances) / n,
                win_rate=sum(p.win_rate for p in performances) / n,
                sharpe_ratio=sum(p.sharpe_ratio for p in performances) / n,
                max_drawdown=sum(p.max_drawdown for p in performances) / n,
                profit_factor=sum(p.profit_factor for p in performances) / n,
                total_trades=int(sum(p.total_trades for p in performances) / n),
                winning_trades=int(sum(p.winning_trades for p in performances) / n),
                losing_trades=int(sum(p.losing_trades for p in performances) / n),
                average_win=sum(p.average_win for p in performances) / n,
                average_loss=sum(p.average_loss for p in performances) / n,
                largest_win=max(p.largest_win for p in performances),
                largest_loss=min(p.largest_loss for p in performances)
            )
            
        except Exception as e:
            ai_logger.error(f"平均性能计算失败: {e}")
            return StrategyPerformance()
            
    def _record_optimization_history(self, strategy_id: str, symbol: str, 
                                   objective: OptimizationObjective, 
                                   optimized_strategy: TradingStrategy):
        """记录优化历史"""
        try:
            history_record = {
                "timestamp": time.time(),
                "strategy_id": strategy_id,
                "symbol": symbol,
                "objective": objective.value,
                "optimized_parameters": {k: v.value for k, v in optimized_strategy.parameters.items()},
                "performance": optimized_strategy.performance.to_dict()
            }
            
            self.optimization_history.append(history_record)
            
            # 限制历史记录大小
            if len(self.optimization_history) > 1000:
                self.optimization_history = self.optimization_history[-1000:]
                
        except Exception as e:
            ai_logger.error(f"记录优化历史失败: {e}")
            
    def get_strategy(self, strategy_id: str) -> Optional[TradingStrategy]:
        """获取策略"""
        return self.strategies.get(strategy_id)
        
    def list_strategies(self) -> List[TradingStrategy]:
        """列出所有策略"""
        return list(self.strategies.values())
        
    def get_optimization_history(self, strategy_id: str = None) -> List[Dict[str, Any]]:
        """获取优化历史"""
        if strategy_id:
            return [h for h in self.optimization_history if h["strategy_id"] == strategy_id]
        return self.optimization_history
        
    def get_strategy_ranking(self, objective: OptimizationObjective = OptimizationObjective.MAXIMIZE_SHARPE) -> List[TradingStrategy]:
        """获取策略排名"""
        try:
            strategies = [s for s in self.strategies.values() if s.is_active]
            
            if objective == OptimizationObjective.MAXIMIZE_PROFIT:
                return sorted(strategies, key=lambda s: s.performance.total_return, reverse=True)
            elif objective == OptimizationObjective.MAXIMIZE_SHARPE:
                return sorted(strategies, key=lambda s: s.performance.sharpe_ratio, reverse=True)
            elif objective == OptimizationObjective.MINIMIZE_DRAWDOWN:
                return sorted(strategies, key=lambda s: s.performance.max_drawdown)
            elif objective == OptimizationObjective.MAXIMIZE_WIN_RATE:
                return sorted(strategies, key=lambda s: s.performance.win_rate, reverse=True)
            else:
                return sorted(strategies, key=lambda s: s.performance.sharpe_ratio, reverse=True)
                
        except Exception as e:
            ai_logger.error(f"获取策略排名失败: {e}")
            return []


# 全局策略优化器实例
strategy_optimizer = StrategyOptimizer()