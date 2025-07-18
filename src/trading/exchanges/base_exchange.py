# -*- coding: utf-8 -*-
"""
交易所基础接口
"""

import asyncio
import aiohttp
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from src.utils.helpers.logger import trade_logger
from src.core.exceptions.trading_exceptions import ExchangeException, OrderException


class OrderSide(Enum):
    """订单方向"""
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """订单类型"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIAL = "partial"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class OrderBook:
    """订单簿"""
    symbol: str
    bids: List[Tuple[float, float]]  # (价格, 数量)
    asks: List[Tuple[float, float]]  # (价格, 数量)
    timestamp: float
    
    @property
    def best_bid(self) -> Optional[float]:
        """最佳买价"""
        return self.bids[0][0] if self.bids else None
        
    @property
    def best_ask(self) -> Optional[float]:
        """最佳卖价"""
        return self.asks[0][0] if self.asks else None
        
    @property
    def spread(self) -> Optional[float]:
        """买卖价差"""
        if self.best_bid and self.best_ask:
            return self.best_ask - self.best_bid
        return None
        
    @property
    def mid_price(self) -> Optional[float]:
        """中间价"""
        if self.best_bid and self.best_ask:
            return (self.best_bid + self.best_ask) / 2
        return None


@dataclass
class Trade:
    """成交记录"""
    symbol: str
    price: float
    amount: float
    side: OrderSide
    timestamp: float
    trade_id: str


@dataclass
class Kline:
    """K线数据"""
    symbol: str
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float
    interval: str


@dataclass
class Balance:
    """账户余额"""
    asset: str
    free: float
    locked: float
    
    @property
    def total(self) -> float:
        """总余额"""
        return self.free + self.locked


@dataclass
class ExchangeOrder:
    """交易所订单"""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    amount: float
    price: Optional[float]
    status: OrderStatus
    filled_amount: float = 0.0
    avg_price: float = 0.0
    timestamp: float = 0.0
    update_time: float = 0.0
    
    @property
    def remaining_amount(self) -> float:
        """剩余数量"""
        return self.amount - self.filled_amount
        
    @property
    def fill_percentage(self) -> float:
        """成交百分比"""
        return (self.filled_amount / self.amount * 100) if self.amount > 0 else 0


class BaseExchange(ABC):
    """交易所基础类"""
    
    def __init__(self, api_key: str = "", secret_key: str = "", 
                 sandbox: bool = True, rate_limit: int = 10):
        self.api_key = api_key
        self.secret_key = secret_key
        self.sandbox = sandbox
        self.rate_limit = rate_limit  # 每秒最大请求数
        
        # 连接状态
        self.is_connected = False
        self.last_ping_time = 0
        
        # 请求限制
        self.request_times = []
        
        # HTTP客户端
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.disconnect()
        
    async def connect(self):
        """连接交易所"""
        try:
            if not self.session:
                connector = aiohttp.TCPConnector(limit=100, ttl_dns_cache=300)
                timeout = aiohttp.ClientTimeout(total=30)
                self.session = aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout
                )
                
            # 测试连接
            await self.ping()
            self.is_connected = True
            trade_logger.info(f"{self.__class__.__name__} 连接成功")
            
        except Exception as e:
            trade_logger.error(f"{self.__class__.__name__} 连接失败: {e}")
            raise ExchangeException(f"连接失败: {e}")
            
    async def disconnect(self):
        """断开连接"""
        try:
            if self.session:
                await self.session.close()
                self.session = None
                
            self.is_connected = False
            trade_logger.info(f"{self.__class__.__name__} 已断开连接")
            
        except Exception as e:
            trade_logger.error(f"断开连接失败: {e}")
            
    async def _rate_limit_check(self):
        """检查请求频率限制"""
        current_time = time.time()
        
        # 清理过期的请求时间
        self.request_times = [t for t in self.request_times if current_time - t < 1]
        
        # 检查是否超过限制
        if len(self.request_times) >= self.rate_limit:
            sleep_time = 1 - (current_time - self.request_times[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
                
        # 记录当前请求时间
        self.request_times.append(current_time)
        
    async def _make_request(self, method: str, url: str, 
                          params: Dict = None, data: Dict = None,
                          headers: Dict = None) -> Dict[str, Any]:
        """发起HTTP请求"""
        try:
            await self._rate_limit_check()
            
            if not self.session:
                raise ExchangeException("未连接到交易所")
                
            async with self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                headers=headers
            ) as response:
                
                if response.status >= 400:
                    error_text = await response.text()
                    raise ExchangeException(f"HTTP {response.status}: {error_text}")
                    
                result = await response.json()
                return result
                
        except asyncio.TimeoutError:
            raise ExchangeException("请求超时")
        except Exception as e:
            trade_logger.error(f"HTTP请求失败: {e}")
            raise ExchangeException(f"请求失败: {e}")
            
    @abstractmethod
    async def ping(self) -> bool:
        """测试连接"""
        pass
        
    @abstractmethod
    async def get_server_time(self) -> int:
        """获取服务器时间"""
        pass
        
    @abstractmethod
    async def get_exchange_info(self) -> Dict[str, Any]:
        """获取交易所信息"""
        pass
        
    @abstractmethod
    async def get_symbols(self) -> List[str]:
        """获取所有交易对"""
        pass
        
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """获取行情数据"""
        pass
        
    @abstractmethod
    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderBook:
        """获取订单簿"""
        pass
        
    @abstractmethod
    async def get_trades(self, symbol: str, limit: int = 50) -> List[Trade]:
        """获取最近成交记录"""
        pass
        
    @abstractmethod
    async def get_klines(self, symbol: str, interval: str, 
                        start_time: Optional[int] = None,
                        end_time: Optional[int] = None,
                        limit: int = 500) -> List[Kline]:
        """获取K线数据"""
        pass
        
    @abstractmethod
    async def get_account(self) -> Dict[str, Any]:
        """获取账户信息"""
        pass
        
    @abstractmethod
    async def get_balances(self) -> List[Balance]:
        """获取账户余额"""
        pass
        
    @abstractmethod
    async def place_order(self, symbol: str, side: OrderSide, 
                         order_type: OrderType, amount: float,
                         price: Optional[float] = None,
                         stop_price: Optional[float] = None,
                         time_in_force: str = "GTC",
                         client_order_id: Optional[str] = None) -> ExchangeOrder:
        """下单"""
        pass
        
    @abstractmethod
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """撤单"""
        pass
        
    @abstractmethod
    async def cancel_all_orders(self, symbol: Optional[str] = None) -> bool:
        """撤销所有订单"""
        pass
        
    @abstractmethod
    async def get_order(self, symbol: str, order_id: str) -> ExchangeOrder:
        """查询订单"""
        pass
        
    @abstractmethod
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[ExchangeOrder]:
        """获取活跃订单"""
        pass
        
    @abstractmethod
    async def get_order_history(self, symbol: Optional[str] = None,
                               start_time: Optional[int] = None,
                               end_time: Optional[int] = None,
                               limit: int = 500) -> List[ExchangeOrder]:
        """获取历史订单"""
        pass
        
    @abstractmethod
    async def get_trades_history(self, symbol: Optional[str] = None,
                                start_time: Optional[int] = None,
                                end_time: Optional[int] = None,
                                limit: int = 500) -> List[Trade]:
        """获取成交历史"""
        pass
        
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            current_time = time.time()
            
            # 检查连接状态
            if not self.is_connected:
                return False
                
            # 检查ping延迟
            if current_time - self.last_ping_time > 30:  # 30秒ping一次
                ping_result = await self.ping()
                self.last_ping_time = current_time
                
                if not ping_result:
                    self.is_connected = False
                    return False
                    
            return True
            
        except Exception as e:
            trade_logger.error(f"健康检查失败: {e}")
            self.is_connected = False
            return False
            
    def get_exchange_name(self) -> str:
        """获取交易所名称"""
        return self.__class__.__name__
        
    def is_sandbox_mode(self) -> bool:
        """是否为沙盒模式"""
        return self.sandbox