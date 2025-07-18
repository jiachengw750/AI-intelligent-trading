# -*- coding: utf-8 -*-
"""
币安交易所接口
"""

import hashlib
import hmac
import time
from typing import Dict, Any, List, Optional
from urllib.parse import urlencode
from .base_exchange import (
    BaseExchange, OrderBook, Trade, Kline, Balance, ExchangeOrder,
    OrderSide, OrderType, OrderStatus
)
from src.utils.helpers.logger import trade_logger
from src.core.exceptions.trading_exceptions import ExchangeException, OrderException


class BinanceExchange(BaseExchange):
    """币安交易所接口"""
    
    def __init__(self, api_key: str = "", secret_key: str = "", sandbox: bool = True):
        super().__init__(api_key, secret_key, sandbox)
        
        # API端点
        if sandbox:
            self.base_url = "https://testnet.binance.vision"
        else:
            self.base_url = "https://api.binance.com"
            
        self.api_version = "/api/v3"
        
        # 费率
        self.maker_fee = 0.001  # 0.1%
        self.taker_fee = 0.001  # 0.1%
        
    def _sign_request(self, params: Dict[str, Any]) -> str:
        """签名请求"""
        try:
            if not self.secret_key:
                raise ExchangeException("未设置密钥")
                
            # 添加时间戳
            params['timestamp'] = int(time.time() * 1000)
            
            # 创建查询字符串
            query_string = urlencode(params)
            
            # 生成签名
            signature = hmac.new(
                self.secret_key.encode('utf-8'),
                query_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            return signature
            
        except Exception as e:
            trade_logger.error(f"签名请求失败: {e}")
            raise ExchangeException(f"签名失败: {e}")
            
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            'X-MBX-APIKEY': self.api_key,
            'Content-Type': 'application/json'
        }
        
    async def ping(self) -> bool:
        """测试连接"""
        try:
            url = f"{self.base_url}{self.api_version}/ping"
            await self._make_request("GET", url)
            return True
            
        except Exception as e:
            trade_logger.error(f"ping失败: {e}")
            return False
            
    async def get_server_time(self) -> int:
        """获取服务器时间"""
        try:
            url = f"{self.base_url}{self.api_version}/time"
            response = await self._make_request("GET", url)
            return response['serverTime']
            
        except Exception as e:
            trade_logger.error(f"获取服务器时间失败: {e}")
            raise ExchangeException(f"获取服务器时间失败: {e}")
            
    async def get_exchange_info(self) -> Dict[str, Any]:
        """获取交易所信息"""
        try:
            url = f"{self.base_url}{self.api_version}/exchangeInfo"
            response = await self._make_request("GET", url)
            return response
            
        except Exception as e:
            trade_logger.error(f"获取交易所信息失败: {e}")
            raise ExchangeException(f"获取交易所信息失败: {e}")
            
    async def get_symbols(self) -> List[str]:
        """获取所有交易对"""
        try:
            exchange_info = await self.get_exchange_info()
            symbols = []
            
            for symbol_info in exchange_info.get('symbols', []):
                if symbol_info.get('status') == 'TRADING':
                    symbols.append(symbol_info['symbol'])
                    
            return symbols
            
        except Exception as e:
            trade_logger.error(f"获取交易对失败: {e}")
            raise ExchangeException(f"获取交易对失败: {e}")
            
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """获取行情数据"""
        try:
            url = f"{self.base_url}{self.api_version}/ticker/24hr"
            params = {'symbol': symbol}
            response = await self._make_request("GET", url, params=params)
            return response
            
        except Exception as e:
            trade_logger.error(f"获取行情数据失败: {e}")
            raise ExchangeException(f"获取行情数据失败: {e}")
            
    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderBook:
        """获取订单簿"""
        try:
            url = f"{self.base_url}{self.api_version}/depth"
            params = {'symbol': symbol, 'limit': limit}
            response = await self._make_request("GET", url, params=params)
            
            bids = [(float(bid[0]), float(bid[1])) for bid in response['bids']]
            asks = [(float(ask[0]), float(ask[1])) for ask in response['asks']]
            
            return OrderBook(
                symbol=symbol,
                bids=bids,
                asks=asks,
                timestamp=time.time()
            )
            
        except Exception as e:
            trade_logger.error(f"获取订单簿失败: {e}")
            raise ExchangeException(f"获取订单簿失败: {e}")
            
    async def get_trades(self, symbol: str, limit: int = 50) -> List[Trade]:
        """获取最近成交记录"""
        try:
            url = f"{self.base_url}{self.api_version}/trades"
            params = {'symbol': symbol, 'limit': limit}
            response = await self._make_request("GET", url, params=params)
            
            trades = []
            for trade_data in response:
                trade = Trade(
                    symbol=symbol,
                    price=float(trade_data['price']),
                    amount=float(trade_data['qty']),
                    side=OrderSide.BUY if trade_data['isBuyerMaker'] else OrderSide.SELL,
                    timestamp=trade_data['time'] / 1000,
                    trade_id=str(trade_data['id'])
                )
                trades.append(trade)
                
            return trades
            
        except Exception as e:
            trade_logger.error(f"获取成交记录失败: {e}")
            raise ExchangeException(f"获取成交记录失败: {e}")
            
    async def get_klines(self, symbol: str, interval: str, 
                        start_time: Optional[int] = None,
                        end_time: Optional[int] = None,
                        limit: int = 500) -> List[Kline]:
        """获取K线数据"""
        try:
            url = f"{self.base_url}{self.api_version}/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            if start_time:
                params['startTime'] = start_time
            if end_time:
                params['endTime'] = end_time
                
            response = await self._make_request("GET", url, params=params)
            
            klines = []
            for kline_data in response:
                kline = Kline(
                    symbol=symbol,
                    timestamp=kline_data[0] / 1000,
                    open=float(kline_data[1]),
                    high=float(kline_data[2]),
                    low=float(kline_data[3]),
                    close=float(kline_data[4]),
                    volume=float(kline_data[5]),
                    interval=interval
                )
                klines.append(kline)
                
            return klines
            
        except Exception as e:
            trade_logger.error(f"获取K线数据失败: {e}")
            raise ExchangeException(f"获取K线数据失败: {e}")
            
    async def get_account(self) -> Dict[str, Any]:
        """获取账户信息"""
        try:
            url = f"{self.base_url}{self.api_version}/account"
            params = {}
            
            # 签名请求
            signature = self._sign_request(params)
            params['signature'] = signature
            
            headers = self._get_headers()
            response = await self._make_request("GET", url, params=params, headers=headers)
            return response
            
        except Exception as e:
            trade_logger.error(f"获取账户信息失败: {e}")
            raise ExchangeException(f"获取账户信息失败: {e}")
            
    async def get_balances(self) -> List[Balance]:
        """获取账户余额"""
        try:
            account_info = await self.get_account()
            balances = []
            
            for balance_data in account_info.get('balances', []):
                free_amount = float(balance_data['free'])
                locked_amount = float(balance_data['locked'])
                
                if free_amount > 0 or locked_amount > 0:
                    balance = Balance(
                        asset=balance_data['asset'],
                        free=free_amount,
                        locked=locked_amount
                    )
                    balances.append(balance)
                    
            return balances
            
        except Exception as e:
            trade_logger.error(f"获取账户余额失败: {e}")
            raise ExchangeException(f"获取账户余额失败: {e}")
            
    def _convert_order_side(self, side: OrderSide) -> str:
        """转换订单方向"""
        return "BUY" if side == OrderSide.BUY else "SELL"
        
    def _convert_order_type(self, order_type: OrderType) -> str:
        """转换订单类型"""
        type_mapping = {
            OrderType.MARKET: "MARKET",
            OrderType.LIMIT: "LIMIT",
            OrderType.STOP: "STOP_LOSS",
            OrderType.STOP_LIMIT: "STOP_LOSS_LIMIT"
        }
        return type_mapping.get(order_type, "LIMIT")
        
    def _convert_order_status(self, status: str) -> OrderStatus:
        """转换订单状态"""
        status_mapping = {
            "NEW": OrderStatus.OPEN,
            "PARTIALLY_FILLED": OrderStatus.PARTIAL,
            "FILLED": OrderStatus.FILLED,
            "CANCELED": OrderStatus.CANCELLED,
            "PENDING_CANCEL": OrderStatus.PENDING,
            "REJECTED": OrderStatus.REJECTED,
            "EXPIRED": OrderStatus.EXPIRED
        }
        return status_mapping.get(status, OrderStatus.PENDING)
        
    async def place_order(self, symbol: str, side: OrderSide, 
                         order_type: OrderType, amount: float,
                         price: Optional[float] = None,
                         stop_price: Optional[float] = None,
                         time_in_force: str = "GTC",
                         client_order_id: Optional[str] = None) -> ExchangeOrder:
        """下单"""
        try:
            url = f"{self.base_url}{self.api_version}/order"
            
            params = {
                'symbol': symbol,
                'side': self._convert_order_side(side),
                'type': self._convert_order_type(order_type),
                'quantity': f"{amount:.8f}".rstrip('0').rstrip('.'),
                'timeInForce': time_in_force
            }
            
            if price is not None:
                params['price'] = f"{price:.8f}".rstrip('0').rstrip('.')
                
            if stop_price is not None:
                params['stopPrice'] = f"{stop_price:.8f}".rstrip('0').rstrip('.')
                
            if client_order_id:
                params['newClientOrderId'] = client_order_id
                
            # 签名请求
            signature = self._sign_request(params)
            params['signature'] = signature
            
            headers = self._get_headers()
            response = await self._make_request("POST", url, data=params, headers=headers)
            
            # 解析响应
            order = ExchangeOrder(
                order_id=str(response['orderId']),
                symbol=response['symbol'],
                side=side,
                order_type=order_type,
                amount=float(response['origQty']),
                price=float(response['price']) if response.get('price') else None,
                status=self._convert_order_status(response['status']),
                filled_amount=float(response['executedQty']),
                avg_price=float(response['price']) if response.get('price') else 0.0,
                timestamp=response['transactTime'] / 1000
            )
            
            trade_logger.info(f"下单成功: {symbol} {side.value} {amount} @ {price}, 订单ID: {order.order_id}")
            return order
            
        except Exception as e:
            trade_logger.error(f"下单失败: {e}")
            raise OrderException(f"下单失败: {e}")
            
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """撤单"""
        try:
            url = f"{self.base_url}{self.api_version}/order"
            
            params = {
                'symbol': symbol,
                'orderId': order_id
            }
            
            # 签名请求
            signature = self._sign_request(params)
            params['signature'] = signature
            
            headers = self._get_headers()
            await self._make_request("DELETE", url, params=params, headers=headers)
            
            trade_logger.info(f"撤单成功: {symbol} 订单ID: {order_id}")
            return True
            
        except Exception as e:
            trade_logger.error(f"撤单失败: {e}")
            return False
            
    async def cancel_all_orders(self, symbol: Optional[str] = None) -> bool:
        """撤销所有订单"""
        try:
            url = f"{self.base_url}{self.api_version}/openOrders"
            
            params = {}
            if symbol:
                params['symbol'] = symbol
                
            # 签名请求
            signature = self._sign_request(params)
            params['signature'] = signature
            
            headers = self._get_headers()
            await self._make_request("DELETE", url, params=params, headers=headers)
            
            trade_logger.info(f"撤销所有订单成功: {symbol if symbol else '所有交易对'}")
            return True
            
        except Exception as e:
            trade_logger.error(f"撤销所有订单失败: {e}")
            return False
            
    async def get_order(self, symbol: str, order_id: str) -> ExchangeOrder:
        """查询订单"""
        try:
            url = f"{self.base_url}{self.api_version}/order"
            
            params = {
                'symbol': symbol,
                'orderId': order_id
            }
            
            # 签名请求
            signature = self._sign_request(params)
            params['signature'] = signature
            
            headers = self._get_headers()
            response = await self._make_request("GET", url, params=params, headers=headers)
            
            # 解析响应
            order = ExchangeOrder(
                order_id=str(response['orderId']),
                symbol=response['symbol'],
                side=OrderSide.BUY if response['side'] == 'BUY' else OrderSide.SELL,
                order_type=OrderType.LIMIT,  # 简化处理
                amount=float(response['origQty']),
                price=float(response['price']) if response.get('price') else None,
                status=self._convert_order_status(response['status']),
                filled_amount=float(response['executedQty']),
                avg_price=float(response['price']) if response.get('price') else 0.0,
                timestamp=response['time'] / 1000,
                update_time=response['updateTime'] / 1000
            )
            
            return order
            
        except Exception as e:
            trade_logger.error(f"查询订单失败: {e}")
            raise OrderException(f"查询订单失败: {e}")
            
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[ExchangeOrder]:
        """获取活跃订单"""
        try:
            url = f"{self.base_url}{self.api_version}/openOrders"
            
            params = {}
            if symbol:
                params['symbol'] = symbol
                
            # 签名请求
            signature = self._sign_request(params)
            params['signature'] = signature
            
            headers = self._get_headers()
            response = await self._make_request("GET", url, params=params, headers=headers)
            
            orders = []
            for order_data in response:
                order = ExchangeOrder(
                    order_id=str(order_data['orderId']),
                    symbol=order_data['symbol'],
                    side=OrderSide.BUY if order_data['side'] == 'BUY' else OrderSide.SELL,
                    order_type=OrderType.LIMIT,  # 简化处理
                    amount=float(order_data['origQty']),
                    price=float(order_data['price']) if order_data.get('price') else None,
                    status=self._convert_order_status(order_data['status']),
                    filled_amount=float(order_data['executedQty']),
                    avg_price=float(order_data['price']) if order_data.get('price') else 0.0,
                    timestamp=order_data['time'] / 1000,
                    update_time=order_data['updateTime'] / 1000
                )
                orders.append(order)
                
            return orders
            
        except Exception as e:
            trade_logger.error(f"获取活跃订单失败: {e}")
            raise ExchangeException(f"获取活跃订单失败: {e}")
            
    async def get_order_history(self, symbol: Optional[str] = None,
                               start_time: Optional[int] = None,
                               end_time: Optional[int] = None,
                               limit: int = 500) -> List[ExchangeOrder]:
        """获取历史订单"""
        try:
            url = f"{self.base_url}{self.api_version}/allOrders"
            
            params = {'limit': limit}
            if symbol:
                params['symbol'] = symbol
            if start_time:
                params['startTime'] = start_time
            if end_time:
                params['endTime'] = end_time
                
            # 签名请求
            signature = self._sign_request(params)
            params['signature'] = signature
            
            headers = self._get_headers()
            response = await self._make_request("GET", url, params=params, headers=headers)
            
            orders = []
            for order_data in response:
                order = ExchangeOrder(
                    order_id=str(order_data['orderId']),
                    symbol=order_data['symbol'],
                    side=OrderSide.BUY if order_data['side'] == 'BUY' else OrderSide.SELL,
                    order_type=OrderType.LIMIT,  # 简化处理
                    amount=float(order_data['origQty']),
                    price=float(order_data['price']) if order_data.get('price') else None,
                    status=self._convert_order_status(order_data['status']),
                    filled_amount=float(order_data['executedQty']),
                    avg_price=float(order_data['price']) if order_data.get('price') else 0.0,
                    timestamp=order_data['time'] / 1000,
                    update_time=order_data['updateTime'] / 1000
                )
                orders.append(order)
                
            return orders
            
        except Exception as e:
            trade_logger.error(f"获取历史订单失败: {e}")
            raise ExchangeException(f"获取历史订单失败: {e}")
            
    async def get_trades_history(self, symbol: Optional[str] = None,
                                start_time: Optional[int] = None,
                                end_time: Optional[int] = None,
                                limit: int = 500) -> List[Trade]:
        """获取成交历史"""
        try:
            url = f"{self.base_url}{self.api_version}/myTrades"
            
            params = {'limit': limit}
            if symbol:
                params['symbol'] = symbol
            if start_time:
                params['startTime'] = start_time
            if end_time:
                params['endTime'] = end_time
                
            # 签名请求
            signature = self._sign_request(params)
            params['signature'] = signature
            
            headers = self._get_headers()
            response = await self._make_request("GET", url, params=params, headers=headers)
            
            trades = []
            for trade_data in response:
                trade = Trade(
                    symbol=trade_data['symbol'],
                    price=float(trade_data['price']),
                    amount=float(trade_data['qty']),
                    side=OrderSide.BUY if trade_data['isBuyer'] else OrderSide.SELL,
                    timestamp=trade_data['time'] / 1000,
                    trade_id=str(trade_data['id'])
                )
                trades.append(trade)
                
            return trades
            
        except Exception as e:
            trade_logger.error(f"获取成交历史失败: {e}")
            raise ExchangeException(f"获取成交历史失败: {e}")