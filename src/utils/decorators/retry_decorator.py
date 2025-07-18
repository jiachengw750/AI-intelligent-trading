# -*- coding: utf-8 -*-
"""
重试装饰器
"""

import asyncio
import functools
from typing import Type, Tuple, Union, Callable, Any
import random
from src.utils.helpers.logger import get_logger

logger = get_logger(__name__)


def async_retry(
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    max_delay: float = 60.0,
    jitter: bool = True
) -> Callable:
    """
    异步重试装饰器
    
    Args:
        exceptions: 需要重试的异常类型
        max_attempts: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 退避因子
        max_delay: 最大延迟时间（秒）
        jitter: 是否添加随机抖动
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        logger.error(f"{func.__name__} 失败，已达到最大重试次数 {max_attempts}: {e}")
                        raise
                        
                    # 计算下次重试的延迟时间
                    if jitter:
                        # 添加随机抖动，避免雷鸣群效应
                        actual_delay = current_delay * (0.5 + random.random())
                    else:
                        actual_delay = current_delay
                        
                    logger.warning(
                        f"{func.__name__} 失败 (尝试 {attempt + 1}/{max_attempts})，"
                        f"{actual_delay:.2f}秒后重试: {e}"
                    )
                    
                    await asyncio.sleep(actual_delay)
                    
                    # 指数退避
                    current_delay = min(current_delay * backoff, max_delay)
                    
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


def sync_retry(
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    max_delay: float = 60.0,
    jitter: bool = True
) -> Callable:
    """
    同步重试装饰器
    
    Args:
        exceptions: 需要重试的异常类型
        max_attempts: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 退避因子
        max_delay: 最大延迟时间（秒）
        jitter: 是否添加随机抖动
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        logger.error(f"{func.__name__} 失败，已达到最大重试次数 {max_attempts}: {e}")
                        raise
                        
                    # 计算下次重试的延迟时间
                    if jitter:
                        actual_delay = current_delay * (0.5 + random.random())
                    else:
                        actual_delay = current_delay
                        
                    logger.warning(
                        f"{func.__name__} 失败 (尝试 {attempt + 1}/{max_attempts})，"
                        f"{actual_delay:.2f}秒后重试: {e}"
                    )
                    
                    import time
                    time.sleep(actual_delay)
                    
                    # 指数退避
                    current_delay = min(current_delay * backoff, max_delay)
                    
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


class RetryableError(Exception):
    """可重试的错误"""
    pass


class NonRetryableError(Exception):
    """不可重试的错误"""
    pass