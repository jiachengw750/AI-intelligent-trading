# -*- coding: utf-8 -*-
"""
订单执行器
"""

import asyncio
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import time
import json
from src.utils.helpers.logger import trading_logger
from src.utils.helpers.async_utils import async_utils
from src.utils.decorators import async_retry
from src.core.exceptions.trading_exceptions import OrderException, OrderExecutionException, InsufficientFundsException
from src.risk import risk_manager, create_position_sizer
from config import trading_config


class OrderType(Enum):
    """订单类型"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"
    ICEBERG = "iceberg"
    TWAP = "twap"
    VWAP = "vwap"


class OrderSide(Enum):
    """订单方向"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL_FILLED = "partial_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class TimeInForce(Enum):
    """订单有效期"""
    GTC = "gtc"  # Good Till Cancelled
    IOC = "ioc"  # Immediate Or Cancel
    FOK = "fok"  # Fill Or Kill
    DAY = "day"  # Day Order


@dataclass
class Order:
    """订单"""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: TimeInForce = TimeInForce.GTC
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    average_price: float = 0.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    exchange: str = "simulation"
    
    # 高级订单参数
    iceberg_qty: Optional[float] = None  # 冰山订单显示数量
    twap_duration: Optional[int] = None  # TWAP执行时间（秒）
    trailing_amount: Optional[float] = None  # 跟踪止损金额
    trailing_percent: Optional[float] = None  # 跟踪止损百分比
    
    # 执行信息
    commission: float = 0.0
    commission_asset: str = ""
    error_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "quantity": self.quantity,
            "price": self.price,
            "stop_price": self.stop_price,
            "time_in_force": self.time_in_force.value,
            "status": self.status.value,
            "filled_quantity": self.filled_quantity,
            "average_price": self.average_price,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "exchange": self.exchange,
            "iceberg_qty": self.iceberg_qty,
            "twap_duration": self.twap_duration,
            "trailing_amount": self.trailing_amount,
            "trailing_percent": self.trailing_percent,
            "commission": self.commission,
            "commission_asset": self.commission_asset,
            "error_message": self.error_message
        }
        
    @property
    def is_buy(self) -> bool:
        """是否为买单"""
        return self.side == OrderSide.BUY
        
    @property
    def is_sell(self) -> bool:
        """是否为卖单"""
        return self.side == OrderSide.SELL
        
    @property
    def is_filled(self) -> bool:
        """是否已完全成交"""
        return self.status == OrderStatus.FILLED
        
    @property
    def is_active(self) -> bool:
        """是否为活跃订单"""
        return self.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIAL_FILLED]
        
    @property
    def remaining_quantity(self) -> float:
        """剩余数量"""
        return max(0, self.quantity - self.filled_quantity)


@dataclass
class ExecutionReport:
    """执行报告"""
    execution_id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    timestamp: float
    commission: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "execution_id": self.execution_id,
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": self.quantity,
            "price": self.price,
            "timestamp": self.timestamp,
            "commission": self.commission
        }


