# -*- coding: utf-8 -*-
"""
WebSocket连接管理器
"""

import asyncio
import json
import time
from typing import Dict, Set, List, Optional, Any
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from src.utils.helpers.logger import get_logger
from src.core.exceptions.trading_exceptions import WebSocketException

logger = get_logger(__name__)


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 活跃连接
        self.active_connections: Dict[str, WebSocket] = {}
        
        # 订阅管理
        self.subscriptions: Dict[str, Set[str]] = {}  # channel -> client_ids
        self.client_subscriptions: Dict[str, Set[str]] = {}  # client_id -> channels
        
        # 消息队列
        self.message_queues: Dict[str, asyncio.Queue] = {}
        
        # 心跳管理
        self.heartbeat_tasks: Dict[str, asyncio.Task] = {}
        self.last_heartbeat: Dict[str, float] = {}
        
        # 配置
        self.heartbeat_interval = 30  # 30秒
        self.heartbeat_timeout = 60   # 60秒超时
        
    async def connect(self, websocket: WebSocket, client_id: str):
        """接受WebSocket连接"""
        await websocket.accept()
        
        # 添加连接
        self.active_connections[client_id] = websocket
        self.client_subscriptions[client_id] = set()
        self.message_queues[client_id] = asyncio.Queue()
        self.last_heartbeat[client_id] = time.time()
        
        # 启动心跳任务
        self.heartbeat_tasks[client_id] = asyncio.create_task(
            self._heartbeat_loop(client_id)
        )
        
        # 启动消息发送任务
        asyncio.create_task(self._message_sender_loop(client_id))
        
        logger.info(f"WebSocket客户端 {client_id} 已连接")
        
        # 发送欢迎消息
        await self.send_personal_message({
            "type": "connection",
            "status": "connected",
            "client_id": client_id,
            "timestamp": time.time()
        }, client_id)
        
    def disconnect(self, client_id: str):
        """断开WebSocket连接"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            
        # 取消订阅
        if client_id in self.client_subscriptions:
            for channel in self.client_subscriptions[client_id]:
                if channel in self.subscriptions:
                    self.subscriptions[channel].discard(client_id)
                    if not self.subscriptions[channel]:
                        del self.subscriptions[channel]
                        
            del self.client_subscriptions[client_id]
            
        # 清理消息队列
        if client_id in self.message_queues:
            del self.message_queues[client_id]
            
        # 取消心跳任务
        if client_id in self.heartbeat_tasks:
            self.heartbeat_tasks[client_id].cancel()
            del self.heartbeat_tasks[client_id]
            
        if client_id in self.last_heartbeat:
            del self.last_heartbeat[client_id]
            
        logger.info(f"WebSocket客户端 {client_id} 已断开")
        
    async def subscribe(self, client_id: str, channels: List[str]):
        """订阅频道"""
        if client_id not in self.active_connections:
            raise WebSocketException(f"客户端 {client_id} 未连接")
            
        for channel in channels:
            # 添加到订阅列表
            if channel not in self.subscriptions:
                self.subscriptions[channel] = set()
            self.subscriptions[channel].add(client_id)
            
            # 添加到客户端订阅列表
            self.client_subscriptions[client_id].add(channel)
            
        logger.info(f"客户端 {client_id} 订阅频道: {channels}")
        
        # 发送订阅确认
        await self.send_personal_message({
            "type": "subscription",
            "action": "subscribe",
            "channels": channels,
            "timestamp": time.time()
        }, client_id)
        
    async def unsubscribe(self, client_id: str, channels: List[str]):
        """取消订阅频道"""
        if client_id not in self.active_connections:
            raise WebSocketException(f"客户端 {client_id} 未连接")
            
        for channel in channels:
            # 从订阅列表移除
            if channel in self.subscriptions:
                self.subscriptions[channel].discard(client_id)
                if not self.subscriptions[channel]:
                    del self.subscriptions[channel]
                    
            # 从客户端订阅列表移除
            if client_id in self.client_subscriptions:
                self.client_subscriptions[client_id].discard(channel)
                
        logger.info(f"客户端 {client_id} 取消订阅频道: {channels}")
        
        # 发送取消订阅确认
        await self.send_personal_message({
            "type": "subscription",
            "action": "unsubscribe",
            "channels": channels,
            "timestamp": time.time()
        }, client_id)
        
    async def send_personal_message(self, message: Dict[str, Any], client_id: str):
        """发送个人消息"""
        if client_id in self.message_queues:
            await self.message_queues[client_id].put(message)
            
    async def broadcast(self, message: Dict[str, Any], channel: str):
        """广播消息到频道"""
        if channel in self.subscriptions:
            for client_id in self.subscriptions[channel]:
                await self.send_personal_message(message, client_id)
                
            logger.debug(f"广播消息到频道 {channel}, 客户端数: {len(self.subscriptions[channel])}")
            
    async def broadcast_all(self, message: Dict[str, Any]):
        """广播消息到所有客户端"""
        for client_id in self.active_connections:
            await self.send_personal_message(message, client_id)
            
    async def _message_sender_loop(self, client_id: str):
        """消息发送循环"""
        try:
            websocket = self.active_connections[client_id]
            queue = self.message_queues[client_id]
            
            while client_id in self.active_connections:
                # 获取消息
                message = await queue.get()
                
                # 发送消息
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"发送消息失败 {client_id}: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"消息发送循环异常 {client_id}: {e}")
        finally:
            self.disconnect(client_id)
            
    async def _heartbeat_loop(self, client_id: str):
        """心跳循环"""
        try:
            while client_id in self.active_connections:
                # 发送心跳
                await self.send_personal_message({
                    "type": "heartbeat",
                    "timestamp": time.time()
                }, client_id)
                
                # 检查心跳超时
                if time.time() - self.last_heartbeat[client_id] > self.heartbeat_timeout:
                    logger.warning(f"客户端 {client_id} 心跳超时")
                    break
                    
                await asyncio.sleep(self.heartbeat_interval)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"心跳循环异常 {client_id}: {e}")
        finally:
            self.disconnect(client_id)
            
    def update_heartbeat(self, client_id: str):
        """更新心跳时间"""
        if client_id in self.last_heartbeat:
            self.last_heartbeat[client_id] = time.time()
            
    def get_client_count(self) -> int:
        """获取客户端数量"""
        return len(self.active_connections)
        
    def get_channel_subscribers(self, channel: str) -> int:
        """获取频道订阅者数量"""
        return len(self.subscriptions.get(channel, set()))
        
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_clients": self.get_client_count(),
            "active_channels": len(self.subscriptions),
            "subscriptions": {
                channel: len(subscribers) 
                for channel, subscribers in self.subscriptions.items()
            }
        }


# 创建全局连接管理器
ws_manager = ConnectionManager()


class MarketDataBroadcaster:
    """市场数据广播器"""
    
    def __init__(self, manager: ConnectionManager):
        self.manager = manager
        self.is_running = False
        self.broadcast_tasks = {}
        
    async def start(self):
        """启动广播器"""
        self.is_running = True
        
        # 启动各种数据广播任务
        self.broadcast_tasks["ticker"] = asyncio.create_task(self._broadcast_ticker())
        self.broadcast_tasks["orderbook"] = asyncio.create_task(self._broadcast_orderbook())
        self.broadcast_tasks["trades"] = asyncio.create_task(self._broadcast_trades())
        self.broadcast_tasks["kline"] = asyncio.create_task(self._broadcast_kline())
        
        logger.info("市场数据广播器已启动")
        
    async def stop(self):
        """停止广播器"""
        self.is_running = False
        
        # 取消所有任务
        for task in self.broadcast_tasks.values():
            task.cancel()
            
        logger.info("市场数据广播器已停止")
        
    async def _broadcast_ticker(self):
        """广播行情数据"""
        while self.is_running:
            try:
                # 从数据源获取最新行情
                from src.data import storage_manager
                
                # 获取所有活跃交易对的最新价格
                tickers = await self._get_latest_tickers()
                
                for symbol, ticker_data in tickers.items():
                    channel = f"ticker:{symbol}"
                    
                    if self.manager.get_channel_subscribers(channel) > 0:
                        await self.manager.broadcast({
                            "type": "ticker",
                            "symbol": symbol,
                            "data": ticker_data,
                            "timestamp": time.time()
                        }, channel)
                        
                await asyncio.sleep(1)  # 1秒更新一次
                
            except Exception as e:
                logger.error(f"广播行情数据失败: {e}")
                await asyncio.sleep(5)
                
    async def _broadcast_orderbook(self):
        """广播订单簿数据"""
        while self.is_running:
            try:
                # 获取订单簿更新
                orderbooks = await self._get_orderbook_updates()
                
                for symbol, orderbook_data in orderbooks.items():
                    channel = f"orderbook:{symbol}"
                    
                    if self.manager.get_channel_subscribers(channel) > 0:
                        await self.manager.broadcast({
                            "type": "orderbook",
                            "symbol": symbol,
                            "data": orderbook_data,
                            "timestamp": time.time()
                        }, channel)
                        
                await asyncio.sleep(0.5)  # 0.5秒更新一次
                
            except Exception as e:
                logger.error(f"广播订单簿数据失败: {e}")
                await asyncio.sleep(5)
                
    async def _broadcast_trades(self):
        """广播成交数据"""
        while self.is_running:
            try:
                # 获取最新成交
                trades = await self._get_latest_trades()
                
                for symbol, trade_list in trades.items():
                    channel = f"trades:{symbol}"
                    
                    if self.manager.get_channel_subscribers(channel) > 0:
                        await self.manager.broadcast({
                            "type": "trades",
                            "symbol": symbol,
                            "data": trade_list,
                            "timestamp": time.time()
                        }, channel)
                        
                await asyncio.sleep(0.1)  # 0.1秒更新一次
                
            except Exception as e:
                logger.error(f"广播成交数据失败: {e}")
                await asyncio.sleep(5)
                
    async def _broadcast_kline(self):
        """广播K线数据"""
        while self.is_running:
            try:
                # 获取K线更新
                klines = await self._get_kline_updates()
                
                for key, kline_data in klines.items():
                    symbol, interval = key.split(":")
                    channel = f"kline:{symbol}:{interval}"
                    
                    if self.manager.get_channel_subscribers(channel) > 0:
                        await self.manager.broadcast({
                            "type": "kline",
                            "symbol": symbol,
                            "interval": interval,
                            "data": kline_data,
                            "timestamp": time.time()
                        }, channel)
                        
                await asyncio.sleep(1)  # 1秒更新一次
                
            except Exception as e:
                logger.error(f"广播K线数据失败: {e}")
                await asyncio.sleep(5)
                
    async def _get_latest_tickers(self) -> Dict[str, Any]:
        """获取最新行情数据"""
        # TODO: 从数据收集器获取实时数据
        return {}
        
    async def _get_orderbook_updates(self) -> Dict[str, Any]:
        """获取订单簿更新"""
        # TODO: 从数据收集器获取实时数据
        return {}
        
    async def _get_latest_trades(self) -> Dict[str, List[Any]]:
        """获取最新成交"""
        # TODO: 从数据收集器获取实时数据
        return {}
        
    async def _get_kline_updates(self) -> Dict[str, Any]:
        """获取K线更新"""
        # TODO: 从数据收集器获取实时数据
        return {}


# 创建市场数据广播器
market_broadcaster = MarketDataBroadcaster(ws_manager)