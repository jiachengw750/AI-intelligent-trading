# -*- coding: utf-8 -*-
"""
分布式缓存管理器
"""

import asyncio
import json
import pickle
import time
from typing import Any, Optional, Dict, List, Union
from datetime import timedelta
import redis.asyncio as redis
from src.utils.helpers.logger import get_logger
from src.core.exceptions.trading_exceptions import CacheException

logger = get_logger(__name__)


class CacheSerializer:
    """缓存序列化器"""
    
    @staticmethod
    def serialize(value: Any) -> bytes:
        """序列化数据"""
        try:
            # 尝试JSON序列化（更快更通用）
            return json.dumps(value).encode('utf-8')
        except (TypeError, ValueError):
            # 回退到pickle（支持更多类型）
            return pickle.dumps(value)
            
    @staticmethod
    def deserialize(data: bytes) -> Any:
        """反序列化数据"""
        try:
            # 尝试JSON反序列化
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # 回退到pickle
            return pickle.loads(data)


class DistributedCache:
    """分布式缓存管理器"""
    
    def __init__(self, redis_url: str = None, prefix: str = "trading"):
        self.redis_url = redis_url or "redis://localhost:6379"
        self.prefix = prefix
        self.client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self._is_connected = False
        
        # 缓存统计
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0
        }
        
    async def connect(self):
        """连接Redis"""
        try:
            self.client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=False,
                max_connections=50
            )
            
            # 测试连接
            await self.client.ping()
            
            # 创建发布订阅客户端
            self.pubsub = self.client.pubsub()
            
            self._is_connected = True
            logger.info("分布式缓存连接成功")
            
        except Exception as e:
            logger.error(f"连接Redis失败: {e}")
            raise CacheException(f"缓存连接失败: {e}")
            
    async def disconnect(self):
        """断开连接"""
        if self.pubsub:
            await self.pubsub.close()
            
        if self.client:
            await self.client.close()
            
        self._is_connected = False
        logger.info("分布式缓存已断开")
        
    def _make_key(self, key: str) -> str:
        """生成带前缀的键"""
        return f"{self.prefix}:{key}"
        
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if not self._is_connected:
            return None
            
        try:
            full_key = self._make_key(key)
            data = await self.client.get(full_key)
            
            if data is None:
                self.stats["misses"] += 1
                return None
                
            self.stats["hits"] += 1
            return CacheSerializer.deserialize(data)
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"获取缓存失败 {key}: {e}")
            return None
            
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        if not self._is_connected:
            return False
            
        try:
            full_key = self._make_key(key)
            data = CacheSerializer.serialize(value)
            
            if ttl:
                await self.client.setex(full_key, ttl, data)
            else:
                await self.client.set(full_key, data)
                
            self.stats["sets"] += 1
            return True
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"设置缓存失败 {key}: {e}")
            return False
            
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self._is_connected:
            return False
            
        try:
            full_key = self._make_key(key)
            result = await self.client.delete(full_key)
            
            self.stats["deletes"] += 1
            return result > 0
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"删除缓存失败 {key}: {e}")
            return False
            
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if not self._is_connected:
            return False
            
        try:
            full_key = self._make_key(key)
            return await self.client.exists(full_key) > 0
            
        except Exception as e:
            logger.error(f"检查缓存键失败 {key}: {e}")
            return False
            
    async def mget(self, keys: List[str]) -> Dict[str, Any]:
        """批量获取"""
        if not self._is_connected:
            return {}
            
        try:
            full_keys = [self._make_key(key) for key in keys]
            values = await self.client.mget(full_keys)
            
            result = {}
            for key, value in zip(keys, values):
                if value is not None:
                    result[key] = CacheSerializer.deserialize(value)
                    self.stats["hits"] += 1
                else:
                    self.stats["misses"] += 1
                    
            return result
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"批量获取缓存失败: {e}")
            return {}
            
    async def mset(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """批量设置"""
        if not self._is_connected:
            return False
            
        try:
            # 序列化数据
            full_mapping = {}
            for key, value in mapping.items():
                full_key = self._make_key(key)
                full_mapping[full_key] = CacheSerializer.serialize(value)
                
            # 批量设置
            await self.client.mset(full_mapping)
            
            # 设置过期时间
            if ttl:
                pipe = self.client.pipeline()
                for full_key in full_mapping.keys():
                    pipe.expire(full_key, ttl)
                await pipe.execute()
                
            self.stats["sets"] += len(mapping)
            return True
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"批量设置缓存失败: {e}")
            return False
            
    async def clear_pattern(self, pattern: str) -> int:
        """清除匹配模式的键"""
        if not self._is_connected:
            return 0
            
        try:
            full_pattern = self._make_key(pattern)
            cursor = 0
            deleted = 0
            
            while True:
                cursor, keys = await self.client.scan(
                    cursor, match=full_pattern, count=100
                )
                
                if keys:
                    deleted += await self.client.delete(*keys)
                    
                if cursor == 0:
                    break
                    
            self.stats["deletes"] += deleted
            return deleted
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"清除缓存模式失败 {pattern}: {e}")
            return 0
            
    async def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """原子递增"""
        if not self._is_connected:
            return None
            
        try:
            full_key = self._make_key(key)
            return await self.client.incr(full_key, amount)
            
        except Exception as e:
            logger.error(f"递增缓存失败 {key}: {e}")
            return None
            
    async def expire(self, key: str, ttl: int) -> bool:
        """设置过期时间"""
        if not self._is_connected:
            return False
            
        try:
            full_key = self._make_key(key)
            return await self.client.expire(full_key, ttl)
            
        except Exception as e:
            logger.error(f"设置过期时间失败 {key}: {e}")
            return False
            
    async def publish(self, channel: str, message: Any) -> int:
        """发布消息"""
        if not self._is_connected:
            return 0
            
        try:
            data = CacheSerializer.serialize(message)
            return await self.client.publish(channel, data)
            
        except Exception as e:
            logger.error(f"发布消息失败 {channel}: {e}")
            return 0
            
    async def subscribe(self, *channels: str):
        """订阅频道"""
        if not self.pubsub:
            raise CacheException("发布订阅未初始化")
            
        await self.pubsub.subscribe(*channels)
        
    async def get_message(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """获取订阅消息"""
        if not self.pubsub:
            return None
            
        try:
            message = await self.pubsub.get_message(timeout=timeout)
            if message and message["type"] == "message":
                message["data"] = CacheSerializer.deserialize(message["data"])
                return message
            return None
            
        except Exception as e:
            logger.error(f"获取订阅消息失败: {e}")
            return None
            
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total * 100) if total > 0 else 0
        
        return {
            **self.stats,
            "hit_rate": hit_rate,
            "total_requests": total
        }
        
    async def health_check(self) -> bool:
        """健康检查"""
        if not self._is_connected:
            return False
            
        try:
            await self.client.ping()
            return True
        except Exception:
            return False


class CacheDecorator:
    """缓存装饰器"""
    
    def __init__(self, cache: DistributedCache):
        self.cache = cache
        
    def cached(self, key_prefix: str, ttl: int = 300):
        """缓存装饰器"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # 生成缓存键
                cache_key = f"{key_prefix}:{str(args)}:{str(sorted(kwargs.items()))}"
                
                # 尝试从缓存获取
                result = await self.cache.get(cache_key)
                if result is not None:
                    return result
                    
                # 执行函数
                result = await func(*args, **kwargs)
                
                # 存入缓存
                await self.cache.set(cache_key, result, ttl)
                
                return result
            return wrapper
        return decorator
        
    def invalidate(self, pattern: str):
        """缓存失效装饰器"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # 执行函数
                result = await func(*args, **kwargs)
                
                # 清除匹配的缓存
                await self.cache.clear_pattern(pattern)
                
                return result
            return wrapper
        return decorator


# 创建全局缓存实例
distributed_cache = DistributedCache()