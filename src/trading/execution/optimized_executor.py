# -*- coding: utf-8 -*-
"""
优化的订单执行器 - 使用批处理和任务调度
"""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from src.trading.execution.order_executor import OrderExecutor, Order
from src.utils.scheduler import (
    task_scheduler, TaskPriority,
    BatchProcessor, BatchConfig, batch_processor_manager
)
from src.utils.cache import distributed_cache
from src.utils.helpers.logger import get_logger

logger = get_logger(__name__)


class OptimizedOrderBatchProcessor(BatchProcessor[Order, Dict[str, Any]]):
    """优化的订单批处理器"""
    
    def __init__(self, order_executor: OrderExecutor):
        super().__init__("optimized_orders", BatchConfig(
            batch_size=100,
            batch_timeout=0.2,
            max_wait_time=1.0,
            enable_deduplication=True,
            priority=TaskPriority.HIGH
        ))
        self.order_executor = order_executor
        
    async def process_batch(self, batch: List[Order]) -> List[Dict[str, Any]]:
        """批量处理订单"""
        # 按交易所和交易对分组
        exchange_groups = {}
        
        for order in batch:
            key = (order.exchange, order.symbol)
            if key not in exchange_groups:
                exchange_groups[key] = []
            exchange_groups[key].append(order)
            
        results = []
        
        # 并行处理每个组
        tasks = []
        for (exchange, symbol), orders in exchange_groups.items():
            task = self._process_exchange_group(exchange, symbol, orders)
            tasks.append(task)
            
        group_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 展平结果
        for group_result in group_results:
            if isinstance(group_result, Exception):
                logger.error(f"批处理组失败: {group_result}")
                continue
            results.extend(group_result)
            
        return results
        
    async def _process_exchange_group(
        self,
        exchange: str,
        symbol: str,
        orders: List[Order]
    ) -> List[Dict[str, Any]]:
        """处理单个交易所/交易对的订单组"""
        try:
            # 优化订单顺序
            optimized_orders = self._optimize_order_sequence(orders)
            
            # 批量执行
            results = []
            for order in optimized_orders:
                try:
                    result = await self.order_executor.execute_order(order)
                    results.append({
                        "order_id": order.order_id,
                        "status": "success",
                        "result": result
                    })
                except Exception as e:
                    results.append({
                        "order_id": order.order_id,
                        "status": "failed",
                        "error": str(e)
                    })
                    
            return results
            
        except Exception as e:
            logger.error(f"处理交易所组失败 {exchange}/{symbol}: {e}")
            return [
                {"order_id": order.order_id, "status": "failed", "error": str(e)}
                for order in orders
            ]
            
    def _optimize_order_sequence(self, orders: List[Order]) -> List[Order]:
        """优化订单执行顺序"""
        # 按类型、方向和价格排序
        return sorted(orders, key=lambda x: (
            0 if x.order_type == "market" else 1,  # 市价单优先
            x.side,
            -x.price if x.side == "sell" else x.price
        ))


