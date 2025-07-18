# -*- coding: utf-8 -*-
"""
AI决策制定器
"""

import asyncio
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import time
import json
from collections import deque
from src.ai.models import model_manager, prompt_manager, response_parser, ModelRequest, ModelType, ResponseType
from src.ai.reasoning.market_analyzer import MarketAnalyzer, MarketAnalysis
from src.utils.helpers.logger import ai_logger
from src.utils.helpers.async_utils import async_utils
from src.core.config import trading_config
from config import ai_config


class DecisionType(Enum):
    """决策类型"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"
    WAIT = "wait"


class DecisionConfidence(Enum):
    """决策置信度"""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class RiskLevel(Enum):
    """风险等级"""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class TradingDecision:
    """交易决策"""
    symbol: str
    decision_type: DecisionType
    confidence: DecisionConfidence
    confidence_score: float
    risk_level: RiskLevel
    reasoning: str
    timestamp: float
    
    # 交易参数
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size: Optional[float] = None
    
    # 时间参数
    holding_period: Optional[int] = None  # 预期持有时间（秒）
    max_holding_period: Optional[int] = None  # 最大持有时间
    
    # 条件参数
    entry_conditions: List[str] = field(default_factory=list)
    exit_conditions: List[str] = field(default_factory=list)
    
    # 风险参数
    max_loss: Optional[float] = None
    risk_reward_ratio: Optional[float] = None
    
    # AI洞察
    ai_insights: str = ""
    market_context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "decision_type": self.decision_type.value,
            "confidence": self.confidence.value,
            "confidence_score": self.confidence_score,
            "risk_level": self.risk_level.value,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "position_size": self.position_size,
            "holding_period": self.holding_period,
            "max_holding_period": self.max_holding_period,
            "entry_conditions": self.entry_conditions,
            "exit_conditions": self.exit_conditions,
            "max_loss": self.max_loss,
            "risk_reward_ratio": self.risk_reward_ratio,
            "ai_insights": self.ai_insights,
            "market_context": self.market_context
        }


@dataclass
class DecisionContext:
    """决策上下文"""
    symbol: str
    current_price: float
    market_analysis: MarketAnalysis
    portfolio_status: Dict[str, Any]
    risk_metrics: Dict[str, Any]
    account_balance: float
    current_positions: Dict[str, Any]
    recent_trades: List[Dict[str, Any]]
    market_conditions: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "current_price": self.current_price,
            "market_analysis": self.market_analysis.to_dict(),
            "portfolio_status": self.portfolio_status,
            "risk_metrics": self.risk_metrics,
            "account_balance": self.account_balance,
            "current_positions": self.current_positions,
            "recent_trades": self.recent_trades,
            "market_conditions": self.market_conditions
        }


class DecisionMaker:
    """AI决策制定器"""
    
    def __init__(self):
        self.market_analyzer = MarketAnalyzer()
        self.decision_history = deque(maxlen=1000)  # 使用deque自动限制大小
        self.max_history_size = 1000
        
        # 决策参数（从配置加载）
        self.min_confidence_threshold = trading_config.min_confidence_threshold
        self.max_risk_per_trade = trading_config.max_risk_per_trade
        self.max_portfolio_risk = trading_config.max_portfolio_risk
        
        # AI模型权重
        self.model_weights = {
            ModelType.QWEN_LONG: 0.6,
            ModelType.DEEPSEEK_V3: 0.4
        }
        
    async def make_decision(self, symbol: str, context: DecisionContext) -> Optional[TradingDecision]:
        """制定交易决策"""
        try:
            ai_logger.info(f"开始为 {symbol} 制定交易决策")
            
            # 获取市场分析
            if not context.market_analysis:
                context.market_analysis = await self.market_analyzer.analyze_market(symbol)
                
            if not context.market_analysis:
                ai_logger.error(f"无法获取 {symbol} 的市场分析")
                return None
                
            # 预处理决策条件
            pre_decision = self._pre_process_decision(context)
            if pre_decision:
                return pre_decision
                
            # 获取多个AI模型的决策
            decisions = await self._get_multiple_ai_decisions(context)
            
            if not decisions:
                ai_logger.warning(f"无法获取 {symbol} 的AI决策")
                return None
                
            # 综合决策
            final_decision = self._aggregate_decisions(decisions, context)
            
            # 后处理决策
            final_decision = self._post_process_decision(final_decision, context)
            
            # 记录决策历史
            self._record_decision(final_decision)
            
            ai_logger.info(f"为 {symbol} 制定决策: {final_decision.decision_type.value} (置信度: {final_decision.confidence_score:.2f})")
            
            return final_decision
            
        except Exception as e:
            ai_logger.error(f"制定决策失败 ({symbol}): {e}")
            return None
            
    def _pre_process_decision(self, context: DecisionContext) -> Optional[TradingDecision]:
        """预处理决策条件"""
        try:
            # 检查账户余额
            if context.account_balance < 100:  # 最小余额限制
                return TradingDecision(
                    symbol=context.symbol,
                    decision_type=DecisionType.WAIT,
                    confidence=DecisionConfidence.VERY_HIGH,
                    confidence_score=0.95,
                    risk_level=RiskLevel.VERY_LOW,
                    reasoning="账户余额不足，暂停交易",
                    timestamp=time.time()
                )
                
            # 检查市场条件
            if context.market_analysis.volatility.value == "extreme":
                return TradingDecision(
                    symbol=context.symbol,
                    decision_type=DecisionType.WAIT,
                    confidence=DecisionConfidence.HIGH,
                    confidence_score=0.8,
                    risk_level=RiskLevel.HIGH,
                    reasoning="市场波动过于剧烈，暂停交易",
                    timestamp=time.time()
                )
                
            # 检查持仓风险
            total_risk = sum(pos.get("risk_amount", 0) for pos in context.current_positions.values())
            if total_risk > context.account_balance * self.max_portfolio_risk:
                return TradingDecision(
                    symbol=context.symbol,
                    decision_type=DecisionType.WAIT,
                    confidence=DecisionConfidence.HIGH,
                    confidence_score=0.85,
                    risk_level=RiskLevel.HIGH,
                    reasoning="投资组合风险过高，暂停新的交易",
                    timestamp=time.time()
                )
                
            return None
            
        except Exception as e:
            ai_logger.error(f"预处理决策失败: {e}")
            return None
            
    async def _get_multiple_ai_decisions(self, context: DecisionContext) -> List[TradingDecision]:
        """获取多个AI模型的决策"""
        try:
            decisions = []
            
            # 准备决策请求数据
            decision_data = {
                "symbol": context.symbol,
                "current_price": context.current_price,
                "account_balance": context.account_balance,
                "current_position": context.current_positions.get(context.symbol, {}),
                "risk_level": "medium",
                "market_analysis": context.market_analysis.analysis_summary,
                "technical_indicators": context.market_analysis.technical_indicators.to_dict(),
                "risk_metrics": context.risk_metrics
            }
            
            # 并行请求多个模型，添加超时控制
            tasks = []
            for model_type in self.model_weights.keys():
                task = asyncio.create_task(
                    asyncio.wait_for(
                        self._get_ai_decision_from_model(model_type, decision_data, context),
                        timeout=30.0  # 30秒超时
                    )
                )
                tasks.append(task)
                
            # 等待所有任务完成，使用TaskGroup更高效
            results = []
            for task in asyncio.as_completed(tasks):
                try:
                    result = await task
                    results.append(result)
                except asyncio.TimeoutError:
                    ai_logger.warning("AI决策请求超时")
                    results.append(asyncio.TimeoutError("AI decision timeout"))
                except Exception as e:
                    ai_logger.error(f"AI决策请求失败: {e}")
                    results.append(e)
            
            # 处理结果
            for result in results:
                if isinstance(result, TradingDecision):
                    decisions.append(result)
                elif isinstance(result, Exception):
                    ai_logger.error(f"AI决策请求失败: {result}")
                    
            return decisions
            
        except Exception as e:
            ai_logger.error(f"获取AI决策失败: {e}")
            return []
            
    async def _get_ai_decision_from_model(self, model_type: ModelType, decision_data: Dict[str, Any], 
                                        context: DecisionContext) -> Optional[TradingDecision]:
        """从特定模型获取决策"""
        try:
            # 格式化提示
            formatted_prompt = prompt_manager.format_prompt("trading_decision", decision_data)
            
            if not formatted_prompt:
                return None
                
            # 创建AI请求
            ai_request = ModelRequest(
                prompt=formatted_prompt["user_prompt"],
                model_type=model_type,
                system_message=formatted_prompt["system_message"],
                temperature=0.3,
                max_tokens=1500
            )
            
            # 获取AI响应
            ai_response = await model_manager.generate(ai_request)
            
            if not ai_response or ai_response.confidence < self.min_confidence_threshold:
                return None
                
            # 解析响应
            parsed_response = response_parser.parse_response(
                ai_response.content,
                ResponseType.TRADING_DECISION
            )
            
            if not parsed_response.structured_data:
                return None
                
            # 构建决策对象
            decision = self._build_decision_from_ai_response(
                parsed_response.structured_data,
                ai_response,
                context
            )
            
            return decision
            
        except Exception as e:
            ai_logger.error(f"从模型 {model_type.value} 获取决策失败: {e}")
            return None
            
    def _build_decision_from_ai_response(self, ai_data: Dict[str, Any], 
                                       ai_response, context: DecisionContext) -> TradingDecision:
        """从AI响应构建决策"""
        try:
            # 解析决策类型
            decision_str = ai_data.get("decision", "hold").lower()
            decision_type = DecisionType(decision_str) if decision_str in [d.value for d in DecisionType] else DecisionType.HOLD
            
            # 解析置信度
            confidence_score = float(ai_data.get("confidence_score", ai_response.confidence))
            confidence = self._score_to_confidence(confidence_score)
            
            # 解析风险等级
            risk_level = RiskLevel.MEDIUM  # 默认中等风险
            
            # 构建决策
            decision = TradingDecision(
                symbol=context.symbol,
                decision_type=decision_type,
                confidence=confidence,
                confidence_score=confidence_score,
                risk_level=risk_level,
                reasoning=ai_data.get("reasoning", ""),
                timestamp=time.time(),
                ai_insights=ai_response.content,
                market_context=context.market_analysis.to_dict()
            )
            
            # 设置交易参数
            decision.entry_price = ai_data.get("entry_price", context.current_price)
            decision.stop_loss = ai_data.get("stop_loss")
            decision.take_profit = ai_data.get("take_profit")
            decision.position_size = ai_data.get("position_size", 0.01)
            
            # 计算风险回报比
            if decision.stop_loss and decision.take_profit:
                risk = abs(decision.entry_price - decision.stop_loss)
                reward = abs(decision.take_profit - decision.entry_price)
                if risk > 0:
                    decision.risk_reward_ratio = reward / risk
                    
            return decision
            
        except Exception as e:
            ai_logger.error(f"构建决策失败: {e}")
            return TradingDecision(
                symbol=context.symbol,
                decision_type=DecisionType.WAIT,
                confidence=DecisionConfidence.LOW,
                confidence_score=0.3,
                risk_level=RiskLevel.HIGH,
                reasoning="AI决策解析失败",
                timestamp=time.time()
            )
            
    def _score_to_confidence(self, score: float) -> DecisionConfidence:
        """分数转置信度"""
        if score >= 0.9:
            return DecisionConfidence.VERY_HIGH
        elif score >= 0.7:
            return DecisionConfidence.HIGH
        elif score >= 0.5:
            return DecisionConfidence.MEDIUM
        elif score >= 0.3:
            return DecisionConfidence.LOW
        else:
            return DecisionConfidence.VERY_LOW
            
    def _aggregate_decisions(self, decisions: List[TradingDecision], 
                           context: DecisionContext) -> TradingDecision:
        """聚合多个决策"""
        try:
            if not decisions:
                return TradingDecision(
                    symbol=context.symbol,
                    decision_type=DecisionType.WAIT,
                    confidence=DecisionConfidence.VERY_LOW,
                    confidence_score=0.0,
                    risk_level=RiskLevel.HIGH,
                    reasoning="无有效决策",
                    timestamp=time.time()
                )
                
            if len(decisions) == 1:
                return decisions[0]
                
            # 加权平均置信度
            total_weight = 0
            weighted_confidence = 0
            decision_votes = {}
            
            for decision in decisions:
                # 获取模型权重（根据决策质量动态调整）
                weight = self._get_decision_weight(decision)
                total_weight += weight
                weighted_confidence += decision.confidence_score * weight
                
                # 统计决策投票
                decision_type = decision.decision_type
                if decision_type not in decision_votes:
                    decision_votes[decision_type] = 0
                decision_votes[decision_type] += weight
                
            # 选择权重最高的决策类型
            final_decision_type = max(decision_votes, key=decision_votes.get)
            final_confidence_score = weighted_confidence / total_weight if total_weight > 0 else 0
            
            # 聚合同类决策的参数
            same_type_decisions = [d for d in decisions if d.decision_type == final_decision_type]
            
            # 平均交易参数
            avg_entry_price = self._average_non_none([d.entry_price for d in same_type_decisions])
            avg_stop_loss = self._average_non_none([d.stop_loss for d in same_type_decisions])
            avg_take_profit = self._average_non_none([d.take_profit for d in same_type_decisions])
            avg_position_size = self._average_non_none([d.position_size for d in same_type_decisions])
            
            # 合并推理
            reasoning_parts = [d.reasoning for d in same_type_decisions if d.reasoning]
            combined_reasoning = " | ".join(reasoning_parts)
            
            # 创建最终决策
            final_decision = TradingDecision(
                symbol=context.symbol,
                decision_type=final_decision_type,
                confidence=self._score_to_confidence(final_confidence_score),
                confidence_score=final_confidence_score,
                risk_level=self._aggregate_risk_level([d.risk_level for d in same_type_decisions]),
                reasoning=combined_reasoning,
                timestamp=time.time(),
                entry_price=avg_entry_price,
                stop_loss=avg_stop_loss,
                take_profit=avg_take_profit,
                position_size=avg_position_size,
                market_context=context.market_analysis.to_dict()
            )
            
            return final_decision
            
        except Exception as e:
            ai_logger.error(f"聚合决策失败: {e}")
            return TradingDecision(
                symbol=context.symbol,
                decision_type=DecisionType.WAIT,
                confidence=DecisionConfidence.LOW,
                confidence_score=0.2,
                risk_level=RiskLevel.HIGH,
                reasoning="决策聚合失败",
                timestamp=time.time()
            )
            
    def _get_decision_weight(self, decision: TradingDecision) -> float:
        """获取决策权重"""
        # 基础权重基于置信度
        base_weight = decision.confidence_score
        
        # 根据历史表现调整权重（这里简化为固定值）
        performance_weight = 1.0
        
        # 根据市场条件调整权重
        market_weight = 1.0
        
        return base_weight * performance_weight * market_weight
        
    def _average_non_none(self, values: List[Optional[float]]) -> Optional[float]:
        """计算非空值的平均数"""
        non_none_values = [v for v in values if v is not None]
        if not non_none_values:
            return None
        return sum(non_none_values) / len(non_none_values)
        
    def _aggregate_risk_level(self, risk_levels: List[RiskLevel]) -> RiskLevel:
        """聚合风险等级"""
        if not risk_levels:
            return RiskLevel.MEDIUM
            
        # 取最高风险等级
        risk_values = {
            RiskLevel.VERY_LOW: 1,
            RiskLevel.LOW: 2,
            RiskLevel.MEDIUM: 3,
            RiskLevel.HIGH: 4,
            RiskLevel.VERY_HIGH: 5
        }
        
        max_risk_value = max(risk_values[risk] for risk in risk_levels)
        
        for risk, value in risk_values.items():
            if value == max_risk_value:
                return risk
                
        return RiskLevel.MEDIUM
        
    def _post_process_decision(self, decision: TradingDecision, 
                             context: DecisionContext) -> TradingDecision:
        """后处理决策"""
        try:
            # 调整仓位大小
            if decision.position_size:
                max_position_size = self._calculate_max_position_size(context)
                decision.position_size = min(decision.position_size, max_position_size)
                
            # 验证交易参数
            decision = self._validate_trading_parameters(decision, context)
            
            # 添加退出条件
            decision.exit_conditions = self._generate_exit_conditions(decision, context)
            
            # 计算最大损失
            if decision.stop_loss and decision.entry_price and decision.position_size:
                decision.max_loss = abs(decision.entry_price - decision.stop_loss) * decision.position_size
                
            return decision
            
        except Exception as e:
            ai_logger.error(f"后处理决策失败: {e}")
            return decision
            
    def _calculate_max_position_size(self, context: DecisionContext) -> float:
        """计算最大仓位大小"""
        try:
            # 基于账户余额和风险限制
            max_risk_amount = context.account_balance * self.max_risk_per_trade
            
            # 简化计算：假设2%的价格变动风险
            price_risk_ratio = 0.02
            max_position_size = max_risk_amount / (context.current_price * price_risk_ratio)
            
            return max_position_size
            
        except Exception as e:
            ai_logger.error(f"计算最大仓位失败: {e}")
            return 0.01  # 默认最小仓位
            
    def _validate_trading_parameters(self, decision: TradingDecision, 
                                   context: DecisionContext) -> TradingDecision:
        """验证交易参数"""
        try:
            # 验证价格合理性
            if decision.entry_price:
                price_deviation = abs(decision.entry_price - context.current_price) / context.current_price
                if price_deviation > 0.05:  # 5%偏差限制
                    decision.entry_price = context.current_price
                    
            # 验证止损止盈合理性
            if decision.stop_loss and decision.take_profit and decision.entry_price:
                if decision.decision_type == DecisionType.BUY:
                    if decision.stop_loss >= decision.entry_price:
                        decision.stop_loss = decision.entry_price * 0.98
                    if decision.take_profit <= decision.entry_price:
                        decision.take_profit = decision.entry_price * 1.02
                elif decision.decision_type == DecisionType.SELL:
                    if decision.stop_loss <= decision.entry_price:
                        decision.stop_loss = decision.entry_price * 1.02
                    if decision.take_profit >= decision.entry_price:
                        decision.take_profit = decision.entry_price * 0.98
                        
            return decision
            
        except Exception as e:
            ai_logger.error(f"验证交易参数失败: {e}")
            return decision
            
    def _generate_exit_conditions(self, decision: TradingDecision, 
                                context: DecisionContext) -> List[str]:
        """生成退出条件"""
        try:
            conditions = []
            
            # 时间条件
            if decision.decision_type in [DecisionType.BUY, DecisionType.SELL]:
                conditions.append("持仓时间超过24小时")
                conditions.append("市场波动性超过极限水平")
                
            # 技术条件
            if context.market_analysis.trend.value == "bullish" and decision.decision_type == DecisionType.BUY:
                conditions.append("趋势转为看跌")
            elif context.market_analysis.trend.value == "bearish" and decision.decision_type == DecisionType.SELL:
                conditions.append("趋势转为看涨")
                
            # 风险条件
            conditions.append("投资组合风险超过限制")
            conditions.append("账户余额低于最低要求")
            
            return conditions
            
        except Exception as e:
            ai_logger.error(f"生成退出条件失败: {e}")
            return []
            
    def _record_decision(self, decision: TradingDecision):
        """记录决策历史"""
        try:
            self.decision_history.append(decision)
            
            # 限制历史记录大小
            if len(self.decision_history) > self.max_history_size:
                self.decision_history = self.decision_history[-self.max_history_size:]
                
            ai_logger.debug(f"记录决策: {decision.symbol} - {decision.decision_type.value}")
            
        except Exception as e:
            ai_logger.error(f"记录决策失败: {e}")
            
    def get_decision_history(self, symbol: str = None, limit: int = 100) -> List[TradingDecision]:
        """获取决策历史"""
        try:
            history = self.decision_history
            
            if symbol:
                history = [d for d in history if d.symbol == symbol]
                
            return history[-limit:]
            
        except Exception as e:
            ai_logger.error(f"获取决策历史失败: {e}")
            return []
            
    def get_decision_stats(self) -> Dict[str, Any]:
        """获取决策统计"""
        try:
            if not self.decision_history:
                return {}
                
            total_decisions = len(self.decision_history)
            decision_types = {}
            confidence_levels = {}
            
            for decision in self.decision_history:
                # 统计决策类型
                decision_type = decision.decision_type.value
                decision_types[decision_type] = decision_types.get(decision_type, 0) + 1
                
                # 统计置信度
                confidence = decision.confidence.value
                confidence_levels[confidence] = confidence_levels.get(confidence, 0) + 1
                
            return {
                "total_decisions": total_decisions,
                "decision_types": decision_types,
                "confidence_levels": confidence_levels,
                "average_confidence": sum(d.confidence_score for d in self.decision_history) / total_decisions
            }
            
        except Exception as e:
            ai_logger.error(f"获取决策统计失败: {e}")
            return {}


# 全局决策制定器实例
decision_maker = DecisionMaker()