class OrderExecutor:
    """订单执行器"""
    
    def __init__(self):
        self.orders: Dict[str, Order] = {}
        self.executions: List[ExecutionReport] = []
        self.is_running = False
        
        # 执行统计
        self.total_orders = 0
        self.filled_orders = 0
        self.cancelled_orders = 0
        self.rejected_orders = 0
        
        # 配置参数
        self.default_commission_rate = 0.001  # 0.1%
        self.max_order_age_seconds = 86400  # 24小时
        self.execution_delay_ms = 100  # 模拟执行延迟
        
        # 回调函数
        self.order_callbacks: List[callable] = []
        self.execution_callbacks: List[callable] = []
        
        # 仓位规模计算器
        self.position_sizer = create_position_sizer(risk_manager)
        
    def add_order_callback(self, callback: callable):
        """添加订单回调"""
        self.order_callbacks.append(callback)
        trading_logger.info(f"添加订单回调: {callback.__name__}")
        
    def add_execution_callback(self, callback: callable):
        """添加执行回调"""
        self.execution_callbacks.append(callback)
        trading_logger.info(f"添加执行回调: {callback.__name__}")
        
    async def _emit_order_update(self, order: Order):
        """发出订单更新事件"""
        for callback in self.order_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(order)
                else:
                    callback(order)
            except Exception as e:
                trading_logger.error(f"订单回调执行失败: {e}")
                
    async def _emit_execution_report(self, execution: ExecutionReport):
        """发出执行报告事件"""
        for callback in self.execution_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(execution)
                else:
                    callback(execution)
            except Exception as e:
                trading_logger.error(f"执行回调执行失败: {e}")
                
    async def submit_order(self, order_params: Dict[str, Any], 
                          portfolio: Dict[str, Any] = None) -> str:
        """提交订单"""
        try:
            # 验证订单参数
            validation_result = await self._validate_order_params(order_params, portfolio)
            if not validation_result[0]:
                raise OrderException(validation_result[1])
                
            # 创建订单
            order = self._create_order(order_params)
            
            # 风险检查
            if portfolio:
                risk_check = await self._perform_risk_check(order, portfolio)
                if not risk_check[0]:
                    order.status = OrderStatus.REJECTED
                    order.error_message = risk_check[1]
                    await self._emit_order_update(order)
                    raise OrderException(f"风险检查失败: {risk_check[1]}")
                    
            # 提交到交易所
            submission_result = await self._submit_to_exchange(order)
            if not submission_result[0]:
                order.status = OrderStatus.REJECTED
                order.error_message = submission_result[1]
                await self._emit_order_update(order)
                raise OrderExecutionException(f"订单提交失败: {submission_result[1]}")
                
            # 保存订单
            self.orders[order.order_id] = order
            self.total_orders += 1
            
            # 发出订单更新事件
            await self._emit_order_update(order)
            
            trading_logger.info(f"订单提交成功: {order.order_id} {order.symbol} {order.side.value} {order.quantity}")
            
            return order.order_id
            
        except Exception as e:
            trading_logger.error(f"提交订单失败: {e}")
            raise
            
    async def _validate_order_params(self, order_params: Dict[str, Any],
                                   portfolio: Dict[str, Any] = None) -> Tuple[bool, str]:
        """验证订单参数"""
        try:
            # 必需参数检查
            required_params = ["symbol", "side", "order_type", "quantity"]
            for param in required_params:
                if param not in order_params:
                    return False, f"缺少必需参数: {param}"
                    
            # 数量检查
            quantity = order_params.get("quantity", 0)
            if quantity <= 0:
                return False, "订单数量必须大于0"
                
            # 价格检查
            order_type = order_params.get("order_type")
            if order_type in ["limit", "stop_limit"]:
                price = order_params.get("price", 0)
                if price <= 0:
                    return False, f"{order_type}订单必须指定有效价格"
                    
            # 止损价格检查
            if order_type in ["stop", "stop_limit", "trailing_stop"]:
                stop_price = order_params.get("stop_price", 0)
                if stop_price <= 0:
                    return False, f"{order_type}订单必须指定有效止损价格"
                    
            # 资金检查
            if portfolio:
                funds_check = await self._check_sufficient_funds(order_params, portfolio)
                if not funds_check[0]:
                    return False, funds_check[1]
                    
            return True, "订单参数验证通过"
            
        except Exception as e:
            trading_logger.error(f"验证订单参数失败: {e}")
            return False, f"验证失败: {str(e)}"
            
    async def _check_sufficient_funds(self, order_params: Dict[str, Any],
                                    portfolio: Dict[str, Any]) -> Tuple[bool, str]:
        """检查资金充足性"""
        try:
            side = order_params.get("side")
            symbol = order_params.get("symbol")
            quantity = order_params.get("quantity", 0)
            price = order_params.get("price", 0)
            
            # 获取当前市价（如果没有指定价格）
            if price <= 0:
                market_price = await self._get_market_price(symbol)
                if market_price <= 0:
                    return False, "无法获取市场价格"
                price = market_price
                
            if side == "buy":
                # 买入需要检查基础货币余额
                base_asset = self._get_base_asset(symbol)
                required_amount = quantity * price
                
                available_balance = portfolio.get("balances", {}).get(base_asset, 0)
                
                if available_balance < required_amount:
                    return False, f"资金不足: 需要 {required_amount:.4f} {base_asset}, 可用 {available_balance:.4f}"
                    
            elif side == "sell":
                # 卖出需要检查交易货币余额
                quote_asset = self._get_quote_asset(symbol)
                
                available_balance = portfolio.get("balances", {}).get(quote_asset, 0)
                
                if available_balance < quantity:
                    return False, f"持仓不足: 需要 {quantity:.4f} {quote_asset}, 可用 {available_balance:.4f}"
                    
            return True, "资金检查通过"
            
        except Exception as e:
            trading_logger.error(f"检查资金充足性失败: {e}")
            return False, f"资金检查失败: {str(e)}"
            
    def _get_base_asset(self, symbol: str) -> str:
        """获取基础货币"""
        # 简化实现，实际应该根据交易所规则解析
        if "/" in symbol:
            return symbol.split("/")[1]
        return "USDT"
        
    def _get_quote_asset(self, symbol: str) -> str:
        """获取交易货币"""
        # 简化实现，实际应该根据交易所规则解析
        if "/" in symbol:
            return symbol.split("/")[0]
        return symbol
        
    async def _get_market_price(self, symbol: str) -> float:
        """获取市场价格"""
        try:
            # 从数据存储获取最新价格
            from src.data import storage_manager
            
            query = {
                "symbol": symbol,
                "data_type": "ticker",
                "limit": 1
            }
            
            data = await storage_manager.retrieve_data(query)
            
            if data:
                latest_data = data[0]
                if "data" in latest_data and "price" in latest_data["data"]:
                    return float(latest_data["data"]["price"])
                    
            return 0.0
            
        except Exception as e:
            trading_logger.error(f"获取市场价格失败: {e}")
            return 0.0
            
    def _create_order(self, order_params: Dict[str, Any]) -> Order:
        """创建订单对象"""
        try:
            order_id = str(uuid.uuid4())
            
            # 解析订单类型和方向
            order_type = OrderType(order_params["order_type"])
            side = OrderSide(order_params["side"])
            time_in_force = TimeInForce(order_params.get("time_in_force", "gtc"))
            
            order = Order(
                order_id=order_id,
                symbol=order_params["symbol"],
                side=side,
                order_type=order_type,
                quantity=float(order_params["quantity"]),
                price=float(order_params.get("price", 0)) if order_params.get("price") else None,
                stop_price=float(order_params.get("stop_price", 0)) if order_params.get("stop_price") else None,
                time_in_force=time_in_force,
                iceberg_qty=float(order_params.get("iceberg_qty", 0)) if order_params.get("iceberg_qty") else None,
                twap_duration=int(order_params.get("twap_duration", 0)) if order_params.get("twap_duration") else None,
                trailing_amount=float(order_params.get("trailing_amount", 0)) if order_params.get("trailing_amount") else None,
                trailing_percent=float(order_params.get("trailing_percent", 0)) if order_params.get("trailing_percent") else None
            )
            
            return order
            
        except Exception as e:
            trading_logger.error(f"创建订单对象失败: {e}")
            raise OrderException(f"创建订单失败: {str(e)}")
            
    async def _perform_risk_check(self, order: Order, portfolio: Dict[str, Any]) -> Tuple[bool, str]:
        """执行风险检查"""
        try:
            # 使用风险管理器验证交易
            trade_info = {
                "symbol": order.symbol,
                "side": order.side.value,
                "amount": order.quantity,
                "price": order.price or 0
            }
            
            risk_check_result = await risk_manager.validate_trade(trade_info, portfolio)
            
            return risk_check_result
            
        except Exception as e:
            trading_logger.error(f"风险检查失败: {e}")
            return False, f"风险检查异常: {str(e)}"
            
    @async_retry(
        exceptions=(ConnectionError, TimeoutError, OrderExecutionException),
        max_attempts=3,
        delay=1.0,
        backoff=2.0,
        jitter=True
    )
    async def _submit_to_exchange(self, order: Order) -> Tuple[bool, str]:
        """提交订单到交易所（带重试）"""
        try:
            # 模拟提交延迟
            await asyncio.sleep(self.execution_delay_ms / 1000.0)
            
            # 根据订单类型处理
            if order.order_type == OrderType.MARKET:
                return await self._submit_market_order(order)
            elif order.order_type == OrderType.LIMIT:
                return await self._submit_limit_order(order)
            elif order.order_type == OrderType.STOP:
                return await self._submit_stop_order(order)
            elif order.order_type == OrderType.STOP_LIMIT:
                return await self._submit_stop_limit_order(order)
            elif order.order_type == OrderType.TRAILING_STOP:
                return await self._submit_trailing_stop_order(order)
            elif order.order_type == OrderType.ICEBERG:
                return await self._submit_iceberg_order(order)
            elif order.order_type == OrderType.TWAP:
                return await self._submit_twap_order(order)
            elif order.order_type == OrderType.VWAP:
                return await self._submit_vwap_order(order)
            else:
                return False, f"不支持的订单类型: {order.order_type.value}"
                
        except Exception as e:
            trading_logger.error(f"提交订单到交易所失败: {e}")
            return False, f"提交失败: {str(e)}"
            
    async def _submit_market_order(self, order: Order) -> Tuple[bool, str]:
        """提交市价单"""
        try:
            # 获取市场价格
            market_price = await self._get_market_price(order.symbol)
            if market_price <= 0:
                return False, "无法获取市场价格"
                
            # 市价单立即执行
            order.status = OrderStatus.SUBMITTED
            order.updated_at = time.time()
            
            # 模拟执行
            await self._execute_order(order, market_price, order.quantity)
            
            return True, "市价单提交成功"
            
        except Exception as e:
            trading_logger.error(f"提交市价单失败: {e}")
            return False, f"市价单提交失败: {str(e)}"
            
    async def _submit_limit_order(self, order: Order) -> Tuple[bool, str]:
        """提交限价单"""
        try:
            order.status = OrderStatus.SUBMITTED
            order.updated_at = time.time()
            
            # 启动限价单监控任务
            asyncio.create_task(self._monitor_limit_order(order))
            
            return True, "限价单提交成功"
            
        except Exception as e:
            trading_logger.error(f"提交限价单失败: {e}")
            return False, f"限价单提交失败: {str(e)}"
            
    async def _submit_stop_order(self, order: Order) -> Tuple[bool, str]:
        """提交止损单"""
        try:
            order.status = OrderStatus.SUBMITTED
            order.updated_at = time.time()
            
            # 启动止损单监控任务
            asyncio.create_task(self._monitor_stop_order(order))
            
            return True, "止损单提交成功"
            
        except Exception as e:
            trading_logger.error(f"提交止损单失败: {e}")
            return False, f"止损单提交失败: {str(e)}"
            
    async def _submit_stop_limit_order(self, order: Order) -> Tuple[bool, str]:
        """提交止损限价单"""
        try:
            order.status = OrderStatus.SUBMITTED
            order.updated_at = time.time()
            
            # 启动止损限价单监控任务
            asyncio.create_task(self._monitor_stop_limit_order(order))
            
            return True, "止损限价单提交成功"
            
        except Exception as e:
            trading_logger.error(f"提交止损限价单失败: {e}")
            return False, f"止损限价单提交失败: {str(e)}"
            
    async def _submit_trailing_stop_order(self, order: Order) -> Tuple[bool, str]:
        """提交跟踪止损单"""
        try:
            order.status = OrderStatus.SUBMITTED
            order.updated_at = time.time()
            
            # 启动跟踪止损单监控任务
            asyncio.create_task(self._monitor_trailing_stop_order(order))
            
            return True, "跟踪止损单提交成功"
            
        except Exception as e:
            trading_logger.error(f"提交跟踪止损单失败: {e}")
            return False, f"跟踪止损单提交失败: {str(e)}"
            
    async def _submit_iceberg_order(self, order: Order) -> Tuple[bool, str]:
        """提交冰山订单"""
        try:
            order.status = OrderStatus.SUBMITTED
            order.updated_at = time.time()
            
            # 启动冰山订单执行任务
            asyncio.create_task(self._execute_iceberg_order(order))
            
            return True, "冰山订单提交成功"
            
        except Exception as e:
            trading_logger.error(f"提交冰山订单失败: {e}")
            return False, f"冰山订单提交失败: {str(e)}"
            
    async def _submit_twap_order(self, order: Order) -> Tuple[bool, str]:
        """提交TWAP订单"""
        try:
            order.status = OrderStatus.SUBMITTED
            order.updated_at = time.time()
            
            # 启动TWAP执行任务
            asyncio.create_task(self._execute_twap_order(order))
            
            return True, "TWAP订单提交成功"
            
        except Exception as e:
            trading_logger.error(f"提交TWAP订单失败: {e}")
            return False, f"TWAP订单提交失败: {str(e)}"
            
    async def _submit_vwap_order(self, order: Order) -> Tuple[bool, str]:
        """提交VWAP订单"""
        try:
            order.status = OrderStatus.SUBMITTED
            order.updated_at = time.time()
            
            # 启动VWAP执行任务
            asyncio.create_task(self._execute_vwap_order(order))
            
            return True, "VWAP订单提交成功"
            
        except Exception as e:
            trading_logger.error(f"提交VWAP订单失败: {e}")
            return False, f"VWAP订单提交失败: {str(e)}"
            
    async def _execute_order(self, order: Order, execution_price: float, execution_quantity: float):
        """执行订单"""
        try:
            # 创建执行报告
            execution = ExecutionReport(
                execution_id=str(uuid.uuid4()),
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=execution_quantity,
                price=execution_price,
                timestamp=time.time(),
                commission=execution_quantity * execution_price * self.default_commission_rate
            )
            
            # 更新订单状态
            order.filled_quantity += execution_quantity
            order.average_price = ((order.average_price * (order.filled_quantity - execution_quantity)) + 
                                 (execution_price * execution_quantity)) / order.filled_quantity
            order.commission += execution.commission
            order.updated_at = time.time()
            
            if order.filled_quantity >= order.quantity:
                order.status = OrderStatus.FILLED
                self.filled_orders += 1
            else:
                order.status = OrderStatus.PARTIAL_FILLED
                
            # 保存执行记录
            self.executions.append(execution)
            
            # 发出事件
            await self._emit_execution_report(execution)
            await self._emit_order_update(order)
            
            trading_logger.info(f"订单执行: {order.order_id} {execution_quantity}@{execution_price}")
            
        except Exception as e:
            trading_logger.error(f"执行订单失败: {e}")
            
    async def _monitor_limit_order(self, order: Order):
        """监控限价单"""
        try:
            while order.is_active and order.order_id in self.orders:
                current_price = await self._get_market_price(order.symbol)
                
                if current_price > 0:
                    # 检查是否可以执行
                    can_execute = False
                    
                    if order.is_buy and current_price <= order.price:
                        can_execute = True
                    elif order.is_sell and current_price >= order.price:
                        can_execute = True
                        
                    if can_execute:
                        execution_price = order.price
                        execution_quantity = order.remaining_quantity
                        
                        await self._execute_order(order, execution_price, execution_quantity)
                        break
                        
                # 检查订单是否过期
                if time.time() - order.created_at > self.max_order_age_seconds:
                    await self.cancel_order(order.order_id, "订单过期")
                    break
                    
                await asyncio.sleep(1)  # 1秒检查一次
                
        except Exception as e:
            trading_logger.error(f"监控限价单失败: {e}")
            
    async def _monitor_stop_order(self, order: Order):
        """监控止损单"""
        try:
            while order.is_active and order.order_id in self.orders:
                current_price = await self._get_market_price(order.symbol)
                
                if current_price > 0 and order.stop_price:
                    # 检查是否触发止损
                    triggered = False
                    
                    if order.is_buy and current_price >= order.stop_price:
                        triggered = True
                    elif order.is_sell and current_price <= order.stop_price:
                        triggered = True
                        
                    if triggered:
                        # 触发后转为市价单执行
                        execution_price = current_price
                        execution_quantity = order.remaining_quantity
                        
                        await self._execute_order(order, execution_price, execution_quantity)
                        break
                        
                # 检查订单是否过期
                if time.time() - order.created_at > self.max_order_age_seconds:
                    await self.cancel_order(order.order_id, "订单过期")
                    break
                    
                await asyncio.sleep(1)
                
        except Exception as e:
            trading_logger.error(f"监控止损单失败: {e}")
            
    async def _monitor_stop_limit_order(self, order: Order):
        """监控止损限价单"""
        try:
            stop_triggered = False
            
            while order.is_active and order.order_id in self.orders:
                current_price = await self._get_market_price(order.symbol)
                
                if current_price > 0 and order.stop_price:
                    if not stop_triggered:
                        # 检查是否触发止损
                        if order.is_buy and current_price >= order.stop_price:
                            stop_triggered = True
                        elif order.is_sell and current_price <= order.stop_price:
                            stop_triggered = True
                    else:
                        # 止损已触发，检查限价执行条件
                        if order.is_buy and current_price <= order.price:
                            execution_price = order.price
                            execution_quantity = order.remaining_quantity
                            await self._execute_order(order, execution_price, execution_quantity)
                            break
                        elif order.is_sell and current_price >= order.price:
                            execution_price = order.price
                            execution_quantity = order.remaining_quantity
                            await self._execute_order(order, execution_price, execution_quantity)
                            break
                            
                # 检查订单是否过期
                if time.time() - order.created_at > self.max_order_age_seconds:
                    await self.cancel_order(order.order_id, "订单过期")
                    break
                    
                await asyncio.sleep(1)
                
        except Exception as e:
            trading_logger.error(f"监控止损限价单失败: {e}")
            
    async def _monitor_trailing_stop_order(self, order: Order):
        """监控跟踪止损单"""
        try:
            best_price = await self._get_market_price(order.symbol)
            current_stop_price = order.stop_price
            
            while order.is_active and order.order_id in self.orders:
                current_price = await self._get_market_price(order.symbol)
                
                if current_price > 0:
                    # 更新最佳价格和止损价格
                    if order.is_buy:
                        if current_price < best_price:
                            best_price = current_price
                            if order.trailing_amount:
                                current_stop_price = best_price + order.trailing_amount
                            elif order.trailing_percent:
                                current_stop_price = best_price * (1 + order.trailing_percent)
                                
                        # 检查是否触发止损
                        if current_price >= current_stop_price:
                            await self._execute_order(order, current_price, order.remaining_quantity)
                            break
                    else:  # sell
                        if current_price > best_price:
                            best_price = current_price
                            if order.trailing_amount:
                                current_stop_price = best_price - order.trailing_amount
                            elif order.trailing_percent:
                                current_stop_price = best_price * (1 - order.trailing_percent)
                                
                        # 检查是否触发止损
                        if current_price <= current_stop_price:
                            await self._execute_order(order, current_price, order.remaining_quantity)
                            break
                            
                # 检查订单是否过期
                if time.time() - order.created_at > self.max_order_age_seconds:
                    await self.cancel_order(order.order_id, "订单过期")
                    break
                    
                await asyncio.sleep(1)
                
        except Exception as e:
            trading_logger.error(f"监控跟踪止损单失败: {e}")
            
    async def _execute_iceberg_order(self, order: Order):
        """执行冰山订单"""
        try:
            if not order.iceberg_qty or order.iceberg_qty <= 0:
                order.iceberg_qty = order.quantity * 0.1  # 默认10%显示
                
            remaining_qty = order.quantity
            
            while remaining_qty > 0 and order.is_active:
                slice_qty = min(order.iceberg_qty, remaining_qty)
                
                # 创建子订单
                slice_executed = False
                timeout = 60  # 60秒超时
                start_time = time.time()
                
                while not slice_executed and (time.time() - start_time) < timeout:
                    current_price = await self._get_market_price(order.symbol)
                    
                    if current_price > 0:
                        # 检查是否可以执行当前切片
                        if ((order.is_buy and current_price <= order.price) or 
                            (order.is_sell and current_price >= order.price)):
                            
                            execution_price = order.price
                            await self._execute_order(order, execution_price, slice_qty)
                            remaining_qty -= slice_qty
                            slice_executed = True
                            
                    if not slice_executed:
                        await asyncio.sleep(2)  # 等待2秒再检查
                        
                if not slice_executed:
                    # 切片超时，取消整个订单
                    await self.cancel_order(order.order_id, "冰山订单执行超时")
                    break
                    
                # 如果还有剩余数量，等待一段时间再执行下一个切片
                if remaining_qty > 0:
                    await asyncio.sleep(5)
                    
        except Exception as e:
            trading_logger.error(f"执行冰山订单失败: {e}")
            
    async def _execute_twap_order(self, order: Order):
        """执行TWAP订单"""
        try:
            if not order.twap_duration or order.twap_duration <= 0:
                order.twap_duration = 3600  # 默认1小时
                
            # 计算执行参数
            total_duration = order.twap_duration
            slice_interval = max(60, total_duration // 20)  # 最少1分钟间隔，最多20个切片
            num_slices = total_duration // slice_interval
            slice_qty = order.quantity / num_slices
            
            executed_slices = 0
            start_time = time.time()
            
            while executed_slices < num_slices and order.is_active:
                current_time = time.time()
                
                # 检查是否到了执行时间
                expected_time = start_time + (executed_slices * slice_interval)
                if current_time >= expected_time:
                    current_price = await self._get_market_price(order.symbol)
                    
                    if current_price > 0:
                        # TWAP以市价执行
                        await self._execute_order(order, current_price, slice_qty)
                        executed_slices += 1
                        
                await asyncio.sleep(10)  # 10秒检查一次
                
        except Exception as e:
            trading_logger.error(f"执行TWAP订单失败: {e}")
            
    async def _execute_vwap_order(self, order: Order):
        """执行VWAP订单"""
        try:
            # VWAP需要获取历史成交量数据
            volume_profile = await self._get_volume_profile(order.symbol)
            
            if not volume_profile:
                # 如果无法获取成交量数据，退化为TWAP
                await self._execute_twap_order(order)
                return
                
            # 根据成交量分布执行订单
            total_volume = sum(volume_profile.values())
            
            for time_slice, volume in volume_profile.items():
                if not order.is_active:
                    break
                    
                # 根据成交量占比计算执行数量
                volume_ratio = volume / total_volume
                slice_qty = order.quantity * volume_ratio
                
                if slice_qty > 0:
                    current_price = await self._get_market_price(order.symbol)
                    if current_price > 0:
                        await self._execute_order(order, current_price, slice_qty)
                        
                await asyncio.sleep(60)  # 1分钟间隔
                
        except Exception as e:
            trading_logger.error(f"执行VWAP订单失败: {e}")
            
    async def _get_volume_profile(self, symbol: str) -> Dict[str, float]:
        """获取成交量分布"""
        try:
            # 简化实现，返回模拟的成交量分布
            # 实际应该从历史数据中分析成交量模式
            return {
                "09:00": 0.15,
                "10:00": 0.12,
                "11:00": 0.10,
                "14:00": 0.13,
                "15:00": 0.18,
                "16:00": 0.16,
                "21:00": 0.16
            }
            
        except Exception as e:
            trading_logger.error(f"获取成交量分布失败: {e}")
            return {}
            
    async def cancel_order(self, order_id: str, reason: str = "") -> bool:
        """取消订单"""
        try:
            if order_id not in self.orders:
                trading_logger.warning(f"订单不存在: {order_id}")
                return False
                
            order = self.orders[order_id]
            
            if not order.is_active:
                trading_logger.warning(f"订单不是活跃状态: {order_id}")
                return False
                
            # 更新订单状态
            order.status = OrderStatus.CANCELLED
            order.error_message = reason
            order.updated_at = time.time()
            
            self.cancelled_orders += 1
            
            # 发出订单更新事件
            await self._emit_order_update(order)
            
            trading_logger.info(f"订单已取消: {order_id} - {reason}")
            
            return True
            
        except Exception as e:
            trading_logger.error(f"取消订单失败: {e}")
            return False
            
    def get_order(self, order_id: str) -> Optional[Order]:
        """获取订单"""
        return self.orders.get(order_id)
        
    def get_orders(self, symbol: str = None, status: OrderStatus = None) -> List[Order]:
        """获取订单列表"""
        orders = list(self.orders.values())
        
        if symbol:
            orders = [order for order in orders if order.symbol == symbol]
            
        if status:
            orders = [order for order in orders if order.status == status]
            
        return orders
        
    def get_active_orders(self, symbol: str = None) -> List[Order]:
        """获取活跃订单"""
        active_orders = [order for order in self.orders.values() if order.is_active]
        
        if symbol:
            active_orders = [order for order in active_orders if order.symbol == symbol]
            
        return active_orders
        
    def get_execution_reports(self, order_id: str = None) -> List[ExecutionReport]:
        """获取执行报告"""
        if order_id:
            return [exec_report for exec_report in self.executions if exec_report.order_id == order_id]
        return self.executions
        
    def get_execution_statistics(self) -> Dict[str, Any]:
        """获取执行统计"""
        total_executions = len(self.executions)
        total_volume = sum(exec_report.quantity for exec_report in self.executions)
        total_commission = sum(exec_report.commission for exec_report in self.executions)
        
        return {
            "total_orders": self.total_orders,
            "filled_orders": self.filled_orders,
            "cancelled_orders": self.cancelled_orders,
            "rejected_orders": self.rejected_orders,
            "fill_rate": self.filled_orders / max(1, self.total_orders),
            "cancel_rate": self.cancelled_orders / max(1, self.total_orders),
            "total_executions": total_executions,
            "total_volume": total_volume,
            "total_commission": total_commission,
            "active_orders": len(self.get_active_orders())
        }


# 全局订单执行器实例
order_executor = OrderExecutor()