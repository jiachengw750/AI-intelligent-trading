# -*- coding: utf-8 -*-
"""
优先级任务队列
"""

import asyncio
import time
import heapq
from typing import Any, Dict, List, Optional, Callable, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
from src.utils.helpers.logger import get_logger
from src.utils.cache.distributed_cache import distributed_cache

logger = get_logger(__name__)


class QueueType(Enum):
    """队列类型"""
    MEMORY = "memory"      # 内存队列
    REDIS = "redis"        # Redis队列
    HYBRID = "hybrid"      # 混合队列


@dataclass
class QueueItem:
    """队列项"""
    id: str
    data: Any
    priority: int = 0
    timestamp: float = field(default_factory=time.time)
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __lt__(self, other):
        """优先级比较"""
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.timestamp < other.timestamp


class PriorityQueue:
    """优先级队列基类"""
    
    def __init__(self, name: str, max_size: int = 10000):
        self.name = name
        self.max_size = max_size
        self.stats = defaultdict(int)
        
    async def push(self, item: QueueItem) -> bool:
        """添加项到队列"""
        raise NotImplementedError
        
    async def pop(self) -> Optional[QueueItem]:
        """从队列取出项"""
        raise NotImplementedError
        
    async def peek(self) -> Optional[QueueItem]:
        """查看队列顶部项"""
        raise NotImplementedError
        
    async def size(self) -> int:
        """获取队列大小"""
        raise NotImplementedError
        
    async def clear(self):
        """清空队列"""
        raise NotImplementedError
        
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return dict(self.stats)


class MemoryPriorityQueue(PriorityQueue):
    """内存优先级队列"""
    
    def __init__(self, name: str, max_size: int = 10000):
        super().__init__(name, max_size)
        self.queue: List[QueueItem] = []
        self.lock = asyncio.Lock()
        self.item_set: Set[str] = set()  # 用于去重
        
    async def push(self, item: QueueItem) -> bool:
        """添加项到队列"""
        async with self.lock:
            # 检查队列大小
            if len(self.queue) >= self.max_size:
                self.stats["rejected"] += 1
                return False
                
            # 检查重复
            if item.id in self.item_set:
                self.stats["duplicates"] += 1
                return False
                
            # 添加到队列
            heapq.heappush(self.queue, item)
            self.item_set.add(item.id)
            self.stats["pushed"] += 1
            
            return True
            
    async def pop(self) -> Optional[QueueItem]:
        """从队列取出项"""
        async with self.lock:
            if not self.queue:
                return None
                
            item = heapq.heappop(self.queue)
            self.item_set.discard(item.id)
            self.stats["popped"] += 1
            
            return item
            
    async def peek(self) -> Optional[QueueItem]:
        """查看队列顶部项"""
        async with self.lock:
            if not self.queue:
                return None
            return self.queue[0]
            
    async def size(self) -> int:
        """获取队列大小"""
        async with self.lock:
            return len(self.queue)
            
    async def clear(self):
        """清空队列"""
        async with self.lock:
            self.queue.clear()
            self.item_set.clear()
            self.stats["cleared"] += 1


