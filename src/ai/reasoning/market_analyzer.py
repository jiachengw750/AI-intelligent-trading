# -*- coding: utf-8 -*-
"""
市场分析推理器
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
from src.ai.models import model_manager, prompt_manager, response_parser, ModelRequest, ModelType, ResponseType
from src.data import collector_manager, storage_manager
from src.utils.helpers.logger import ai_logger
from src.utils.helpers.async_utils import async_utils
from config import ai_config, system_config


class MarketTrend(Enum):
    """市场趋势"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    SIDEWAYS = "sideways"
    UNCERTAIN = "uncertain"


class MarketVolatility(Enum):
    """市场波动性"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class MarketSentiment(Enum):
    """市场情绪"""
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


@dataclass
class TechnicalIndicators:
    """技术指标"""
    rsi: float = 0.0
    macd: float = 0.0
    macd_signal: float = 0.0
    macd_histogram: float = 0.0
    bollinger_upper: float = 0.0
    bollinger_lower: float = 0.0
    bollinger_middle: float = 0.0
    sma_20: float = 0.0
    sma_50: float = 0.0
    sma_200: float = 0.0
    ema_12: float = 0.0
    ema_26: float = 0.0
    atr: float = 0.0
    volume_sma: float = 0.0
    stoch_k: float = 0.0
    stoch_d: float = 0.0
    williams_r: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        """转换为字典"""
        return {
            "rsi": self.rsi,
            "macd": self.macd,
            "macd_signal": self.macd_signal,
            "macd_histogram": self.macd_histogram,
            "bollinger_upper": self.bollinger_upper,
            "bollinger_lower": self.bollinger_lower,
            "bollinger_middle": self.bollinger_middle,
            "sma_20": self.sma_20,
            "sma_50": self.sma_50,
            "sma_200": self.sma_200,
            "ema_12": self.ema_12,
            "ema_26": self.ema_26,
            "atr": self.atr,
            "volume_sma": self.volume_sma,
            "stoch_k": self.stoch_k,
            "stoch_d": self.stoch_d,
            "williams_r": self.williams_r
        }


@dataclass
class MarketAnalysis:
    """市场分析结果"""
    symbol: str
    timestamp: float
    current_price: float
    trend: MarketTrend
    volatility: MarketVolatility
    sentiment: MarketSentiment
    technical_indicators: TechnicalIndicators
    support_levels: List[float] = field(default_factory=list)
    resistance_levels: List[float] = field(default_factory=list)
    price_targets: Dict[str, float] = field(default_factory=dict)
    confidence_score: float = 0.0
    analysis_summary: str = ""
    ai_insights: str = ""
    risk_factors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "current_price": self.current_price,
            "trend": self.trend.value,
            "volatility": self.volatility.value,
            "sentiment": self.sentiment.value,
            "technical_indicators": self.technical_indicators.to_dict(),
            "support_levels": self.support_levels,
            "resistance_levels": self.resistance_levels,
            "price_targets": self.price_targets,
            "confidence_score": self.confidence_score,
            "analysis_summary": self.analysis_summary,
            "ai_insights": self.ai_insights,
            "risk_factors": self.risk_factors
        }


class TechnicalAnalyzer:
    """技术分析器"""
    
    def __init__(self):
        self.required_periods = 200  # 需要的最小数据周期
        
    def calculate_indicators(self, df: pd.DataFrame) -> TechnicalIndicators:
        """计算技术指标"""
        try:
            if len(df) < self.required_periods:
                ai_logger.warning(f"数据不足，需要至少 {self.required_periods} 个周期")
                return TechnicalIndicators()
                
            indicators = TechnicalIndicators()
            
            # 确保数据类型正确
            df = df.copy()
            df['close'] = pd.to_numeric(df['close'], errors='coerce')
            df['high'] = pd.to_numeric(df['high'], errors='coerce')
            df['low'] = pd.to_numeric(df['low'], errors='coerce')
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
            
            # RSI
            indicators.rsi = self._calculate_rsi(df['close'])
            
            # MACD
            indicators.macd, indicators.macd_signal, indicators.macd_histogram = self._calculate_macd(df['close'])
            
            # 布林带
            indicators.bollinger_upper, indicators.bollinger_middle, indicators.bollinger_lower = self._calculate_bollinger_bands(df['close'])
            
            # 移动平均线
            indicators.sma_20 = df['close'].rolling(window=20).mean().iloc[-1]
            indicators.sma_50 = df['close'].rolling(window=50).mean().iloc[-1]
            indicators.sma_200 = df['close'].rolling(window=200).mean().iloc[-1]
            
            # EMA
            indicators.ema_12 = df['close'].ewm(span=12).mean().iloc[-1]
            indicators.ema_26 = df['close'].ewm(span=26).mean().iloc[-1]
            
            # ATR
            indicators.atr = self._calculate_atr(df)
            
            # 成交量移动平均
            indicators.volume_sma = df['volume'].rolling(window=20).mean().iloc[-1]
            
            # 随机指标
            indicators.stoch_k, indicators.stoch_d = self._calculate_stochastic(df)
            
            # 威廉指标
            indicators.williams_r = self._calculate_williams_r(df)
            
            return indicators
            
        except Exception as e:
            ai_logger.error(f"计算技术指标失败: {e}")
            return TechnicalIndicators()
            
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """计算RSI"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return float(rsi.iloc[-1])
        except:
            return 50.0
            
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[float, float, float]:
        """计算MACD"""
        try:
            ema_fast = prices.ewm(span=fast).mean()
            ema_slow = prices.ewm(span=slow).mean()
            macd = ema_fast - ema_slow
            signal_line = macd.ewm(span=signal).mean()
            histogram = macd - signal_line
            
            return float(macd.iloc[-1]), float(signal_line.iloc[-1]), float(histogram.iloc[-1])
        except:
            return 0.0, 0.0, 0.0
            
    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: float = 2) -> Tuple[float, float, float]:
        """计算布林带"""
        try:
            sma = prices.rolling(window=period).mean()
            std = prices.rolling(window=period).std()
            upper = sma + (std * std_dev)
            lower = sma - (std * std_dev)
            
            return float(upper.iloc[-1]), float(sma.iloc[-1]), float(lower.iloc[-1])
        except:
            return 0.0, 0.0, 0.0
            
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """计算ATR"""
        try:
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = true_range.rolling(window=period).mean()
            
            return float(atr.iloc[-1])
        except:
            return 0.0
            
    def _calculate_stochastic(self, df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> Tuple[float, float]:
        """计算随机指标"""
        try:
            lowest_low = df['low'].rolling(window=k_period).min()
            highest_high = df['high'].rolling(window=k_period).max()
            
            k_percent = 100 * ((df['close'] - lowest_low) / (highest_high - lowest_low))
            d_percent = k_percent.rolling(window=d_period).mean()
            
            return float(k_percent.iloc[-1]), float(d_percent.iloc[-1])
        except:
            return 50.0, 50.0
            
    def _calculate_williams_r(self, df: pd.DataFrame, period: int = 14) -> float:
        """计算威廉指标"""
        try:
            highest_high = df['high'].rolling(window=period).max()
            lowest_low = df['low'].rolling(window=period).min()
            
            williams_r = -100 * ((highest_high - df['close']) / (highest_high - lowest_low))
            
            return float(williams_r.iloc[-1])
        except:
            return -50.0


class MarketAnalyzer:
    """市场分析器"""
    
    def __init__(self):
        self.technical_analyzer = TechnicalAnalyzer()
        self.analysis_cache: Dict[str, MarketAnalysis] = {}
        self.cache_ttl = 300  # 5分钟缓存
        
    async def analyze_market(self, symbol: str, timeframe: str = "1h") -> Optional[MarketAnalysis]:
        """分析市场"""
        try:
            # 检查缓存
            cache_key = f"{symbol}_{timeframe}"
            if cache_key in self.analysis_cache:
                cached_analysis = self.analysis_cache[cache_key]
                if time.time() - cached_analysis.timestamp < self.cache_ttl:
                    return cached_analysis
                    
            # 获取历史数据
            market_data = await self._get_market_data(symbol, timeframe)
            if not market_data:
                return None
                
            # 技术分析
            technical_indicators = self.technical_analyzer.calculate_indicators(market_data)
            
            # 计算支撑阻力位
            support_levels, resistance_levels = self._calculate_support_resistance(market_data)
            
            # 判断趋势
            trend = self._determine_trend(market_data, technical_indicators)
            
            # 计算波动性
            volatility = self._calculate_volatility(market_data, technical_indicators)
            
            # 获取当前价格
            current_price = float(market_data['close'].iloc[-1])
            
            # 计算价格目标
            price_targets = self._calculate_price_targets(current_price, support_levels, resistance_levels, trend)
            
            # 创建基础分析
            analysis = MarketAnalysis(
                symbol=symbol,
                timestamp=time.time(),
                current_price=current_price,
                trend=trend,
                volatility=volatility,
                sentiment=MarketSentiment.NEUTRAL,  # 默认中性，AI会分析
                technical_indicators=technical_indicators,
                support_levels=support_levels,
                resistance_levels=resistance_levels,
                price_targets=price_targets,
                confidence_score=0.0,  # AI会计算
                risk_factors=[]  # AI会分析
            )
            
            # AI增强分析
            enhanced_analysis = await self._enhance_with_ai(analysis, market_data)
            
            # 缓存结果
            self.analysis_cache[cache_key] = enhanced_analysis
            
            return enhanced_analysis
            
        except Exception as e:
            ai_logger.error(f"市场分析失败 ({symbol}): {e}")
            return None
            
    async def _get_market_data(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """获取市场数据"""
        try:
            # 从存储中获取历史数据
            query = {
                "symbol": symbol,
                "data_type": "kline",
                "start_time": time.time() - 86400 * 30,  # 30天数据
                "end_time": time.time(),
                "limit": 1000
            }
            
            data = await storage_manager.retrieve_data(query)
            
            if not data:
                ai_logger.warning(f"未找到 {symbol} 的历史数据")
                return None
                
            # 转换为DataFrame
            records = []
            for item in data:
                if 'data' in item and 'klines' in item['data']:
                    records.extend(item['data']['klines'])
                    
            if not records:
                return None
                
            df = pd.DataFrame(records)
            
            # 确保列名正确
            required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            if not all(col in df.columns for col in required_columns):
                ai_logger.error(f"数据格式不正确，缺少必要列: {required_columns}")
                return None
                
            # 排序并去重
            df = df.sort_values('timestamp').drop_duplicates(subset=['timestamp'])
            
            return df
            
        except Exception as e:
            ai_logger.error(f"获取市场数据失败: {e}")
            return None
            
    def _calculate_support_resistance(self, df: pd.DataFrame) -> Tuple[List[float], List[float]]:
        """计算支撑阻力位"""
        try:
            # 使用局部极值计算支撑阻力
            highs = df['high'].values
            lows = df['low'].values
            
            # 找到局部高点和低点
            resistance_levels = []
            support_levels = []
            
            window = 10
            for i in range(window, len(highs) - window):
                # 局部高点
                if all(highs[i] >= highs[i-j] for j in range(1, window+1)) and \
                   all(highs[i] >= highs[i+j] for j in range(1, window+1)):
                    resistance_levels.append(highs[i])
                    
                # 局部低点
                if all(lows[i] <= lows[i-j] for j in range(1, window+1)) and \
                   all(lows[i] <= lows[i+j] for j in range(1, window+1)):
                    support_levels.append(lows[i])
                    
            # 去重并排序
            resistance_levels = sorted(list(set(resistance_levels)), reverse=True)[:5]
            support_levels = sorted(list(set(support_levels)))[:5]
            
            return support_levels, resistance_levels
            
        except Exception as e:
            ai_logger.error(f"计算支撑阻力位失败: {e}")
            return [], []
            
    def _determine_trend(self, df: pd.DataFrame, indicators: TechnicalIndicators) -> MarketTrend:
        """判断趋势"""
        try:
            current_price = float(df['close'].iloc[-1])
            
            # 多重信号确认趋势
            bullish_signals = 0
            bearish_signals = 0
            
            # 移动平均线信号
            if current_price > indicators.sma_20 > indicators.sma_50:
                bullish_signals += 1
            elif current_price < indicators.sma_20 < indicators.sma_50:
                bearish_signals += 1
                
            # MACD信号
            if indicators.macd > indicators.macd_signal and indicators.macd_histogram > 0:
                bullish_signals += 1
            elif indicators.macd < indicators.macd_signal and indicators.macd_histogram < 0:
                bearish_signals += 1
                
            # RSI信号
            if 30 < indicators.rsi < 70:
                if indicators.rsi > 50:
                    bullish_signals += 0.5
                else:
                    bearish_signals += 0.5
                    
            # 价格位置相对于布林带
            if current_price > indicators.bollinger_middle:
                bullish_signals += 0.5
            elif current_price < indicators.bollinger_middle:
                bearish_signals += 0.5
                
            # 判断趋势
            if bullish_signals > bearish_signals + 1:
                return MarketTrend.BULLISH
            elif bearish_signals > bullish_signals + 1:
                return MarketTrend.BEARISH
            elif abs(bullish_signals - bearish_signals) <= 1:
                return MarketTrend.SIDEWAYS
            else:
                return MarketTrend.UNCERTAIN
                
        except Exception as e:
            ai_logger.error(f"判断趋势失败: {e}")
            return MarketTrend.UNCERTAIN
            
    def _calculate_volatility(self, df: pd.DataFrame, indicators: TechnicalIndicators) -> MarketVolatility:
        """计算波动性"""
        try:
            # 使用ATR和价格变化率计算波动性
            current_price = float(df['close'].iloc[-1])
            
            # ATR相对于价格的比例
            atr_ratio = indicators.atr / current_price if current_price > 0 else 0
            
            # 近期价格变化率
            price_changes = df['close'].pct_change().dropna()
            recent_volatility = price_changes.tail(20).std()
            
            # 综合评估
            volatility_score = (atr_ratio * 0.6) + (recent_volatility * 0.4)
            
            if volatility_score < 0.01:
                return MarketVolatility.LOW
            elif volatility_score < 0.03:
                return MarketVolatility.MEDIUM
            elif volatility_score < 0.05:
                return MarketVolatility.HIGH
            else:
                return MarketVolatility.EXTREME
                
        except Exception as e:
            ai_logger.error(f"计算波动性失败: {e}")
            return MarketVolatility.MEDIUM
            
    def _calculate_price_targets(self, current_price: float, support_levels: List[float], 
                               resistance_levels: List[float], trend: MarketTrend) -> Dict[str, float]:
        """计算价格目标"""
        try:
            targets = {}
            
            if trend == MarketTrend.BULLISH:
                # 上涨目标
                if resistance_levels:
                    targets["target_1"] = resistance_levels[0]
                    if len(resistance_levels) > 1:
                        targets["target_2"] = resistance_levels[1]
                        
                # 止损位
                if support_levels:
                    targets["stop_loss"] = support_levels[-1]
                    
            elif trend == MarketTrend.BEARISH:
                # 下跌目标
                if support_levels:
                    targets["target_1"] = support_levels[-1]
                    if len(support_levels) > 1:
                        targets["target_2"] = support_levels[-2]
                        
                # 止损位
                if resistance_levels:
                    targets["stop_loss"] = resistance_levels[0]
                    
            else:
                # 区间交易
                if support_levels and resistance_levels:
                    targets["range_low"] = support_levels[-1]
                    targets["range_high"] = resistance_levels[0]
                    
            return targets
            
        except Exception as e:
            ai_logger.error(f"计算价格目标失败: {e}")
            return {}
            
    async def _enhance_with_ai(self, analysis: MarketAnalysis, market_data: pd.DataFrame) -> MarketAnalysis:
        """使用AI增强分析"""
        try:
            # 构建AI分析请求
            analysis_data = {
                "symbol": analysis.symbol,
                "timeframe": "1h",
                "current_price": analysis.current_price,
                "technical_indicators": analysis.technical_indicators.to_dict(),
                "market_depth": self._prepare_market_depth_data(market_data)
            }
            
            # 格式化提示
            formatted_prompt = prompt_manager.format_prompt("market_analysis", analysis_data)
            
            if not formatted_prompt:
                return analysis
                
            # 创建AI请求
            ai_request = ModelRequest(
                prompt=formatted_prompt["user_prompt"],
                model_type=ModelType.QWEN_LONG,
                system_message=formatted_prompt["system_message"],
                temperature=0.3,
                max_tokens=2000
            )
            
            # 获取AI响应
            ai_response = await model_manager.generate(ai_request)
            
            if ai_response and ai_response.confidence > 0.5:
                # 解析AI响应
                parsed_response = response_parser.parse_response(
                    ai_response.content,
                    ResponseType.MARKET_ANALYSIS
                )
                
                if parsed_response.structured_data:
                    # 更新分析结果
                    analysis.confidence_score = ai_response.confidence
                    analysis.ai_insights = ai_response.content
                    analysis.analysis_summary = parsed_response.structured_data.get("outlook", "")
                    
                    # 提取风险因素
                    risk_factors = parsed_response.structured_data.get("risk_factors", "")
                    if risk_factors:
                        analysis.risk_factors = [rf.strip() for rf in risk_factors.split(",")]
                        
                    # 更新情绪分析
                    sentiment_str = parsed_response.structured_data.get("sentiment", "neutral")
                    sentiment_mapping = {
                        "积极": MarketSentiment.POSITIVE,
                        "消极": MarketSentiment.NEGATIVE,
                        "中性": MarketSentiment.NEUTRAL
                    }
                    analysis.sentiment = sentiment_mapping.get(sentiment_str, MarketSentiment.NEUTRAL)
                    
            return analysis
            
        except Exception as e:
            ai_logger.error(f"AI增强分析失败: {e}")
            return analysis
            
    def _prepare_market_depth_data(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """准备市场深度数据"""
        try:
            recent_data = market_data.tail(24)  # 最近24个周期
            
            return {
                "volume_profile": {
                    "avg_volume": float(recent_data['volume'].mean()),
                    "volume_trend": "increasing" if recent_data['volume'].iloc[-1] > recent_data['volume'].mean() else "decreasing",
                    "volume_spike": float(recent_data['volume'].max() / recent_data['volume'].mean())
                },
                "price_action": {
                    "price_range": float(recent_data['high'].max() - recent_data['low'].min()),
                    "consolidation": float(recent_data['close'].std()),
                    "momentum": float((recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]) / recent_data['close'].iloc[0])
                }
            }
            
        except Exception as e:
            ai_logger.error(f"准备市场深度数据失败: {e}")
            return {}
            
    def get_analysis_summary(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取分析摘要"""
        analysis = self.analysis_cache.get(f"{symbol}_1h")
        if analysis:
            return {
                "symbol": analysis.symbol,
                "trend": analysis.trend.value,
                "volatility": analysis.volatility.value,
                "sentiment": analysis.sentiment.value,
                "confidence": analysis.confidence_score,
                "last_updated": analysis.timestamp
            }
        return None
        
    def clear_cache(self):
        """清除缓存"""
        self.analysis_cache.clear()
        ai_logger.info("市场分析缓存已清除")


# 全局市场分析器实例
market_analyzer = MarketAnalyzer()