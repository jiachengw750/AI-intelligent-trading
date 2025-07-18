#!/usr/bin/env python3
"""
测试数据管理模块
提供测试数据的生成、清理、模拟和管理功能
"""

import asyncio
import json
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Generator
from pathlib import Path
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch


class TestDataManager:
    """测试数据管理器"""
    
    def __init__(self, data_dir: str = "/tmp/test_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # 数据配置
        self.config = {
            'symbols': ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'DOT/USDT'],
            'price_ranges': {
                'BTC/USDT': (30000, 70000),
                'ETH/USDT': (1500, 4000),
                'BNB/USDT': (200, 600),
                'ADA/USDT': (0.3, 1.5),
                'DOT/USDT': (5, 25)
            },
            'volume_ranges': {
                'BTC/USDT': (100, 10000),
                'ETH/USDT': (500, 50000),
                'BNB/USDT': (1000, 100000),
                'ADA/USDT': (10000, 1000000),
                'DOT/USDT': (5000, 500000)
            }
        }
        
        self.generated_data = {}
        self.cleanup_tasks = []
    
    def generate_market_data(self, symbol: str, count: int = 100, 
                           time_interval: int = 60) -> List[Dict[str, Any]]:
        """生成市场数据"""
        
        if symbol not in self.config['price_ranges']:
            raise ValueError(f"Unsupported symbol: {symbol}")
        
        price_range = self.config['price_ranges'][symbol]
        volume_range = self.config['volume_ranges'][symbol]
        
        # 生成基础价格序列
        base_price = random.uniform(*price_range)
        price_volatility = base_price * 0.02  # 2% 波动率
        
        market_data = []
        current_time = datetime.now()
        
        for i in range(count):
            # 生成价格（随机游走）
            price_change = random.gauss(0, price_volatility)
            current_price = max(base_price + price_change, price_range[0])
            current_price = min(current_price, price_range[1])
            base_price = current_price
            
            # 生成其他数据
            volume = random.uniform(*volume_range)
            spread = current_price * 0.001  # 0.1% 点差
            
            data_point = {
                'symbol': symbol,
                'timestamp': (current_time - timedelta(seconds=i * time_interval)).isoformat(),
                'price': round(current_price, 2),
                'volume': round(volume, 2),
                'high': round(current_price * (1 + random.uniform(0, 0.02)), 2),
                'low': round(current_price * (1 - random.uniform(0, 0.02)), 2),
                'open': round(current_price * (1 + random.uniform(-0.01, 0.01)), 2),
                'close': round(current_price, 2),
                'bid': round(current_price - spread/2, 2),
                'ask': round(current_price + spread/2, 2)
            }
            
            market_data.append(data_point)
        
        # 保存生成的数据
        self._save_generated_data(f'market_data_{symbol}', market_data)
        
        return market_data
    
    def generate_trade_data(self, symbol: str, count: int = 50) -> List[Dict[str, Any]]:
        """生成交易数据"""
        
        market_data = self.generate_market_data(symbol, count)
        trade_data = []
        
        for i in range(count):
            action = random.choice(['buy', 'sell'])
            price = market_data[i]['price']
            quantity = random.uniform(0.001, 1.0)
            
            trade = {
                'id': f'trade_{uuid.uuid4().hex[:8]}',
                'symbol': symbol,
                'action': action,
                'price': price,
                'quantity': round(quantity, 6),
                'timestamp': market_data[i]['timestamp'],
                'status': random.choice(['completed', 'pending', 'failed']),
                'fees': round(price * quantity * 0.001, 4),  # 0.1% 手续费
                'order_id': f'order_{uuid.uuid4().hex[:8]}'
            }
            
            trade_data.append(trade)
        
        self._save_generated_data(f'trade_data_{symbol}', trade_data)
        
        return trade_data
    
    def generate_portfolio_data(self, symbols: List[str] = None) -> Dict[str, Any]:
        """生成投资组合数据"""
        
        if symbols is None:
            symbols = self.config['symbols'][:3]  # 默认前3个交易对
        
        portfolio = {
            'timestamp': datetime.now().isoformat(),
            'total_value': 0.0,
            'cash_balance': random.uniform(1000, 10000),
            'positions': {},
            'total_pnl': 0.0,
            'daily_pnl': 0.0
        }
        
        for symbol in symbols:
            price_range = self.config['price_ranges'][symbol]
            current_price = random.uniform(*price_range)
            quantity = random.uniform(0.01, 1.0)
            avg_price = current_price * random.uniform(0.9, 1.1)
            
            position = {
                'symbol': symbol,
                'quantity': round(quantity, 6),
                'average_price': round(avg_price, 2),
                'current_price': round(current_price, 2),
                'market_value': round(current_price * quantity, 2),
                'unrealized_pnl': round((current_price - avg_price) * quantity, 2),
                'realized_pnl': round(random.uniform(-100, 100), 2),
                'percentage': 0.0  # 将在后面计算
            }
            
            portfolio['positions'][symbol] = position
            portfolio['total_value'] += position['market_value']
            portfolio['total_pnl'] += position['unrealized_pnl'] + position['realized_pnl']
        
        portfolio['total_value'] += portfolio['cash_balance']
        portfolio['daily_pnl'] = portfolio['total_pnl'] * random.uniform(0.8, 1.2)
        
        # 计算持仓百分比
        for symbol, position in portfolio['positions'].items():
            position['percentage'] = round(
                (position['market_value'] / portfolio['total_value']) * 100, 2
            )
        
        self._save_generated_data('portfolio_data', portfolio)
        
        return portfolio
    
    def generate_user_data(self, count: int = 10) -> List[Dict[str, Any]]:
        """生成用户数据"""
        
        users = []
        
        for i in range(count):
            user = {
                'id': f'user_{uuid.uuid4().hex[:8]}',
                'username': f'user_{i+1}',
                'email': f'user{i+1}@example.com',
                'created_at': (datetime.now() - timedelta(days=random.randint(1, 365))).isoformat(),
                'last_login': (datetime.now() - timedelta(hours=random.randint(1, 24))).isoformat(),
                'status': random.choice(['active', 'inactive', 'suspended']),
                'balance': round(random.uniform(100, 50000), 2),
                'risk_level': random.choice(['low', 'medium', 'high']),
                'trading_enabled': random.choice([True, False]),
                'kyc_verified': random.choice([True, False])
            }
            
            users.append(user)
        
        self._save_generated_data('user_data', users)
        
        return users
    
    def generate_order_data(self, symbol: str, count: int = 30) -> List[Dict[str, Any]]:
        """生成订单数据"""
        
        orders = []
        price_range = self.config['price_ranges'][symbol]
        
        for i in range(count):
            action = random.choice(['buy', 'sell'])
            order_type = random.choice(['market', 'limit', 'stop_loss', 'take_profit'])
            price = random.uniform(*price_range)
            quantity = random.uniform(0.001, 1.0)
            
            order = {
                'id': f'order_{uuid.uuid4().hex[:8]}',
                'symbol': symbol,
                'action': action,
                'type': order_type,
                'price': round(price, 2),
                'quantity': round(quantity, 6),
                'filled_quantity': round(quantity * random.uniform(0, 1), 6),
                'status': random.choice(['pending', 'filled', 'partial', 'cancelled']),
                'timestamp': (datetime.now() - timedelta(minutes=random.randint(1, 1440))).isoformat(),
                'user_id': f'user_{uuid.uuid4().hex[:8]}',
                'fees': round(price * quantity * 0.001, 4)
            }
            
            # 如果是限价单，调整价格
            if order_type == 'limit':
                if action == 'buy':
                    order['price'] = round(price * 0.98, 2)  # 买入限价低于市价
                else:
                    order['price'] = round(price * 1.02, 2)  # 卖出限价高于市价
            
            orders.append(order)
        
        self._save_generated_data(f'order_data_{symbol}', orders)
        
        return orders
    
    def generate_system_metrics(self, count: int = 100) -> List[Dict[str, Any]]:
        """生成系统指标数据"""
        
        metrics = []
        current_time = datetime.now()
        
        for i in range(count):
            metric = {
                'timestamp': (current_time - timedelta(seconds=i * 30)).isoformat(),
                'cpu_usage': round(random.uniform(10, 90), 2),
                'memory_usage': round(random.uniform(30, 85), 2),
                'disk_usage': round(random.uniform(20, 80), 2),
                'network_io': {
                    'bytes_sent': random.randint(1000, 100000),
                    'bytes_received': random.randint(5000, 500000)
                },
                'active_connections': random.randint(10, 100),
                'response_time': round(random.uniform(0.01, 0.5), 3),
                'error_rate': round(random.uniform(0, 0.05), 4),
                'throughput': random.randint(50, 500)
            }
            
            metrics.append(metric)
        
        self._save_generated_data('system_metrics', metrics)
        
        return metrics
    
    def generate_ai_analysis_data(self, symbol: str, count: int = 20) -> List[Dict[str, Any]]:
        """生成AI分析数据"""
        
        analyses = []
        
        for i in range(count):
            analysis = {
                'timestamp': (datetime.now() - timedelta(hours=i)).isoformat(),
                'symbol': symbol,
                'trend': random.choice(['bullish', 'bearish', 'neutral']),
                'confidence': round(random.uniform(0.1, 0.9), 2),
                'indicators': {
                    'rsi': round(random.uniform(20, 80), 2),
                    'macd': round(random.uniform(-1, 1), 4),
                    'bollinger_position': random.choice(['upper', 'middle', 'lower']),
                    'sma_20': round(random.uniform(40000, 50000), 2),
                    'sma_50': round(random.uniform(39000, 51000), 2)
                },
                'support_levels': [
                    round(random.uniform(42000, 44000), 2),
                    round(random.uniform(40000, 42000), 2)
                ],
                'resistance_levels': [
                    round(random.uniform(46000, 48000), 2),
                    round(random.uniform(48000, 50000), 2)
                ],
                'recommendation': random.choice(['buy', 'sell', 'hold']),
                'risk_score': round(random.uniform(0.1, 0.8), 2),
                'reasoning': f"AI analysis for {symbol} based on technical indicators"
            }
            
            analyses.append(analysis)
        
        self._save_generated_data(f'ai_analysis_{symbol}', analyses)
        
        return analyses
    
    def create_mock_data_source(self, data_type: str, data: List[Dict[str, Any]]):
        """创建模拟数据源"""
        
        class MockDataSource:
            def __init__(self, data):
                self.data = data
                self.current_index = 0
            
            async def get_next(self):
                if self.current_index >= len(self.data):
                    self.current_index = 0
                
                item = self.data[self.current_index]
                self.current_index += 1
                return item
            
            async def get_all(self):
                return self.data
            
            async def get_by_symbol(self, symbol):
                return [item for item in self.data if item.get('symbol') == symbol]
        
        return MockDataSource(data)
    
    def create_market_data_stream(self, symbol: str, interval: float = 1.0) -> Generator:
        """创建市场数据流生成器"""
        
        price_range = self.config['price_ranges'][symbol]
        base_price = random.uniform(*price_range)
        
        while True:
            # 生成实时价格变化
            price_change = random.gauss(0, base_price * 0.005)
            current_price = max(base_price + price_change, price_range[0])
            current_price = min(current_price, price_range[1])
            base_price = current_price
            
            market_data = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'price': round(current_price, 2),
                'volume': round(random.uniform(*self.config['volume_ranges'][symbol]), 2),
                'bid': round(current_price - current_price * 0.0005, 2),
                'ask': round(current_price + current_price * 0.0005, 2)
            }
            
            yield market_data
    
    async def simulate_trading_scenario(self, scenario_name: str, 
                                      duration: int = 60) -> Dict[str, Any]:
        """模拟交易场景"""
        
        scenarios = {
            'normal_market': self._simulate_normal_market,
            'volatile_market': self._simulate_volatile_market,
            'crash_scenario': self._simulate_crash_scenario,
            'bull_run': self._simulate_bull_run,
            'high_frequency': self._simulate_high_frequency
        }
        
        if scenario_name not in scenarios:
            raise ValueError(f"Unknown scenario: {scenario_name}")
        
        print(f"Starting simulation: {scenario_name}")
        start_time = datetime.now()
        
        scenario_data = await scenarios[scenario_name](duration)
        
        end_time = datetime.now()
        scenario_data['simulation_info'] = {
            'scenario': scenario_name,
            'duration': duration,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'actual_duration': (end_time - start_time).total_seconds()
        }
        
        self._save_generated_data(f'scenario_{scenario_name}', scenario_data)
        
        return scenario_data
    
    async def _simulate_normal_market(self, duration: int) -> Dict[str, Any]:
        """模拟正常市场条件"""
        
        market_data = []
        trade_data = []
        
        for i in range(duration):
            # 生成市场数据
            for symbol in self.config['symbols']:
                data = self.generate_market_data(symbol, 1)[0]
                market_data.append(data)
                
                # 随机生成交易
                if random.random() < 0.3:  # 30%概率生成交易
                    trade = self.generate_trade_data(symbol, 1)[0]
                    trade_data.append(trade)
            
            await asyncio.sleep(0.1)  # 模拟实时间隔
        
        return {
            'market_data': market_data,
            'trade_data': trade_data,
            'scenario_type': 'normal_market'
        }
    
    async def _simulate_volatile_market(self, duration: int) -> Dict[str, Any]:
        """模拟波动市场"""
        
        market_data = []
        volatility_events = []
        
        for i in range(duration):
            # 增加波动性
            volatility_multiplier = random.uniform(1.5, 3.0)
            
            for symbol in self.config['symbols']:
                data = self.generate_market_data(symbol, 1)[0]
                
                # 应用波动性
                base_price = data['price']
                volatility = base_price * 0.02 * volatility_multiplier
                price_change = random.gauss(0, volatility)
                data['price'] += price_change
                data['high'] = max(data['high'], data['price'])
                data['low'] = min(data['low'], data['price'])
                
                market_data.append(data)
                
                # 记录波动事件
                if abs(price_change) > base_price * 0.05:
                    volatility_events.append({
                        'timestamp': data['timestamp'],
                        'symbol': symbol,
                        'price_change': price_change,
                        'percentage_change': (price_change / base_price) * 100
                    })
            
            await asyncio.sleep(0.1)
        
        return {
            'market_data': market_data,
            'volatility_events': volatility_events,
            'scenario_type': 'volatile_market'
        }
    
    async def _simulate_crash_scenario(self, duration: int) -> Dict[str, Any]:
        """模拟市场崩盘场景"""
        
        market_data = []
        crash_events = []
        
        crash_started = False
        crash_start_time = random.randint(10, duration - 20)
        
        for i in range(duration):
            if i == crash_start_time:
                crash_started = True
                crash_events.append({
                    'type': 'crash_start',
                    'timestamp': datetime.now().isoformat(),
                    'trigger': 'market_panic'
                })
            
            for symbol in self.config['symbols']:
                data = self.generate_market_data(symbol, 1)[0]
                
                # 应用崩盘效应
                if crash_started:
                    crash_intensity = min((i - crash_start_time) / 10, 1.0)
                    price_drop = data['price'] * crash_intensity * 0.1
                    data['price'] -= price_drop
                    data['low'] = min(data['low'], data['price'])
                    data['volume'] *= (1 + crash_intensity * 2)  # 增加交易量
                
                market_data.append(data)
            
            await asyncio.sleep(0.1)
        
        return {
            'market_data': market_data,
            'crash_events': crash_events,
            'scenario_type': 'crash_scenario'
        }
    
    async def _simulate_bull_run(self, duration: int) -> Dict[str, Any]:
        """模拟牛市场景"""
        
        market_data = []
        
        for i in range(duration):
            uptrend_strength = 0.002  # 2%上升趋势
            
            for symbol in self.config['symbols']:
                data = self.generate_market_data(symbol, 1)[0]
                
                # 应用上升趋势
                trend_boost = data['price'] * uptrend_strength
                data['price'] += trend_boost
                data['high'] = max(data['high'], data['price'])
                data['volume'] *= 1.2  # 增加交易量
                
                market_data.append(data)
            
            await asyncio.sleep(0.1)
        
        return {
            'market_data': market_data,
            'scenario_type': 'bull_run'
        }
    
    async def _simulate_high_frequency(self, duration: int) -> Dict[str, Any]:
        """模拟高频交易场景"""
        
        market_data = []
        hft_orders = []
        
        for i in range(duration * 10):  # 高频率
            for symbol in self.config['symbols']:
                data = self.generate_market_data(symbol, 1)[0]
                
                # 微小价格变化
                micro_change = data['price'] * random.uniform(-0.0001, 0.0001)
                data['price'] += micro_change
                
                market_data.append(data)
                
                # 生成高频订单
                if random.random() < 0.7:  # 70%概率生成订单
                    order = {
                        'timestamp': data['timestamp'],
                        'symbol': symbol,
                        'action': random.choice(['buy', 'sell']),
                        'quantity': round(random.uniform(0.001, 0.1), 6),
                        'price': data['price'],
                        'type': 'market',
                        'execution_time': random.uniform(0.001, 0.01)
                    }
                    hft_orders.append(order)
            
            await asyncio.sleep(0.01)  # 高频间隔
        
        return {
            'market_data': market_data,
            'hft_orders': hft_orders,
            'scenario_type': 'high_frequency'
        }
    
    def _save_generated_data(self, key: str, data: Any):
        """保存生成的数据"""
        
        self.generated_data[key] = data
        
        # 保存到文件
        file_path = self.data_dir / f"{key}.json"
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        # 添加到清理任务
        self.cleanup_tasks.append(file_path)
    
    def get_generated_data(self, key: str) -> Any:
        """获取生成的数据"""
        return self.generated_data.get(key)
    
    def cleanup_test_data(self):
        """清理测试数据"""
        
        print("Cleaning up test data...")
        
        # 清理生成的文件
        for file_path in self.cleanup_tasks:
            if file_path.exists():
                file_path.unlink()
        
        # 清理内存中的数据
        self.generated_data.clear()
        self.cleanup_tasks.clear()
        
        print("Test data cleanup completed.")
    
    def export_to_csv(self, key: str, output_path: Optional[str] = None):
        """导出数据到CSV"""
        
        data = self.get_generated_data(key)
        if not data:
            raise ValueError(f"No data found for key: {key}")
        
        if output_path is None:
            output_path = self.data_dir / f"{key}.csv"
        
        if isinstance(data, list):
            df = pd.DataFrame(data)
            df.to_csv(output_path, index=False)
        else:
            # 处理单个对象
            df = pd.DataFrame([data])
            df.to_csv(output_path, index=False)
        
        print(f"Data exported to: {output_path}")
    
    def create_test_database(self, db_name: str = "test_trading_db"):
        """创建测试数据库"""
        
        # 这里可以创建实际的数据库连接和表结构
        # 目前返回模拟的数据库配置
        return {
            'host': 'localhost',
            'port': 5432,
            'database': db_name,
            'username': 'test_user',
            'password': 'test_password',
            'schema': 'test_schema'
        }
    
    def create_test_fixtures(self) -> Dict[str, Any]:
        """创建测试固定数据"""
        
        fixtures = {
            'users': self.generate_user_data(5),
            'market_data': {},
            'portfolios': {},
            'orders': {},
            'trades': {}
        }
        
        # 为每个交易对生成固定数据
        for symbol in self.config['symbols']:
            fixtures['market_data'][symbol] = self.generate_market_data(symbol, 50)
            fixtures['orders'][symbol] = self.generate_order_data(symbol, 20)
            fixtures['trades'][symbol] = self.generate_trade_data(symbol, 15)
        
        # 生成投资组合数据
        for user in fixtures['users']:
            user_symbols = random.sample(self.config['symbols'], 3)
            fixtures['portfolios'][user['id']] = self.generate_portfolio_data(user_symbols)
        
        self._save_generated_data('test_fixtures', fixtures)
        
        return fixtures


