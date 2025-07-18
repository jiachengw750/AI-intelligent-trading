# -*- coding: utf-8 -*-
"""
批量处理器
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Callable, TypeVar, Generic, Union
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime, timedelta
from src.utils.helpers.logger import get_logger
from src.utils.scheduler.task_scheduler import task_scheduler, TaskPriority

logger = get_logger(__name__)

T = TypeVar('T')
R = TypeVar('R')


@dataclass
class BatchConfig:
    """批处理配置"""
    batch_size: int = 100
    batch_timeout: float = 1.0  # 秒
    max_wait_time: float = 5.0  # 最大等待时间
    enable_compression: bool = False  # 是否启用数据压缩
    enable_deduplication: bool = True  # 是否去重
    priority: TaskPriority = TaskPriority.NORMAL


@dataclass 
class BatchItem(Generic[T]):
    """批处理项"""
    id: str
    data: T
    timestamp: float = field(default_factory=time.time)
    callback: Optional[Callable[[Any], None]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BatchProcessor(Generic[T, R]):
    """批量处理器基类"""
    
    def __init__(self, name: str, config: Optional[BatchConfig] = None):
        self.name = name
        self.config = config or BatchConfig()
        
        # 批处理队列
        self.queue: List[BatchItem[T]] = []
        self.queue_lock = asyncio.Lock()
        
        # 处理状态
        self.is_running = False
        self.processor_task: Optional[asyncio.Task] = None
        
        # 统计信息
        self.stats = {
            "total_items": 0,
            "total_batches": 0,
            "failed_items": 0,
            "processing_time": 0.0,
            "last_batch_time": None
        }
        
        # 去重集合
        self.seen_items: set = set()
        
    async def start(self):
        """启动批处理器"""
        if self.is_running:
            return
            
        self.is_running = True
        self.processor_task = asyncio.create_task(self._process_loop())
        logger.info(f"批处理器 {self.name} 已启动")
        
    async def stop(self):
        """停止批处理器"""
        self.is_running = False
        
        if self.processor_task:
            # 处理剩余的项
            await self._process_batch(force=True)
            
            # 取消处理任务
            self.processor_task.cancel()
            await asyncio.gather(self.processor_task, return_exceptions=True)
            
        logger.info(f"批处理器 {self.name} 已停止")
        
    async def add_item(
        self,
        item_id: str,
        data: T,
        callback: Optional[Callable[[R], None]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """添加待处理项"""
        async with self.queue_lock:
            # 去重检查
            if self.config.enable_deduplication and item_id in self.seen_items:
                logger.debug(f"跳过重复项: {item_id}")
                return
                
            item = BatchItem(
                id=item_id,
                data=data,
                callback=callback,
                metadata=metadata or {}
            )
            
            self.queue.append(item)
            
            if self.config.enable_deduplication:
                self.seen_items.add(item_id)
                
            # 检查是否需要立即处理
            if len(self.queue) >= self.config.batch_size:
                asyncio.create_task(self._process_batch())
                
    async def add_items(self, items: List[Dict[str, Any]]):
        """批量添加项"""
        for item in items:
            await self.add_item(**item)
            
    async def _process_loop(self):
        """处理循环"""
        while self.is_running:
            try:
                # 等待批处理超时
                await asyncio.sleep(self.config.batch_timeout)
                
                # 处理批次
                await self._process_batch()
                
            except Exception as e:
                logger.error(f"批处理循环错误: {e}")
                
    async def _process_batch(self, force: bool = False):
        """处理批次"""
        async with self.queue_lock:
            # 检查是否有待处理项
            if not self.queue:
                return
                
            # 检查是否满足批处理条件
            current_time = time.time()
            oldest_item_age = current_time - self.queue[0].timestamp
            
            should_process = (
                force or
                len(self.queue) >= self.config.batch_size or
                oldest_item_age >= self.config.max_wait_time
            )
            
            if not should_process:
                return
                
            # 取出待处理项
            batch_items = self.queue[:self.config.batch_size]
            self.queue = self.queue[self.config.batch_size:]
            
        # 处理批次
        await self._execute_batch(batch_items)
        
    async def _execute_batch(self, items: List[BatchItem[T]]):
        """执行批处理"""
        if not items:
            return
            
        start_time = time.time()
        
        try:
            # 提取数据
            batch_data = [item.data for item in items]
            
            # 压缩数据（如果启用）
            if self.config.enable_compression:
                batch_data = self._compress_data(batch_data)
                
            # 执行批处理
            results = await self.process_batch(batch_data)
            
            # 处理结果
            if results:
                for item, result in zip(items, results):
                    if item.callback:
                        try:
                            if asyncio.iscoroutinefunction(item.callback):
                                await item.callback(result)
                            else:
                                item.callback(result)
                        except Exception as e:
                            logger.error(f"回调执行失败: {e}")
                            
            # 更新统计
            self.stats["total_items"] += len(items)
            self.stats["total_batches"] += 1
            self.stats["processing_time"] += time.time() - start_time
            self.stats["last_batch_time"] = datetime.now()
            
            logger.debug(f"批处理完成: {len(items)} 项, 耗时: {time.time() - start_time:.2f}s")
            
        except Exception as e:
            logger.error(f"批处理失败: {e}")
            self.stats["failed_items"] += len(items)
            
            # 执行错误回调
            for item in items:
                if item.callback:
                    try:
                        if asyncio.iscoroutinefunction(item.callback):
                            await item.callback(None)
                        else:
                            item.callback(None)
                    except Exception as callback_error:
                        logger.error(f"错误回调失败: {callback_error}")
                        
    async def process_batch(self, batch: List[T]) -> List[R]:
        """处理批次的具体实现（子类需要重写）"""
        raise NotImplementedError("子类必须实现process_batch方法")
        
    def _compress_data(self, data: List[T]) -> List[T]:
        """压缩数据（可选实现）"""
        return data
        
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "queue_size": len(self.queue),
            "avg_processing_time": (
                self.stats["processing_time"] / self.stats["total_batches"]
                if self.stats["total_batches"] > 0 else 0
            )
        }


class DatabaseBatchProcessor(BatchProcessor[Dict[str, Any], bool]):
    """数据库批量处理器"""
    
    def __init__(self, db_pool):
        super().__init__("database", BatchConfig(
            batch_size=1000,
            batch_timeout=0.5,
            max_wait_time=2.0
        ))
        self.db_pool = db_pool
        
    async def process_batch(self, batch: List[Dict[str, Any]]) -> List[bool]:
        """批量写入数据库"""
        # 按表分组
        table_groups = defaultdict(list)
        for item in batch:
            table_groups[item["table"]].append(item)
            
        results = []
        
        # 批量插入每个表
        for table, items in table_groups.items():
            try:
                # 构建批量插入SQL
                if items[0]["operation"] == "insert":
                    await self._batch_insert(table, items)
                elif items[0]["operation"] == "update":
                    await self._batch_update(table, items)
                elif items[0]["operation"] == "delete":
                    await self._batch_delete(table, items)
                    
                results.extend([True] * len(items))
                
            except Exception as e:
                logger.error(f"批量数据库操作失败 {table}: {e}")
                results.extend([False] * len(items))
                
        return results
        
    async def _batch_insert(self, table: str, items: List[Dict[str, Any]]):
        """批量插入"""
        if not items:
            return
            
        # 提取列名和值
        columns = list(items[0]["data"].keys())
        values = [
            [item["data"][col] for col in columns]
            for item in items
        ]
        
        # 执行批量插入
        async with self.db_pool.acquire() as conn:
            await conn.executemany(
                f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join(['$' + str(i+1) for i in range(len(columns))])})",
                values
            )
            
    async def _batch_update(self, table: str, items: List[Dict[str, Any]]):
        """批量更新"""
        # 简化实现，实际应该构建更复杂的UPDATE语句
        async with self.db_pool.acquire() as conn:
            for item in items:
                set_clause = ", ".join([f"{k} = ${i+2}" for i, k in enumerate(item["data"].keys())])
                values = [item["id"]] + list(item["data"].values())
                await conn.execute(
                    f"UPDATE {table} SET {set_clause} WHERE id = $1",
                    *values
                )
                
    async def _batch_delete(self, table: str, items: List[Dict[str, Any]]):
        """批量删除"""
        ids = [item["id"] for item in items]
        
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                f"DELETE FROM {table} WHERE id = ANY($1)",
                ids
            )


class MetricsBatchProcessor(BatchProcessor[Dict[str, Any], None]):
    """指标批量处理器"""
    
    def __init__(self, metrics_storage):
        super().__init__("metrics", BatchConfig(
            batch_size=500,
            batch_timeout=1.0,
            enable_compression=True
        ))
        self.metrics_storage = metrics_storage
        
    async def process_batch(self, batch: List[Dict[str, Any]]) -> List[None]:
        """批量处理指标"""
        # 按指标类型分组
        metric_groups = defaultdict(list)
        
        for metric in batch:
            metric_groups[metric["type"]].append(metric)
            
        # 聚合和存储
        for metric_type, metrics in metric_groups.items():
            aggregated = self._aggregate_metrics(metrics)
            await self.metrics_storage.store_metrics(metric_type, aggregated)
            
        return [None] * len(batch)
        
    def _aggregate_metrics(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """聚合指标"""
        # 简单的聚合示例
        aggregated = {
            "count": len(metrics),
            "timestamp": time.time(),
            "values": defaultdict(list)
        }
        
        for metric in metrics:
            for key, value in metric.get("data", {}).items():
                if isinstance(value, (int, float)):
                    aggregated["values"][key].append(value)
                    
        # 计算统计值
        for key, values in aggregated["values"].items():
            if values:
                aggregated["values"][key] = {
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "sum": sum(values)
                }
                
        return aggregated


class OrderBatchProcessor(BatchProcessor[Dict[str, Any], Dict[str, Any]]:
    """订单批量处理器"""
    
    def __init__(self, order_executor):
        super().__init__("orders", BatchConfig(
            batch_size=50,
            batch_timeout=0.1,
            max_wait_time=0.5,
            enable_deduplication=True
        ))
        self.order_executor = order_executor
        
    async def process_batch(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量执行订单"""
        # 按交易对分组
        symbol_groups = defaultdict(list)
        
        for order in batch:
            symbol_groups[order["symbol"]].append(order)
            
        results = []
        
        # 批量执行每个交易对的订单
        for symbol, orders in symbol_groups.items():
            try:
                # 优化订单执行顺序
                optimized_orders = self._optimize_order_sequence(orders)
                
                # 批量执行
                execution_results = await self.order_executor.execute_batch(
                    symbol,
                    optimized_orders
                )
                
                results.extend(execution_results)
                
            except Exception as e:
                logger.error(f"批量订单执行失败 {symbol}: {e}")
                # 返回失败结果
                results.extend([
                    {"order_id": order["id"], "status": "failed", "error": str(e)}
                    for order in orders
                ])
                
        return results
        
    def _optimize_order_sequence(self, orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """优化订单执行顺序"""
        # 按价格和类型排序，减少市场影响
        return sorted(orders, key=lambda x: (
            x.get("side", "buy"),
            -x.get("price", 0) if x.get("side") == "sell" else x.get("price", 0)
        ))


# 创建全局批处理器管理器
class BatchProcessorManager:
    """批处理器管理器"""
    
    def __init__(self):
        self.processors: Dict[str, BatchProcessor] = {}
        
    def register(self, processor: BatchProcessor):
        """注册批处理器"""
        self.processors[processor.name] = processor
        logger.info(f"注册批处理器: {processor.name}")
        
    async def start_all(self):
        """启动所有处理器"""
        for processor in self.processors.values():
            await processor.start()
            
    async def stop_all(self):
        """停止所有处理器"""
        for processor in self.processors.values():
            await processor.stop()
            
    def get_processor(self, name: str) -> Optional[BatchProcessor]:
        """获取处理器"""
        return self.processors.get(name)
        
    def get_all_stats(self) -> Dict[str, Any]:
        """获取所有处理器的统计信息"""
        return {
            name: processor.get_stats()
            for name, processor in self.processors.items()
        }


# 创建全局批处理器管理器
batch_processor_manager = BatchProcessorManager()