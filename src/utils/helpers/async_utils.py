# -*- coding: utf-8 -*-
"""
异步工具函数模块
"""

import asyncio
import functools
from typing import Any, Callable, Coroutine, Optional, TypeVar, Union
from concurrent.futures import ThreadPoolExecutor
import time
from src.utils.helpers.logger import main_logger

T = TypeVar('T')


class AsyncUtils:
    """异步工具类"""
    
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
    async def run_in_executor(self, func: Callable[..., T], *args, **kwargs) -> T:
        """在线程池中运行同步函数"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            functools.partial(func, *args, **kwargs)
        )
        
    async def gather_with_timeout(self, 
                                 *coroutines: Coroutine,
                                 timeout: Optional[float] = None) -> list:
        """并发运行协程，支持超时"""
        try:
            if timeout:
                return await asyncio.wait_for(
                    asyncio.gather(*coroutines, return_exceptions=True),
                    timeout=timeout
                )
            else:
                return await asyncio.gather(*coroutines, return_exceptions=True)
        except asyncio.TimeoutError:
            main_logger.error(f"协程执行超时: {timeout}秒")
            raise
            
    async def retry_async(self,
                         func: Callable[..., Coroutine[Any, Any, T]],
                         *args,
                         max_retries: int = 3,
                         delay: float = 1.0,
                         backoff_factor: float = 2.0,
                         **kwargs) -> T:
        """异步重试装饰器"""
        for attempt in range(max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries:
                    main_logger.error(f"重试失败，已达到最大重试次数 {max_retries}: {e}")
                    raise
                    
                wait_time = delay * (backoff_factor ** attempt)
                main_logger.warning(f"第 {attempt + 1} 次重试失败，{wait_time}秒后重试: {e}")
                await asyncio.sleep(wait_time)
                
    async def with_semaphore(self, 
                           semaphore: asyncio.Semaphore,
                           func: Callable[..., Coroutine[Any, Any, T]],
                           *args, **kwargs) -> T:
        """使用信号量限制并发"""
        async with semaphore:
            return await func(*args, **kwargs)
            
    def create_semaphore(self, limit: int) -> asyncio.Semaphore:
        """创建信号量"""
        return asyncio.Semaphore(limit)
        
    def close(self):
        """关闭线程池"""
        self.executor.shutdown(wait=True)


def async_timer(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
    """异步函数计时装饰器"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            main_logger.debug(f"{func.__name__} 执行时间: {execution_time:.4f}秒")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            main_logger.error(f"{func.__name__} 执行失败 (耗时: {execution_time:.4f}秒): {e}")
            raise
    return wrapper


def async_rate_limit(calls_per_second: float):
    """异步速率限制装饰器"""
    min_interval = 1.0 / calls_per_second
    last_called = 0.0
    
    def decorator(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            nonlocal last_called
            
            current_time = time.time()
            elapsed = current_time - last_called
            
            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)
                
            last_called = time.time()
            return await func(*args, **kwargs)
            
        return wrapper
    return decorator


async def safe_gather(*coroutines: Coroutine, return_exceptions: bool = True) -> list:
    """安全的并发执行，记录异常"""
    results = await asyncio.gather(*coroutines, return_exceptions=return_exceptions)
    
    if return_exceptions:
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                main_logger.error(f"协程 {i} 执行异常: {result}")
                
    return results


class AsyncBatch:
    """异步批处理工具"""
    
    def __init__(self, batch_size: int = 100, timeout: float = 30.0):
        self.batch_size = batch_size
        self.timeout = timeout
        self.items = []
        self.results = []
        
    async def add_item(self, item: Any):
        """添加项目到批处理"""
        self.items.append(item)
        
        if len(self.items) >= self.batch_size:
            await self.process_batch()
            
    async def process_batch(self):
        """处理当前批次"""
        if not self.items:
            return
            
        batch = self.items.copy()
        self.items.clear()
        
        try:
            # 这里可以自定义批处理逻辑
            main_logger.info(f"处理批次: {len(batch)} 个项目")
            # 实际的批处理逻辑由子类实现
            await self._process_items(batch)
        except Exception as e:
            main_logger.error(f"批处理失败: {e}")
            
    async def _process_items(self, items: list):
        """处理项目列表 - 由子类实现"""
        pass
        
    async def flush(self):
        """处理剩余项目"""
        if self.items:
            await self.process_batch()


# 全局异步工具实例
async_utils = AsyncUtils()