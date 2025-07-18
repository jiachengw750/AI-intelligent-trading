"""
交易相关数据模式
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum


class OrderType(str, Enum):
    """订单类型枚举"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"
    OCO = "oco"  # One-Cancels-Other


class OrderSide(str, Enum):
    """订单方向枚举"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    """订单状态枚举"""
    PENDING = "pending"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class TimeInForce(str, Enum):
    """订单时效性枚举"""
    GTC = "GTC"  # Good Till Cancelled
    IOC = "IOC"  # Immediate Or Cancel
    FOK = "FOK"  # Fill Or Kill
    GTD = "GTD"  # Good Till Date


class CreateOrderRequest(BaseModel):
    """创建订单请求模型"""
    symbol: str = Field(..., description="交易对符号")
    side: OrderSide = Field(..., description="订单方向")
    type: OrderType = Field(..., description="订单类型")
    quantity: Decimal = Field(..., gt=0, description="数量")
    price: Optional[Decimal] = Field(None, gt=0, description="价格")
    stop_price: Optional[Decimal] = Field(None, gt=0, description="止损价格")
    time_in_force: TimeInForce = Field(default=TimeInForce.GTC, description="时效性")
    client_order_id: Optional[str] = Field(None, description="客户端订单ID")
    
    @validator('price')
    def validate_price_for_limit_orders(cls, v, values):
        if values.get('type') == OrderType.LIMIT and not v:
            raise ValueError('限价单必须指定价格')
        return v
    
    @validator('stop_price')
    def validate_stop_price(cls, v, values):
        if values.get('type') in [OrderType.STOP, OrderType.STOP_LIMIT] and not v:
            raise ValueError('止损单必须指定止损价格')
        return v


class OrderInfo(BaseModel):
    """订单信息模型"""
    order_id: str = Field(..., description="订单ID")
    client_order_id: Optional[str] = Field(None, description="客户端订单ID")
    symbol: str = Field(..., description="交易对符号")
    side: OrderSide = Field(..., description="订单方向")
    type: OrderType = Field(..., description="订单类型")
    status: OrderStatus = Field(..., description="订单状态")
    quantity: Decimal = Field(..., description="数量")
    price: Optional[Decimal] = Field(None, description="价格")
    stop_price: Optional[Decimal] = Field(None, description="止损价格")
    filled_quantity: Decimal = Field(..., description="已成交数量")
    remaining_quantity: Decimal = Field(..., description="剩余数量")
    average_price: Optional[Decimal] = Field(None, description="平均成交价格")
    time_in_force: TimeInForce = Field(..., description="时效性")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class CancelOrderRequest(BaseModel):
    """取消订单请求模型"""
    order_id: Optional[str] = Field(None, description="订单ID")
    client_order_id: Optional[str] = Field(None, description="客户端订单ID")
    symbol: str = Field(..., description="交易对符号")
    
    @validator('order_id')
    def validate_order_identification(cls, v, values):
        if not v and not values.get('client_order_id'):
            raise ValueError('必须提供订单ID或客户端订单ID')
        return v


class ModifyOrderRequest(BaseModel):
    """修改订单请求模型"""
    order_id: str = Field(..., description="订单ID")
    quantity: Optional[Decimal] = Field(None, gt=0, description="新数量")
    price: Optional[Decimal] = Field(None, gt=0, description="新价格")
    stop_price: Optional[Decimal] = Field(None, gt=0, description="新止损价格")


class TradeInfo(BaseModel):
    """交易信息模型"""
    trade_id: str = Field(..., description="交易ID")
    order_id: str = Field(..., description="订单ID")
    symbol: str = Field(..., description="交易对符号")
    side: OrderSide = Field(..., description="交易方向")
    quantity: Decimal = Field(..., description="交易数量")
    price: Decimal = Field(..., description="交易价格")
    commission: Decimal = Field(..., description="手续费")
    commission_asset: str = Field(..., description="手续费资产")
    timestamp: datetime = Field(..., description="交易时间")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class PositionInfo(BaseModel):
    """持仓信息模型"""
    symbol: str = Field(..., description="交易对符号")
    side: str = Field(..., description="持仓方向")
    size: Decimal = Field(..., description="持仓数量")
    entry_price: Decimal = Field(..., description="入场价格")
    market_price: Decimal = Field(..., description="市场价格")
    unrealized_pnl: Decimal = Field(..., description="未实现盈亏")
    realized_pnl: Decimal = Field(..., description="已实现盈亏")
    margin: Decimal = Field(..., description="保证金")
    leverage: Decimal = Field(..., description="杠杆")
    liquidation_price: Optional[Decimal] = Field(None, description="强平价格")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class BalanceInfo(BaseModel):
    """余额信息模型"""
    asset: str = Field(..., description="资产符号")
    free: Decimal = Field(..., description="可用余额")
    locked: Decimal = Field(..., description="冻结余额")
    total: Decimal = Field(..., description="总余额")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class MarketDataRequest(BaseModel):
    """市场数据请求模型"""
    symbol: str = Field(..., description="交易对符号")
    interval: str = Field(..., description="时间间隔")
    limit: int = Field(default=100, ge=1, le=1000, description="数据条数")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")


class KlineData(BaseModel):
    """K线数据模型"""
    symbol: str = Field(..., description="交易对符号")
    interval: str = Field(..., description="时间间隔")
    open_time: datetime = Field(..., description="开盘时间")
    close_time: datetime = Field(..., description="收盘时间")
    open_price: Decimal = Field(..., description="开盘价")
    high_price: Decimal = Field(..., description="最高价")
    low_price: Decimal = Field(..., description="最低价")
    close_price: Decimal = Field(..., description="收盘价")
    volume: Decimal = Field(..., description="成交量")
    quote_volume: Decimal = Field(..., description="成交额")
    trades_count: int = Field(..., description="成交笔数")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class OrderBookEntry(BaseModel):
    """订单簿条目模型"""
    price: Decimal = Field(..., description="价格")
    quantity: Decimal = Field(..., description="数量")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class OrderBookData(BaseModel):
    """订单簿数据模型"""
    symbol: str = Field(..., description="交易对符号")
    bids: List[OrderBookEntry] = Field(..., description="买单")
    asks: List[OrderBookEntry] = Field(..., description="卖单")
    timestamp: datetime = Field(..., description="时间戳")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TickerData(BaseModel):
    """行情数据模型"""
    symbol: str = Field(..., description="交易对符号")
    price: Decimal = Field(..., description="最新价格")
    price_change: Decimal = Field(..., description="价格变动")
    price_change_percent: Decimal = Field(..., description="价格变动百分比")
    high_price: Decimal = Field(..., description="24小时最高价")
    low_price: Decimal = Field(..., description="24小时最低价")
    volume: Decimal = Field(..., description="24小时成交量")
    quote_volume: Decimal = Field(..., description="24小时成交额")
    open_price: Decimal = Field(..., description="开盘价")
    timestamp: datetime = Field(..., description="时间戳")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class BatchOrderRequest(BaseModel):
    """批量订单请求模型"""
    orders: List[CreateOrderRequest] = Field(..., description="订单列表")
    
    @validator('orders')
    def validate_orders_count(cls, v):
        if len(v) > 100:
            raise ValueError('批量订单数量不能超过100')
        return v


class BatchOrderResponse(BaseModel):
    """批量订单响应模型"""
    success_orders: List[OrderInfo] = Field(..., description="成功订单")
    failed_orders: List[Dict[str, Any]] = Field(..., description="失败订单")
    total_count: int = Field(..., description="总订单数")
    success_count: int = Field(..., description="成功订单数")
    failed_count: int = Field(..., description="失败订单数")