# -*- coding: utf-8 -*-
"""
订单管理器
"""

import asyncio
import time
import uuid
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from src.utils.helpers.logger import trade_logger
from src.utils.helpers.async_utils import async_utils
from src.trading.exchanges.base_exchange import BaseExchange, ExchangeOrder, OrderSide, OrderType, OrderStatus
from src.core.exceptions.trading_exceptions import OrderException, ExchangeException


class OrderManagerStatus(Enum):
    """订单管理器状态"""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"


@dataclass
class OrderEvent:
    """订单事件"""
    event_type: str
    order_id: str
    symbol: str
    timestamp: float
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ManagedOrder:
    """管理的订单"""
    internal_id: str
    exchange_order: ExchangeOrder
    exchange_name: str
    created_time: float
    last_update_time: float
    retry_count: int = 0
    max_retries: int = 3
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "internal_id": self.internal_id,
            "exchange_order": {
                "order_id": self.exchange_order.order_id,
                "symbol": self.exchange_order.symbol,
                "side": self.exchange_order.side.value,
                "order_type": self.exchange_order.order_type.value,
                "amount": self.exchange_order.amount,
                "price": self.exchange_order.price,
                "status": self.exchange_order.status.value,
                "filled_amount": self.exchange_order.filled_amount,
                "avg_price": self.exchange_order.avg_price
            },
            "exchange_name": self.exchange_name,
            "created_time": self.created_time,
            "last_update_time": self.last_update_time,
            "retry_count": self.retry_count,
            "is_active": self.is_active
        }