class RedisPriorityQueue(PriorityQueue):
    """Redis优先级队列"""
    
    def __init__(self, name: str, max_size: int = 10000):
        super().__init__(name, max_size)
        self.key_prefix = f"queue:{name}"
        self.cache = distributed_cache
        
    async def push(self, item: QueueItem) -> bool:
        """添加项到队列"""
        try:
            # 检查队列大小
            size = await self.size()
            if size >= self.max_size:
                self.stats["rejected"] += 1
                return False
                
            # 使用有序集合存储
            score = self._calculate_score(item)
            
            # 序列化数据
            data = {
                "id": item.id,
                "data": item.data,
                "priority": item.priority,
                "timestamp": item.timestamp,
                "retry_count": item.retry_count,
                "metadata": item.metadata
            }
            
            # 添加到有序集合
            key = f"{self.key_prefix}:items"
            await self.cache.client.zadd(key, {item.id: score})
            
            # 存储项数据
            item_key = f"{self.key_prefix}:data:{item.id}"
            await self.cache.set(item_key, data, ttl=86400)  # 24小时过期
            
            self.stats["pushed"] += 1
            return True
            
        except Exception as e:
            logger.error(f"Redis队列推送失败: {e}")
            self.stats["errors"] += 1
            return False
            
    async def pop(self) -> Optional[QueueItem]:
        """从队列取出项"""
        try:
            # 获取最高优先级的项
            key = f"{self.key_prefix}:items"
            items = await self.cache.client.zrange(key, 0, 0)
            
            if not items:
                return None
                
            item_id = items[0]
            
            # 从有序集合中移除
            await self.cache.client.zrem(key, item_id)
            
            # 获取项数据
            item_key = f"{self.key_prefix}:data:{item_id}"
            data = await self.cache.get(item_key)
            
            if not data:
                return None
                
            # 删除项数据
            await self.cache.delete(item_key)
            
            # 重建队列项
            item = QueueItem(
                id=data["id"],
                data=data["data"],
                priority=data["priority"],
                timestamp=data["timestamp"],
                retry_count=data["retry_count"],
                metadata=data["metadata"]
            )
            
            self.stats["popped"] += 1
            return item
            
        except Exception as e:
            logger.error(f"Redis队列弹出失败: {e}")
            self.stats["errors"] += 1
            return None
            
    async def peek(self) -> Optional[QueueItem]:
        """查看队列顶部项"""
        try:
            # 获取最高优先级的项
            key = f"{self.key_prefix}:items"
            items = await self.cache.client.zrange(key, 0, 0)
            
            if not items:
                return None
                
            item_id = items[0]
            
            # 获取项数据
            item_key = f"{self.key_prefix}:data:{item_id}"
            data = await self.cache.get(item_key)
            
            if not data:
                return None
                
            # 重建队列项
            item = QueueItem(
                id=data["id"],
                data=data["data"],
                priority=data["priority"],
                timestamp=data["timestamp"],
                retry_count=data["retry_count"],
                metadata=data["metadata"]
            )
            
            return item
            
        except Exception as e:
            logger.error(f"Redis队列查看失败: {e}")
            return None
            
    async def size(self) -> int:
        """获取队列大小"""
        try:
            key = f"{self.key_prefix}:items"
            return await self.cache.client.zcard(key)
        except Exception:
            return 0
            
    async def clear(self):
        """清空队列"""
        try:
            # 删除有序集合
            key = f"{self.key_prefix}:items"
            await self.cache.client.delete(key)
            
            # 删除所有数据键
            pattern = f"{self.key_prefix}:data:*"
            await self.cache.clear_pattern(pattern)
            
            self.stats["cleared"] += 1
            
        except Exception as e:
            logger.error(f"Redis队列清空失败: {e}")
            
    def _calculate_score(self, item: QueueItem) -> float:
        """计算排序分数（越小优先级越高）"""
        # 组合优先级和时间戳
        return item.priority * 1e10 + item.timestamp