# 测试数据管理器的使用示例
if __name__ == '__main__':
    async def main():
        # 创建测试数据管理器
        test_manager = TestDataManager()
        
        try:
            # 生成各种测试数据
            print("Generating test data...")
            
            # 生成市场数据
            market_data = test_manager.generate_market_data('BTC/USDT', 100)
            print(f"Generated {len(market_data)} market data points")
            
            # 生成交易数据
            trade_data = test_manager.generate_trade_data('BTC/USDT', 50)
            print(f"Generated {len(trade_data)} trade records")
            
            # 生成投资组合数据
            portfolio = test_manager.generate_portfolio_data()
            print(f"Generated portfolio with {len(portfolio['positions'])} positions")
            
            # 生成用户数据
            users = test_manager.generate_user_data(10)
            print(f"Generated {len(users)} user records")
            
            # 模拟交易场景
            scenario_data = await test_manager.simulate_trading_scenario('normal_market', 30)
            print(f"Simulated normal market scenario with {len(scenario_data['market_data'])} data points")
            
            # 创建测试固定数据
            fixtures = test_manager.create_test_fixtures()
            print(f"Created test fixtures with {len(fixtures)} categories")
            
            # 导出数据
            test_manager.export_to_csv('market_data_BTC/USDT')
            test_manager.export_to_csv('trade_data_BTC/USDT')
            
            print("Test data generation completed successfully!")
            
        finally:
            # 清理测试数据
            test_manager.cleanup_test_data()
    
    asyncio.run(main())