class OrderManager:
    """订单管理器"""
    
    def __init__(self):
        # 状态管理
        self.status = OrderManagerStatus.STOPPED
        self.is_monitoring = False
        
        # 订单存储
        self.active_orders: Dict[str, ManagedOrder] = {}
        self.completed_orders: List[ManagedOrder] = []
        self.failed_orders: List[ManagedOrder] = []
        
        # 交易所连接
        self.exchanges: Dict[str, BaseExchange] = {}
        self.primary_exchange: Optional[str] = None
        
        # 事件系统
        self.event_handlers: Dict[str, List[Callable]] = {
            "order_created": [],
            "order_filled": [],
            "order_partial": [],
            "order_cancelled": [],
            "order_failed": [],
            "order_updated": []
        }
        
        # 监控配置
        self.update_interval = 1.0  # 1秒
        self.order_timeout = 300    # 5分钟超时
        
        # 统计信息
        self.total_orders = 0
        self.successful_orders = 0
        self.failed_order_count = 0
        
    def add_exchange(self, name: str, exchange: BaseExchange, 
                    is_primary: bool = False):
        """添加交易所"""
        self.exchanges[name] = exchange
        
        if is_primary or not self.primary_exchange:
            self.primary_exchange = name
            
        trade_logger.info(f"添加交易所: {name}, 主交易所: {is_primary}")
        
    def remove_exchange(self, name: str):
        """移除交易所"""
        if name in self.exchanges:
            del self.exchanges[name]
            
            if self.primary_exchange == name:
                self.primary_exchange = next(iter(self.exchanges.keys())) if self.exchanges else None
                
            trade_logger.info(f"移除交易所: {name}")
            
    def add_event_handler(self, event_type: str, handler: Callable):
        """添加事件处理器"""
        if event_type in self.event_handlers:
            self.event_handlers[event_type].append(handler)
            trade_logger.debug(f"添加事件处理器: {event_type}")
            
    def remove_event_handler(self, event_type: str, handler: Callable):
        """移除事件处理器"""
        if event_type in self.event_handlers and handler in self.event_handlers[event_type]:
            self.event_handlers[event_type].remove(handler)
            trade_logger.debug(f"移除事件处理器: {event_type}")
            
    async def _emit_event(self, event: OrderEvent):
        """发出事件"""
        handlers = self.event_handlers.get(event.event_type, [])
        
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                trade_logger.error(f"事件处理器执行失败: {e}")
                
    async def start(self):
        """启动订单管理器"""
        try:
            if self.status == OrderManagerStatus.RUNNING:
                trade_logger.warning("订单管理器已在运行")
                return
                
            # 检查交易所连接
            if not self.exchanges:
                raise OrderException("未添加任何交易所")
                
            # 测试交易所连接
            for name, exchange in self.exchanges.items():
                if not exchange.is_connected:
                    await exchange.connect()
                    
            self.status = OrderManagerStatus.RUNNING
            
            # 启动监控任务
            await self._start_monitoring()
            
            trade_logger.info("订单管理器启动成功")
            
        except Exception as e:
            trade_logger.error(f"启动订单管理器失败: {e}")
            raise OrderException(f"启动失败: {e}")
            
    async def stop(self):
        """停止订单管理器"""
        try:
            self.status = OrderManagerStatus.STOPPED
            self.is_monitoring = False
            
            # 取消所有活跃订单
            await self.cancel_all_orders()
            
            # 断开交易所连接
            for exchange in self.exchanges.values():
                await exchange.disconnect()
                
            trade_logger.info("订单管理器已停止")
            
        except Exception as e:
            trade_logger.error(f"停止订单管理器失败: {e}")
            
    async def pause(self):
        """暂停订单管理器"""
        self.status = OrderManagerStatus.PAUSED
        trade_logger.info("订单管理器已暂停")
        
    async def resume(self):
        """恢复订单管理器"""
        if self.status == OrderManagerStatus.PAUSED:
            self.status = OrderManagerStatus.RUNNING
            trade_logger.info("订单管理器已恢复")
            
    async def _start_monitoring(self):
        """启动监控任务"""
        if self.is_monitoring:
            return
            
        self.is_monitoring = True
        
        # 创建监控任务
        asyncio.create_task(self._monitor_orders())
        
        trade_logger.info("订单监控任务已启动")
        
    async def _monitor_orders(self):
        """监控订单状态"""
        while self.is_monitoring and self.status == OrderManagerStatus.RUNNING:
            try:
                await self._update_all_orders()
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                trade_logger.error(f"监控订单失败: {e}")
                await asyncio.sleep(self.update_interval)
                
    async def _update_all_orders(self):
        """更新所有活跃订单"""
        update_tasks = []
        
        for internal_id, managed_order in list(self.active_orders.items()):
            if managed_order.is_active:
                task = self._update_order(internal_id)
                update_tasks.append(task)
                
        if update_tasks:
            await asyncio.gather(*update_tasks, return_exceptions=True)
            
    async def _update_order(self, internal_id: str):
        """更新单个订单"""
        try:
            managed_order = self.active_orders.get(internal_id)
            if not managed_order:
                return
                
            exchange = self.exchanges.get(managed_order.exchange_name)
            if not exchange:
                trade_logger.error(f"交易所不存在: {managed_order.exchange_name}")
                return
                
            # 获取最新订单状态
            updated_order = await exchange.get_order(
                managed_order.exchange_order.symbol,
                managed_order.exchange_order.order_id
            )
            
            # 检查状态变化
            old_status = managed_order.exchange_order.status
            old_filled = managed_order.exchange_order.filled_amount
            
            # 更新订单信息
            managed_order.exchange_order = updated_order
            managed_order.last_update_time = time.time()
            
            # 处理状态变化
            await self._handle_order_status_change(managed_order, old_status, old_filled)
            
        except Exception as e:
            trade_logger.error(f"更新订单失败 {internal_id}: {e}")
            
            # 增加重试计数
            if internal_id in self.active_orders:
                managed_order = self.active_orders[internal_id]
                managed_order.retry_count += 1
                
                if managed_order.retry_count >= managed_order.max_retries:
                    trade_logger.error(f"订单 {internal_id} 超过最大重试次数，标记为失败")
                    await self._mark_order_failed(internal_id, f"更新失败: {e}")
                    
    async def _handle_order_status_change(self, managed_order: ManagedOrder, 
                                        old_status: OrderStatus, old_filled: float):
        """处理订单状态变化"""
        new_status = managed_order.exchange_order.status
        new_filled = managed_order.exchange_order.filled_amount
        
        # 创建事件数据
        event_data = {
            "internal_id": managed_order.internal_id,
            "order_id": managed_order.exchange_order.order_id,
            "symbol": managed_order.exchange_order.symbol,
            "old_status": old_status.value,
            "new_status": new_status.value,
            "old_filled": old_filled,
            "new_filled": new_filled
        }
        
        # 状态变化处理
        if new_status != old_status:
            
            if new_status == OrderStatus.FILLED:
                # 订单完全成交
                await self._move_to_completed(managed_order.internal_id)
                await self._emit_event(OrderEvent("order_filled", managed_order.internal_id, 
                                                managed_order.exchange_order.symbol, time.time(), event_data))
                
            elif new_status == OrderStatus.CANCELLED:
                # 订单被取消
                await self._move_to_completed(managed_order.internal_id)
                await self._emit_event(OrderEvent("order_cancelled", managed_order.internal_id,
                                                managed_order.exchange_order.symbol, time.time(), event_data))
                
            elif new_status == OrderStatus.REJECTED:
                # 订单被拒绝
                await self._mark_order_failed(managed_order.internal_id, "订单被交易所拒绝")
                
            elif new_status == OrderStatus.EXPIRED:
                # 订单过期
                await self._mark_order_failed(managed_order.internal_id, "订单过期")
                
        # 部分成交处理
        if new_filled > old_filled and new_status == OrderStatus.PARTIAL:
            await self._emit_event(OrderEvent("order_partial", managed_order.internal_id,
                                            managed_order.exchange_order.symbol, time.time(), event_data))
            
        # 发出更新事件
        await self._emit_event(OrderEvent("order_updated", managed_order.internal_id,
                                        managed_order.exchange_order.symbol, time.time(), event_data))
        
    async def _move_to_completed(self, internal_id: str):
        """将订单移动到已完成列表"""
        if internal_id in self.active_orders:
            managed_order = self.active_orders.pop(internal_id)
            managed_order.is_active = False
            self.completed_orders.append(managed_order)
            self.successful_orders += 1
            
            trade_logger.info(f"订单已完成: {internal_id}")
            
    async def _mark_order_failed(self, internal_id: str, reason: str):
        """标记订单失败"""
        if internal_id in self.active_orders:
            managed_order = self.active_orders.pop(internal_id)
            managed_order.is_active = False
            self.failed_orders.append(managed_order)
            self.failed_order_count += 1
            
            # 发出失败事件
            event_data = {"reason": reason}
            await self._emit_event(OrderEvent("order_failed", internal_id,
                                            managed_order.exchange_order.symbol, time.time(), event_data))
            
            trade_logger.error(f"订单失败: {internal_id}, 原因: {reason}")
            
    async def place_order(self, symbol: str, side: OrderSide, order_type: OrderType,
                         amount: float, price: Optional[float] = None,
                         stop_price: Optional[float] = None,
                         exchange_name: Optional[str] = None,
                         time_in_force: str = "GTC") -> str:
        """下单"""
        try:
            if self.status != OrderManagerStatus.RUNNING:
                raise OrderException("订单管理器未运行")
                
            # 选择交易所
            target_exchange_name = exchange_name or self.primary_exchange
            if not target_exchange_name or target_exchange_name not in self.exchanges:
                raise OrderException(f"交易所不可用: {target_exchange_name}")
                
            exchange = self.exchanges[target_exchange_name]
            
            # 检查交易所连接
            if not await exchange.health_check():
                raise ExchangeException(f"交易所连接异常: {target_exchange_name}")
                
            # 生成内部订单ID
            internal_id = str(uuid.uuid4())
            
            # 下单
            exchange_order = await exchange.place_order(
                symbol=symbol,
                side=side,
                order_type=order_type,
                amount=amount,
                price=price,
                stop_price=stop_price,
                time_in_force=time_in_force,
                client_order_id=internal_id
            )
            
            # 创建管理订单
            managed_order = ManagedOrder(
                internal_id=internal_id,
                exchange_order=exchange_order,
                exchange_name=target_exchange_name,
                created_time=time.time(),
                last_update_time=time.time()
            )
            
            # 添加到活跃订单
            self.active_orders[internal_id] = managed_order
            self.total_orders += 1
            
            # 发出创建事件
            event_data = {
                "exchange_name": target_exchange_name,
                "exchange_order_id": exchange_order.order_id
            }
            await self._emit_event(OrderEvent("order_created", internal_id, symbol, time.time(), event_data))
            
            trade_logger.info(f"下单成功: {symbol} {side.value} {amount} @ {price}, 内部ID: {internal_id}")
            
            return internal_id
            
        except Exception as e:
            trade_logger.error(f"下单失败: {e}")
            raise OrderException(f"下单失败: {e}")
            
    async def cancel_order(self, internal_id: str) -> bool:
        """取消订单"""
        try:
            managed_order = self.active_orders.get(internal_id)
            if not managed_order:
                trade_logger.warning(f"订单不存在或已完成: {internal_id}")
                return False
                
            exchange = self.exchanges.get(managed_order.exchange_name)
            if not exchange:
                raise OrderException(f"交易所不存在: {managed_order.exchange_name}")
                
            # 取消订单
            success = await exchange.cancel_order(
                managed_order.exchange_order.symbol,
                managed_order.exchange_order.order_id
            )
            
            if success:
                trade_logger.info(f"取消订单成功: {internal_id}")
            else:
                trade_logger.warning(f"取消订单失败: {internal_id}")
                
            return success
            
        except Exception as e:
            trade_logger.error(f"取消订单失败: {e}")
            return False
            
    async def cancel_all_orders(self, symbol: Optional[str] = None) -> int:
        """取消所有订单"""
        cancelled_count = 0
        
        orders_to_cancel = list(self.active_orders.keys())
        
        for internal_id in orders_to_cancel:
            managed_order = self.active_orders.get(internal_id)
            if managed_order and (not symbol or managed_order.exchange_order.symbol == symbol):
                success = await self.cancel_order(internal_id)
                if success:
                    cancelled_count += 1
                    
        trade_logger.info(f"批量取消订单完成: {cancelled_count}/{len(orders_to_cancel)}")
        return cancelled_count
        
    def get_order(self, internal_id: str) -> Optional[ManagedOrder]:
        """获取订单"""
        return self.active_orders.get(internal_id)
        
    def get_active_orders(self, symbol: Optional[str] = None) -> List[ManagedOrder]:
        """获取活跃订单"""
        orders = list(self.active_orders.values())
        
        if symbol:
            orders = [order for order in orders if order.exchange_order.symbol == symbol]
            
        return orders
        
    def get_completed_orders(self, limit: int = 100) -> List[ManagedOrder]:
        """获取已完成订单"""
        return self.completed_orders[-limit:]
        
    def get_failed_orders(self, limit: int = 100) -> List[ManagedOrder]:
        """获取失败订单"""
        return self.failed_orders[-limit:]
        
    def get_order_statistics(self) -> Dict[str, Any]:
        """获取订单统计"""
        success_rate = (self.successful_orders / self.total_orders * 100) if self.total_orders > 0 else 0
        
        return {
            "total_orders": self.total_orders,
            "active_orders": len(self.active_orders),
            "successful_orders": self.successful_orders,
            "failed_orders": self.failed_order_count,
            "success_rate": success_rate,
            "status": self.status.value,
            "connected_exchanges": len([e for e in self.exchanges.values() if e.is_connected])
        }
        
    def clear_history(self):
        """清除历史记录"""
        self.completed_orders.clear()
        self.failed_orders.clear()
        trade_logger.info("订单历史记录已清除")


# 创建全局订单管理器
order_manager = OrderManager()