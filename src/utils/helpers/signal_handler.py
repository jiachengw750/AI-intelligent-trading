# -*- coding: utf-8 -*-
"""
信号处理器模块
"""

import signal
import sys
import asyncio
from typing import Optional, Callable
from src.utils.helpers.logger import main_logger


class SignalHandler:
    """信号处理器类"""
    
    def __init__(self, shutdown_callback: Optional[Callable] = None):
        self.shutdown_callback = shutdown_callback
        self.shutdown_event = asyncio.Event()
        
    def setup_handlers(self):
        """设置信号处理器"""
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        
        # Windows系统支持
        if hasattr(signal, 'SIGBREAK'):
            signal.signal(signal.SIGBREAK, self._handle_shutdown)
            
    def _handle_shutdown(self, signum, frame):
        """处理关闭信号"""
        main_logger.info(f"接收到信号 {signum}，开始关闭系统...")
        
        if self.shutdown_callback:
            try:
                # 如果是异步回调，需要在事件循环中运行
                if asyncio.iscoroutinefunction(self.shutdown_callback):
                    loop = asyncio.get_event_loop()
                    loop.create_task(self.shutdown_callback())
                else:
                    self.shutdown_callback()
            except Exception as e:
                main_logger.error(f"关闭回调执行错误: {e}")
                
        self.shutdown_event.set()
        
    async def wait_for_shutdown(self):
        """等待关闭信号"""
        await self.shutdown_event.wait()
        
    def is_shutdown_requested(self) -> bool:
        """检查是否收到关闭信号"""
        return self.shutdown_event.is_set()


# 全局信号处理器实例
_signal_handler: Optional[SignalHandler] = None


def setup_signal_handlers(shutdown_callback: Optional[Callable] = None):
    """设置信号处理器"""
    global _signal_handler
    _signal_handler = SignalHandler(shutdown_callback)
    _signal_handler.setup_handlers()
    return _signal_handler


def get_signal_handler() -> Optional[SignalHandler]:
    """获取信号处理器实例"""
    return _signal_handler