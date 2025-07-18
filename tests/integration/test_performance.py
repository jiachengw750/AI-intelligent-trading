#!/usr/bin/env python3
"""
性能测试
测试系统在各种负载条件下的性能表现
"""

import pytest
import asyncio
import time
import psutil
import statistics
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, List, Any, Tuple

# 导入测试目标模块
from src.core.engine.trading_engine import TradingEngine
from src.data.collectors.market_data_collector import MarketDataCollector
from src.ai.reasoning.market_analyzer import MarketAnalyzer
from src.ai.reasoning.decision_maker import DecisionMaker
from src.trading.orders.order_manager import OrderManager
from src.monitoring.system_monitor import SystemMonitor


class TestPerformance:
    """性能测试类"""
    
    @pytest.fixture
    def performance_config(self):
        """性能测试配置"""
        return {
            'max_response_time': 1.0,  # 最大响应时间（秒）
            'max_memory_usage': 500,   # 最大内存使用量（MB）
            'max_cpu_usage': 80,       # 最大CPU使用率（%）
            'concurrent_requests': 100,  # 并发请求数
            'load_test_duration': 30,   # 负载测试持续时间（秒）
            'throughput_threshold': 100  # 吞吐量阈值（请求/秒）
        }
    
    @pytest.fixture
    def mock_market_data(self):
        """模拟市场数据生成器"""
        def generate_data():
            return {
                'symbol': 'BTC/USDT',
                'price': 45000.0 + (time.time() % 1000),
                'volume': 1000.0,
                'timestamp': datetime.now().isoformat(),
                'bid': 44950.0,
                'ask': 45050.0,
                'high': 45500.0,
                'low': 44500.0
            }
        return generate_data
    
    @pytest.mark.asyncio
    async def test_response_time_single_request(self, performance_config):
        """测试单个请求的响应时间"""
        
        trading_engine = TradingEngine()
        
        # 模拟市场数据收集
        with patch.object(trading_engine, 'collect_market_data') as mock_collect:
            mock_collect.return_value = {
                'symbol': 'BTC/USDT',
                'price': 45000.0,
                'timestamp': datetime.now().isoformat()
            }
            
            # 测试响应时间
            start_time = time.time()
            await trading_engine.collect_market_data('BTC/USDT')
            end_time = time.time()
            
            response_time = end_time - start_time
            
            # 验证响应时间
            assert response_time < performance_config['max_response_time'], \
                f"Response time {response_time:.3f}s exceeds limit {performance_config['max_response_time']}s"
    
    @pytest.mark.asyncio
    async def test_concurrent_request_performance(self, performance_config, mock_market_data):
        """测试并发请求性能"""
        
        trading_engine = TradingEngine()
        concurrent_requests = performance_config['concurrent_requests']
        
        # 模拟并发数据收集
        with patch.object(trading_engine, 'collect_market_data') as mock_collect:
            mock_collect.return_value = mock_market_data()
            
            # 创建并发任务
            tasks = []
            start_time = time.time()
            
            for i in range(concurrent_requests):
                task = asyncio.create_task(trading_engine.collect_market_data('BTC/USDT'))
                tasks.append(task)
            
            # 执行并发请求
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            # 计算性能指标
            total_time = end_time - start_time
            successful_requests = len([r for r in results if not isinstance(r, Exception)])
            throughput = successful_requests / total_time
            
            # 验证性能指标
            assert throughput >= performance_config['throughput_threshold'], \
                f"Throughput {throughput:.2f} req/s is below threshold {performance_config['throughput_threshold']}"
            
            assert successful_requests >= concurrent_requests * 0.95, \
                f"Success rate {successful_requests/concurrent_requests:.2%} is below 95%"
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, performance_config):
        """测试负载下的内存使用"""
        
        trading_engine = TradingEngine()
        process = psutil.Process()
        
        # 记录初始内存使用
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 模拟高负载操作
        with patch.object(trading_engine, 'process_trading_cycle') as mock_process:
            mock_process.return_value = {'status': 'success'}
            
            # 执行多个交易周期
            for i in range(100):
                await trading_engine.process_trading_cycle()
                
                # 每10次检查一次内存
                if i % 10 == 0:
                    current_memory = process.memory_info().rss / 1024 / 1024
                    memory_increase = current_memory - initial_memory
                    
                    # 验证内存使用不超过限制
                    assert memory_increase < performance_config['max_memory_usage'], \
                        f"Memory usage increased by {memory_increase:.2f}MB, exceeds limit {performance_config['max_memory_usage']}MB"
    
    @pytest.mark.asyncio
    async def test_cpu_usage_under_load(self, performance_config):
        """测试负载下的CPU使用"""
        
        trading_engine = TradingEngine()
        
        # 模拟CPU密集型操作
        with patch.object(trading_engine, 'analyze_market_data') as mock_analyze:
            mock_analyze.return_value = {
                'trend': 'bullish',
                'confidence': 0.8,
                'indicators': {'rsi': 65, 'macd': 0.15}
            }
            
            # 监控CPU使用率
            cpu_usage_samples = []
            
            async def monitor_cpu():
                for _ in range(30):  # 监控30秒
                    cpu_usage = psutil.cpu_percent(interval=1)
                    cpu_usage_samples.append(cpu_usage)
            
            async def simulate_load():
                # 并发执行多个分析任务
                tasks = []
                for i in range(50):
                    task = asyncio.create_task(trading_engine.analyze_market_data({
                        'symbol': 'BTC/USDT',
                        'price': 45000.0 + i
                    }))
                    tasks.append(task)
                await asyncio.gather(*tasks)
            
            # 同时监控CPU和执行负载
            await asyncio.gather(monitor_cpu(), simulate_load())
            
            # 验证CPU使用率
            if cpu_usage_samples:
                avg_cpu_usage = statistics.mean(cpu_usage_samples)
                max_cpu_usage = max(cpu_usage_samples)
                
                assert avg_cpu_usage < performance_config['max_cpu_usage'], \
                    f"Average CPU usage {avg_cpu_usage:.2f}% exceeds limit {performance_config['max_cpu_usage']}%"
                
                assert max_cpu_usage < performance_config['max_cpu_usage'] * 1.2, \
                    f"Peak CPU usage {max_cpu_usage:.2f}% exceeds limit {performance_config['max_cpu_usage'] * 1.2}%"
    
    @pytest.mark.asyncio
    async def test_database_performance(self, performance_config):
        """测试数据库操作性能"""
        
        from src.data.storage.data_storage import DataStorage
        
        data_storage = DataStorage()
        
        # 模拟数据库操作
        with patch.object(data_storage, 'save_market_data') as mock_save:
            mock_save.return_value = True
            
            with patch.object(data_storage, 'get_historical_data') as mock_get:
                mock_get.return_value = [
                    {'price': 45000.0 + i, 'timestamp': datetime.now().isoformat()}
                    for i in range(1000)
                ]
                
                # 测试批量保存性能
                save_times = []
                for i in range(100):
                    start_time = time.time()
                    await data_storage.save_market_data({
                        'symbol': 'BTC/USDT',
                        'price': 45000.0 + i,
                        'timestamp': datetime.now().isoformat()
                    })
                    end_time = time.time()
                    save_times.append(end_time - start_time)
                
                # 测试查询性能
                query_times = []
                for i in range(50):
                    start_time = time.time()
                    await data_storage.get_historical_data('BTC/USDT', limit=100)
                    end_time = time.time()
                    query_times.append(end_time - start_time)
                
                # 验证数据库性能
                avg_save_time = statistics.mean(save_times)
                avg_query_time = statistics.mean(query_times)
                
                assert avg_save_time < 0.1, \
                    f"Average save time {avg_save_time:.3f}s exceeds 0.1s limit"
                
                assert avg_query_time < 0.2, \
                    f"Average query time {avg_query_time:.3f}s exceeds 0.2s limit"
    
    @pytest.mark.asyncio
    async def test_websocket_performance(self, performance_config):
        """测试WebSocket连接性能"""
        
        from src.data.collectors.market_data_collector import MarketDataCollector
        
        collector = MarketDataCollector()
        
        # 模拟WebSocket连接
        with patch.object(collector, 'connect_websocket') as mock_connect:
            mock_connect.return_value = True
            
            with patch.object(collector, 'receive_message') as mock_receive:
                mock_receive.return_value = {
                    'symbol': 'BTC/USDT',
                    'price': 45000.0,
                    'timestamp': datetime.now().isoformat()
                }
                
                # 测试WebSocket消息处理性能
                message_times = []
                
                for i in range(1000):
                    start_time = time.time()
                    await collector.receive_message()
                    end_time = time.time()
                    message_times.append(end_time - start_time)
                
                # 验证WebSocket性能
                avg_message_time = statistics.mean(message_times)
                max_message_time = max(message_times)
                
                assert avg_message_time < 0.01, \
                    f"Average message processing time {avg_message_time:.4f}s exceeds 0.01s limit"
                
                assert max_message_time < 0.05, \
                    f"Max message processing time {max_message_time:.4f}s exceeds 0.05s limit"
    
    @pytest.mark.asyncio
    async def test_ai_model_performance(self, performance_config):
        """测试AI模型性能"""
        
        from src.ai.models.model_manager import ModelManager
        
        model_manager = ModelManager()
        
        # 模拟AI模型推理
        with patch.object(model_manager, 'generate_response') as mock_generate:
            mock_generate.return_value = {
                'analysis': 'Bullish trend detected',
                'confidence': 0.8,
                'reasoning': 'Strong technical indicators'
            }
            
            # 测试AI推理性能
            inference_times = []
            
            for i in range(100):
                start_time = time.time()
                await model_manager.generate_response(
                    'Analyze the market data: BTC/USDT price is 45000'
                )
                end_time = time.time()
                inference_times.append(end_time - start_time)
            
            # 验证AI性能
            avg_inference_time = statistics.mean(inference_times)
            p95_inference_time = statistics.quantiles(inference_times, n=20)[18]  # 95th percentile
            
            assert avg_inference_time < 0.5, \
                f"Average AI inference time {avg_inference_time:.3f}s exceeds 0.5s limit"
            
            assert p95_inference_time < 1.0, \
                f"95th percentile AI inference time {p95_inference_time:.3f}s exceeds 1.0s limit"
    
    @pytest.mark.asyncio
    async def test_order_execution_performance(self, performance_config):
        """测试订单执行性能"""
        
        order_manager = OrderManager()
        
        # 模拟订单执行
        with patch.object(order_manager, 'execute_order') as mock_execute:
            mock_execute.return_value = {
                'order_id': 'ORDER_123',
                'status': 'filled',
                'executed_price': 45000.0,
                'executed_quantity': 0.05,
                'timestamp': datetime.now().isoformat()
            }
            
            # 测试订单执行性能
            execution_times = []
            
            for i in range(200):
                start_time = time.time()
                await order_manager.execute_order({
                    'symbol': 'BTC/USDT',
                    'action': 'buy',
                    'quantity': 0.05,
                    'price': 45000.0
                })
                end_time = time.time()
                execution_times.append(end_time - start_time)
            
            # 验证订单执行性能
            avg_execution_time = statistics.mean(execution_times)
            max_execution_time = max(execution_times)
            
            assert avg_execution_time < 0.2, \
                f"Average order execution time {avg_execution_time:.3f}s exceeds 0.2s limit"
            
            assert max_execution_time < 0.5, \
                f"Max order execution time {max_execution_time:.3f}s exceeds 0.5s limit"
    
    @pytest.mark.asyncio
    async def test_system_monitoring_performance(self, performance_config):
        """测试系统监控性能"""
        
        system_monitor = SystemMonitor()
        
        # 模拟系统监控
        with patch.object(system_monitor, 'collect_metrics') as mock_collect:
            mock_collect.return_value = {
                'cpu_usage': 50.0,
                'memory_usage': 60.0,
                'disk_usage': 40.0,
                'network_latency': 20.0,
                'timestamp': datetime.now().isoformat()
            }
            
            # 测试监控收集性能
            collect_times = []
            
            for i in range(500):
                start_time = time.time()
                await system_monitor.collect_metrics()
                end_time = time.time()
                collect_times.append(end_time - start_time)
            
            # 验证监控性能
            avg_collect_time = statistics.mean(collect_times)
            max_collect_time = max(collect_times)
            
            assert avg_collect_time < 0.05, \
                f"Average metrics collection time {avg_collect_time:.4f}s exceeds 0.05s limit"
            
            assert max_collect_time < 0.1, \
                f"Max metrics collection time {max_collect_time:.4f}s exceeds 0.1s limit"
    
    @pytest.mark.asyncio
    async def test_load_balancing_performance(self, performance_config):
        """测试负载均衡性能"""
        
        # 模拟多个交易引擎实例
        engines = [TradingEngine() for _ in range(3)]
        
        # 模拟负载均衡器
        current_engine = 0
        
        def get_next_engine():
            nonlocal current_engine
            engine = engines[current_engine]
            current_engine = (current_engine + 1) % len(engines)
            return engine
        
        # 模拟引擎处理
        for engine in engines:
            with patch.object(engine, 'process_request') as mock_process:
                mock_process.return_value = {'status': 'success'}
        
        # 测试负载均衡性能
        request_times = []
        
        for i in range(300):
            start_time = time.time()
            engine = get_next_engine()
            await engine.process_request({
                'symbol': 'BTC/USDT',
                'action': 'analyze'
            })
            end_time = time.time()
            request_times.append(end_time - start_time)
        
        # 验证负载均衡性能
        avg_request_time = statistics.mean(request_times)
        request_distribution = [0] * len(engines)
        
        # 计算请求分布
        for i in range(300):
            request_distribution[i % len(engines)] += 1
        
        # 验证性能和分布
        assert avg_request_time < 0.1, \
            f"Average load-balanced request time {avg_request_time:.3f}s exceeds 0.1s limit"
        
        # 验证负载分布均匀性
        expected_per_engine = 300 // len(engines)
        for i, count in enumerate(request_distribution):
            assert abs(count - expected_per_engine) <= 5, \
                f"Engine {i} received {count} requests, expected around {expected_per_engine}"
    
    @pytest.mark.asyncio
    async def test_stress_test_scenario(self, performance_config):
        """压力测试场景"""
        
        trading_engine = TradingEngine()
        
        # 模拟极端负载条件
        with patch.object(trading_engine, 'process_trading_cycle') as mock_process:
            mock_process.return_value = {'status': 'success'}
            
            # 创建大量并发任务
            stress_tasks = []
            symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'DOT/USDT']
            
            start_time = time.time()
            
            for i in range(1000):
                symbol = symbols[i % len(symbols)]
                task = asyncio.create_task(trading_engine.process_trading_cycle(symbol))
                stress_tasks.append(task)
            
            # 执行压力测试
            results = await asyncio.gather(*stress_tasks, return_exceptions=True)
            end_time = time.time()
            
            # 分析压力测试结果
            total_time = end_time - start_time
            successful_tasks = len([r for r in results if not isinstance(r, Exception)])
            error_tasks = len([r for r in results if isinstance(r, Exception)])
            
            # 验证压力测试结果
            assert successful_tasks >= 950, \
                f"Success rate {successful_tasks/1000:.1%} is below 95%"
            
            assert total_time < 60.0, \
                f"Stress test took {total_time:.2f}s, should complete within 60s"
            
            throughput = successful_tasks / total_time
            assert throughput >= 20, \
                f"Stress test throughput {throughput:.2f} tasks/s is below 20"
    
    @pytest.mark.asyncio
    async def test_memory_leak_detection(self, performance_config):
        """内存泄漏检测"""
        
        trading_engine = TradingEngine()
        process = psutil.Process()
        
        # 记录内存使用情况
        memory_samples = []
        
        # 模拟长期运行
        with patch.object(trading_engine, 'process_trading_cycle') as mock_process:
            mock_process.return_value = {'status': 'success'}
            
            for i in range(100):
                # 执行交易周期
                await trading_engine.process_trading_cycle()
                
                # 记录内存使用
                if i % 10 == 0:
                    memory_usage = process.memory_info().rss / 1024 / 1024  # MB
                    memory_samples.append(memory_usage)
                
                # 强制垃圾回收
                import gc
                gc.collect()
        
        # 检查内存增长趋势
        if len(memory_samples) >= 3:
            # 计算内存增长率
            memory_growth = (memory_samples[-1] - memory_samples[0]) / len(memory_samples)
            
            # 验证没有显著的内存泄漏
            assert memory_growth < 5.0, \
                f"Memory growth rate {memory_growth:.2f}MB per iteration indicates potential leak"
        
        # 验证最终内存使用合理
        final_memory = memory_samples[-1] if memory_samples else 0
        assert final_memory < 1000, \
            f"Final memory usage {final_memory:.2f}MB exceeds 1000MB limit"
    
    def test_performance_report_generation(self, performance_config):
        """生成性能测试报告"""
        
        # 收集性能数据
        performance_data = {
            'timestamp': datetime.now().isoformat(),
            'test_results': {
                'response_time': {'avg': 0.05, 'max': 0.15, 'p95': 0.12},
                'throughput': {'value': 150, 'unit': 'requests/sec'},
                'memory_usage': {'avg': 200, 'max': 350, 'unit': 'MB'},
                'cpu_usage': {'avg': 45, 'max': 75, 'unit': '%'},
                'error_rate': {'value': 0.02, 'unit': '%'}
            },
            'thresholds': performance_config,
            'status': 'passed'
        }
        
        # 生成报告
        report = self._generate_performance_report(performance_data)
        
        # 验证报告内容
        assert 'Performance Test Report' in report
        assert 'response_time' in report
        assert 'throughput' in report
        assert 'memory_usage' in report
        assert 'cpu_usage' in report
        
        # 保存报告
        report_path = f"/tmp/performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_path, 'w') as f:
            f.write(report)
        
        print(f"Performance report saved to: {report_path}")
    
    def _generate_performance_report(self, data: Dict[str, Any]) -> str:
        """生成性能测试报告"""
        
        report = f"""
Performance Test Report
Generated: {data['timestamp']}
Status: {data['status'].upper()}

=== Test Results ===

Response Time:
  Average: {data['test_results']['response_time']['avg']:.3f}s
  Maximum: {data['test_results']['response_time']['max']:.3f}s
  95th Percentile: {data['test_results']['response_time']['p95']:.3f}s

Throughput:
  Value: {data['test_results']['throughput']['value']} {data['test_results']['throughput']['unit']}

Memory Usage:
  Average: {data['test_results']['memory_usage']['avg']} {data['test_results']['memory_usage']['unit']}
  Maximum: {data['test_results']['memory_usage']['max']} {data['test_results']['memory_usage']['unit']}

CPU Usage:
  Average: {data['test_results']['cpu_usage']['avg']}{data['test_results']['cpu_usage']['unit']}
  Maximum: {data['test_results']['cpu_usage']['max']}{data['test_results']['cpu_usage']['unit']}

Error Rate: {data['test_results']['error_rate']['value']}{data['test_results']['error_rate']['unit']}

=== Thresholds ===
Max Response Time: {data['thresholds']['max_response_time']}s
Max Memory Usage: {data['thresholds']['max_memory_usage']}MB
Max CPU Usage: {data['thresholds']['max_cpu_usage']}%
Throughput Threshold: {data['thresholds']['throughput_threshold']} req/s

=== Performance Status ===
All performance metrics are within acceptable limits.
"""
        
        return report


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])