class HybridPriorityQueue(PriorityQueue):
    """混合优先级队列（内存+Redis）"""
    
    def __init__(self, name: str, max_size: int = 10000, memory_ratio: float = 0.2):
        super().__init__(name, max_size)
        self.memory_ratio = memory_ratio
        self.memory_size = int(max_size * memory_ratio)
        
        # 内存队列（热数据）
        self.memory_queue = MemoryPriorityQueue(f"{name}_memory", self.memory_size)
        
        # Redis队列（冷数据）
        self.redis_queue = RedisPriorityQueue(f"{name}_redis", max_size - self.memory_size)
        
        # 后台任务
        self.rebalance_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """启动混合队列"""
        # 启动重平衡任务
        self.rebalance_task = asyncio.create_task(self._rebalance_loop())
        
    async def stop(self):
        """停止混合队列"""
        if self.rebalance_task:
            self.rebalance_task.cancel()
            await asyncio.gather(self.rebalance_task, return_exceptions=True)
            
    async def push(self, item: QueueItem) -> bool:
        """添加项到队列"""
        # 优先添加到内存队列
        if await self.memory_queue.push(item):
            self.stats["pushed"] += 1
            return True
            
        # 内存队列满，添加到Redis
        if await self.redis_queue.push(item):
            self.stats["pushed"] += 1
            return True
            
        self.stats["rejected"] += 1
        return False
        
    async def pop(self) -> Optional[QueueItem]:
        """从队列取出项"""
        # 优先从内存队列取
        item = await self.memory_queue.pop()
        if item:
            self.stats["popped"] += 1
            # 触发重平衡
            asyncio.create_task(self._rebalance())
            return item
            
        # 内存队列空，从Redis取
        item = await self.redis_queue.pop()
        if item:
            self.stats["popped"] += 1
            return item
            
        return None
        
    async def peek(self) -> Optional[QueueItem]:
        """查看队列顶部项"""
        # 比较内存和Redis的顶部项
        memory_item = await self.memory_queue.peek()
        redis_item = await self.redis_queue.peek()
        
        if not memory_item:
            return redis_item
        if not redis_item:
            return memory_item
            
        # 返回优先级更高的项
        return memory_item if memory_item < redis_item else redis_item
        
    async def size(self) -> int:
        """获取队列大小"""
        memory_size = await self.memory_queue.size()
        redis_size = await self.redis_queue.size()
        return memory_size + redis_size
        
    async def clear(self):
        """清空队列"""
        await self.memory_queue.clear()
        await self.redis_queue.clear()
        self.stats["cleared"] += 1
        
    async def _rebalance(self):
        """重平衡内存和Redis队列"""
        try:
            # 检查内存队列是否有空间
            memory_size = await self.memory_queue.size()
            if memory_size < self.memory_size:
                # 从Redis移动项到内存
                items_to_move = self.memory_size - memory_size
                
                for _ in range(items_to_move):
                    item = await self.redis_queue.pop()
                    if not item:
                        break
                        
                    await self.memory_queue.push(item)
                    
                self.stats["rebalanced"] += items_to_move
                
        except Exception as e:
            logger.error(f"队列重平衡失败: {e}")
            
    async def _rebalance_loop(self):
        """定期重平衡"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟检查一次
                await self._rebalance()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"重平衡循环错误: {e}")


class TaskQueue:
    """任务队列管理器"""
    
    def __init__(self):
        self.queues: Dict[str, PriorityQueue] = {}
        self.default_queue_type = QueueType.HYBRID
        
    def create_queue(
        self,
        name: str,
        queue_type: QueueType = None,
        max_size: int = 10000,
        **kwargs
    ) -> PriorityQueue:
        """创建队列"""
        queue_type = queue_type or self.default_queue_type
        
        if queue_type == QueueType.MEMORY:
            queue = MemoryPriorityQueue(name, max_size)
        elif queue_type == QueueType.REDIS:
            queue = RedisPriorityQueue(name, max_size)
        elif queue_type == QueueType.HYBRID:
            memory_ratio = kwargs.get("memory_ratio", 0.2)
            queue = HybridPriorityQueue(name, max_size, memory_ratio)
        else:
            raise ValueError(f"未知队列类型: {queue_type}")
            
        self.queues[name] = queue
        logger.info(f"创建队列: {name} (类型: {queue_type.value})")
        
        return queue
        
    def get_queue(self, name: str) -> Optional[PriorityQueue]:
        """获取队列"""
        return self.queues.get(name)
        
    async def start_all(self):
        """启动所有队列"""
        for queue in self.queues.values():
            if isinstance(queue, HybridPriorityQueue):
                await queue.start()
                
    async def stop_all(self):
        """停止所有队列"""
        for queue in self.queues.values():
            if isinstance(queue, HybridPriorityQueue):
                await queue.stop()
                
    def get_all_stats(self) -> Dict[str, Any]:
        """获取所有队列统计"""
        stats = {}
        for name, queue in self.queues.items():
            stats[name] = {
                "type": queue.__class__.__name__,
                "stats": queue.get_stats()
            }
        return stats


# 创建全局任务队列管理器
task_queue_manager = TaskQueue()