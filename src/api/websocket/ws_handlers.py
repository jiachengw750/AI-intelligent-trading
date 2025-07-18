# -*- coding: utf-8 -*-
"""
WebSocket消息处理器
"""

import json
import time
from typing import Dict, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from src.api.websocket.ws_manager import ws_manager
from src.trading import portfolio_manager, order_manager
from src.monitoring import trade_monitor, system_monitor
from src.utils.helpers.logger import get_logger

logger = get_logger(__name__)


async def handle_websocket_connection(websocket: WebSocket, client_id: str):
    """处理WebSocket连接"""
    try:
        # 接受连接
        await ws_manager.connect(websocket, client_id)
        
        # 消息处理循环
        while True:
            # 接收消息
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 处理消息
            await handle_websocket_message(client_id, message)
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket客户端 {client_id} 主动断开连接")
        ws_manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket连接错误 {client_id}: {e}")
        ws_manager.disconnect(client_id)


async def handle_websocket_message(client_id: str, message: Dict[str, Any]):
    """处理WebSocket消息"""
    try:
        msg_type = message.get("type")
        
        if msg_type == "ping":
            # 处理心跳
            ws_manager.update_heartbeat(client_id)
            await ws_manager.send_personal_message({
                "type": "pong",
                "timestamp": time.time()
            }, client_id)
            
        elif msg_type == "subscribe":
            # 处理订阅
            channels = message.get("channels", [])
            await ws_manager.subscribe(client_id, channels)
            
        elif msg_type == "unsubscribe":
            # 处理取消订阅
            channels = message.get("channels", [])
            await ws_manager.unsubscribe(client_id, channels)
            
        elif msg_type == "market":
            # 处理市场数据请求
            await handle_market_request(client_id, message)
            
        elif msg_type == "trading":
            # 处理交易请求
            await handle_trading_request(client_id, message)
            
        elif msg_type == "portfolio":
            # 处理投资组合请求
            await handle_portfolio_request(client_id, message)
            
        elif msg_type == "system":
            # 处理系统请求
            await handle_system_request(client_id, message)
            
        else:
            # 未知消息类型
            await ws_manager.send_personal_message({
                "type": "error",
                "message": f"未知消息类型: {msg_type}",
                "timestamp": time.time()
            }, client_id)
            
    except Exception as e:
        logger.error(f"处理WebSocket消息失败: {e}")
        await ws_manager.send_personal_message({
            "type": "error",
            "message": str(e),
            "timestamp": time.time()
        }, client_id)


async def handle_market_subscription(symbol: str, data_type: str):
    """处理市场数据订阅"""
    channel = f"{data_type}:{symbol}"
    
    # 广播市场数据更新
    await ws_manager.broadcast({
        "type": data_type,
        "symbol": symbol,
        "data": {
            # 这里应该包含实际的市场数据
            "price": 0.0,
            "volume": 0.0,
            "timestamp": time.time()
        },
        "timestamp": time.time()
    }, channel)


async def handle_trading_events(event_type: str, event_data: Dict[str, Any]):
    """处理交易事件"""
    # 广播交易事件到订阅的客户端
    channel = f"trading:{event_type}"
    
    await ws_manager.broadcast({
        "type": "trading_event",
        "event_type": event_type,
        "data": event_data,
        "timestamp": time.time()
    }, channel)


async def handle_portfolio_updates(user_id: str, update_type: str, data: Dict[str, Any]):
    """处理投资组合更新"""
    # 发送投资组合更新到特定用户
    channel = f"portfolio:{user_id}"
    
    await ws_manager.broadcast({
        "type": "portfolio_update",
        "update_type": update_type,
        "data": data,
        "timestamp": time.time()
    }, channel)


async def handle_system_alerts(alert_level: str, alert_data: Dict[str, Any]):
    """处理系统告警"""
    # 广播系统告警到管理员频道
    channel = "system:alerts"
    
    await ws_manager.broadcast({
        "type": "system_alert",
        "level": alert_level,
        "data": alert_data,
        "timestamp": time.time()
    }, channel)


async def handle_market_request(client_id: str, message: Dict[str, Any]):
    """处理市场数据请求"""
    action = message.get("action")
    
    if action == "get_ticker":
        symbol = message.get("symbol")
        # TODO: 从数据收集器获取实时数据
        await ws_manager.send_personal_message({
            "type": "market_response",
            "action": action,
            "symbol": symbol,
            "data": {
                "price": 0.0,
                "volume": 0.0,
                "change_24h": 0.0
            },
            "timestamp": time.time()
        }, client_id)
        
    elif action == "get_orderbook":
        symbol = message.get("symbol")
        depth = message.get("depth", 20)
        # TODO: 从数据收集器获取订单簿
        await ws_manager.send_personal_message({
            "type": "market_response",
            "action": action,
            "symbol": symbol,
            "data": {
                "bids": [],
                "asks": []
            },
            "timestamp": time.time()
        }, client_id)


async def handle_trading_request(client_id: str, message: Dict[str, Any]):
    """处理交易请求"""
    action = message.get("action")
    
    if action == "get_orders":
        # 获取活跃订单
        orders = order_manager.get_active_orders()
        
        await ws_manager.send_personal_message({
            "type": "trading_response",
            "action": action,
            "data": {
                "orders": [order.to_dict() for order in orders]
            },
            "timestamp": time.time()
        }, client_id)
        
    elif action == "get_order_status":
        order_id = message.get("order_id")
        order = order_manager.get_order(order_id)
        
        await ws_manager.send_personal_message({
            "type": "trading_response", 
            "action": action,
            "data": {
                "order": order.to_dict() if order else None
            },
            "timestamp": time.time()
        }, client_id)


async def handle_portfolio_request(client_id: str, message: Dict[str, Any]):
    """处理投资组合请求"""
    action = message.get("action")
    
    if action == "get_positions":
        # 获取当前持仓
        positions = portfolio_manager.get_all_positions()
        
        await ws_manager.send_personal_message({
            "type": "portfolio_response",
            "action": action,
            "data": {
                "positions": {
                    symbol: pos.to_dict() 
                    for symbol, pos in positions.items()
                }
            },
            "timestamp": time.time()
        }, client_id)
        
    elif action == "get_metrics":
        # 获取投资组合指标
        metrics = await portfolio_manager.get_portfolio_metrics()
        
        await ws_manager.send_personal_message({
            "type": "portfolio_response",
            "action": action,
            "data": metrics.to_dict(),
            "timestamp": time.time()
        }, client_id)


async def handle_system_request(client_id: str, message: Dict[str, Any]):
    """处理系统请求"""
    action = message.get("action")
    
    if action == "get_status":
        # 获取系统状态
        status = system_monitor.get_system_status()
        
        await ws_manager.send_personal_message({
            "type": "system_response",
            "action": action,
            "data": status,
            "timestamp": time.time()
        }, client_id)
        
    elif action == "get_alerts":
        # 获取活跃告警
        alerts = system_monitor.get_active_alerts()
        
        await ws_manager.send_personal_message({
            "type": "system_response",
            "action": action,
            "data": {
                "alerts": alerts
            },
            "timestamp": time.time()
        }, client_id)