class OptimizedOrderExecutor:
    """优化的订单执行器"""
    
    def __init__(self, base_executor: OrderExecutor):
        self.base_executor = base_executor
        self.batch_processor = OptimizedOrderBatchProcessor(base_executor)
        
        # 注册批处理器
        batch_processor_manager.register(self.batch_processor)
        
        # 缓存装饰器
        self.cache_decorator = distributed_cache.CacheDecorator(distributed_cache)
        
    async def start(self):
        """启动优化执行器"""
        await self.batch_processor.start()
        logger.info("优化订单执行器已启动")
        
    async def stop(self):
        """停止优化执行器"""
        await self.batch_processor.stop()
        logger.info("优化订单执行器已停止")
        
    async def execute_order(self, order: Order) -> Dict[str, Any]:
        """执行单个订单（使用批处理）"""
        # 添加到批处理队列
        future = asyncio.Future()
        
        await self.batch_processor.add_item(
            item_id=order.order_id,
            data=order,
            callback=lambda result: future.set_result(result)
        )
        
        # 等待结果
        return await future
        
    async def execute_orders_batch(self, orders: List[Order]) -> List[Dict[str, Any]]:
        """批量执行订单"""
        # 使用任务调度器并行执行
        task_ids = []
        
        for order in orders:
            task_id = await task_scheduler.submit_task(
                self.base_executor.execute_order,
                order,
                name=f"execute_order_{order.order_id}",
                priority=TaskPriority.HIGH if order.order_type == "market" else TaskPriority.NORMAL
            )
            task_ids.append((order.order_id, task_id))
            
        # 等待所有任务完成
        results = []
        for order_id, task_id in task_ids:
            try:
                result = await task_scheduler.wait_for_task(task_id, timeout=30.0)
                results.append({
                    "order_id": order_id,
                    "status": "success",
                    "result": result
                })
            except Exception as e:
                results.append({
                    "order_id": order_id,
                    "status": "failed",
                    "error": str(e)
                })
                
        return results
        
    @distributed_cache.CacheDecorator(distributed_cache).cached("order_book", ttl=5)
    async def get_order_book(self, exchange: str, symbol: str, depth: int = 20):
        """获取订单簿（带缓存）"""
        return await self.base_executor.get_order_book(exchange, symbol, depth)
        
    async def smart_order_routing(
        self,
        order: Order,
        exchanges: List[str]
    ) -> Dict[str, Any]:
        """智能订单路由"""
        # 获取所有交易所的价格
        price_tasks = []
        for exchange in exchanges:
            task = task_scheduler.submit_task(
                self._get_best_price,
                exchange,
                order.symbol,
                order.side,
                order.quantity,
                name=f"get_price_{exchange}",
                priority=TaskPriority.HIGH
            )
            price_tasks.append((exchange, task))
            
        # 等待价格结果
        exchange_prices = []
        for exchange, task_id in price_tasks:
            try:
                price = await task_scheduler.wait_for_task(task_id, timeout=2.0)
                exchange_prices.append((exchange, price))
            except Exception as e:
                logger.warning(f"获取{exchange}价格失败: {e}")
                
        # 选择最佳交易所
        if not exchange_prices:
            raise Exception("无法获取任何交易所的价格")
            
        # 根据订单方向选择最佳价格
        if order.side == "buy":
            best_exchange, best_price = min(exchange_prices, key=lambda x: x[1])
        else:
            best_exchange, best_price = max(exchange_prices, key=lambda x: x[1])
            
        # 在最佳交易所执行订单
        order.exchange = best_exchange
        result = await self.execute_order(order)
        
        return {
            "order": result,
            "routing": {
                "selected_exchange": best_exchange,
                "best_price": best_price,
                "all_prices": dict(exchange_prices)
            }
        }
        
    async def _get_best_price(
        self,
        exchange: str,
        symbol: str,
        side: str,
        quantity: float
    ) -> float:
        """获取最佳价格"""
        order_book = await self.get_order_book(exchange, symbol)
        
        if side == "buy":
            # 计算卖单的加权平均价格
            asks = order_book.get("asks", [])
            return self._calculate_weighted_price(asks, quantity)
        else:
            # 计算买单的加权平均价格
            bids = order_book.get("bids", [])
            return self._calculate_weighted_price(bids, quantity)
            
    def _calculate_weighted_price(
        self,
        orders: List[List[float]],
        quantity: float
    ) -> float:
        """计算加权平均价格"""
        if not orders:
            return 0.0
            
        total_cost = 0.0
        remaining_qty = quantity
        
        for price, qty in orders:
            if remaining_qty <= 0:
                break
                
            fill_qty = min(remaining_qty, qty)
            total_cost += price * fill_qty
            remaining_qty -= fill_qty
            
        if remaining_qty > 0:
            # 数量不足，使用最后的价格
            return orders[-1][0] if orders else 0.0
            
        return total_cost / quantity
        
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "batch_processor": self.batch_processor.get_stats(),
            "task_scheduler": task_scheduler.get_stats(),
            "cache_stats": distributed_cache.get_stats()
        }


# 创建优化执行器实例的工厂函数
def create_optimized_executor(base_executor: OrderExecutor) -> OptimizedOrderExecutor:
    """创建优化的订单执行器"""
    return OptimizedOrderExecutor(base_executor)