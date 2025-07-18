#!/usr/bin/env python3
"""
端到端交易系统集成测试
测试完整的交易流程，从数据收集到订单执行
"""

import asyncio
import pytest
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
from unittest.mock import Mock, patch

from src.data.collectors.market_data_collector import MarketDataCollector
from src.ai.reasoning.market_analyzer import MarketAnalyzer
from src.ai.reasoning.decision_maker import DecisionMaker
from src.trading.orders.order_manager import OrderManager
from src.trading.execution.order_executor import OrderExecutor
from src.risk.control.risk_manager import RiskManager
from src.monitoring.system_monitor import SystemMonitor
from src.core.engine.trading_engine import TradingEngine


class TestE2ETradingSystem:
    """端到端交易系统测试"""
    
    @pytest.fixture
    def mock_market_data(self):
        """模拟市场数据"""
        return {
            'symbol': 'BTC/USDT',
            'price': 45000.0,
            'volume': 1000.0,
            'timestamp': datetime.now().isoformat(),
            'bid': 44950.0,
            'ask': 45050.0,
            'high': 45500.0,
            'low': 44500.0,
            'open': 44800.0,
            'close': 45000.0
        }
    
    @pytest.fixture
    def mock_portfolio(self):
        """模拟投资组合"""
        return {
            'balance': 10000.0,
            'positions': {
                'BTC/USDT': {
                    'quantity': 0.1,
                    'average_price': 44000.0,
                    'unrealized_pnl': 100.0
                }
            }
        }
    
    @pytest.fixture
    async def trading_engine(self):
        """创建交易引擎实例"""
        engine = TradingEngine()
        await engine.initialize()
        return engine
    
    @pytest.mark.asyncio
    async def test_complete_trading_workflow(self, trading_engine, mock_market_data, mock_portfolio):
        """测试完整的交易工作流程"""
        
        # 1. 数据收集阶段
        with patch('src.data.collectors.market_data_collector.MarketDataCollector.collect_data') as mock_collect:
            mock_collect.return_value = mock_market_data
            
            # 2. 市场分析阶段
            with patch('src.ai.reasoning.market_analyzer.MarketAnalyzer.analyze_market') as mock_analyze:
                mock_analyze.return_value = {
                    'trend': 'bullish',
                    'confidence': 0.75,
                    'indicators': {
                        'rsi': 65,
                        'macd': 'positive',
                        'bollinger_bands': 'upper'
                    }
                }
                
                # 3. 决策制定阶段
                with patch('src.ai.reasoning.decision_maker.DecisionMaker.make_decision') as mock_decision:
                    mock_decision.return_value = {
                        'action': 'buy',
                        'symbol': 'BTC/USDT',
                        'quantity': 0.05,
                        'price': 45000.0,
                        'confidence': 0.8
                    }
                    
                    # 4. 风险管理阶段
                    with patch('src.risk.control.risk_manager.RiskManager.validate_order') as mock_risk:
                        mock_risk.return_value = {
                            'approved': True,
                            'max_position': 0.1,
                            'risk_score': 0.3
                        }
                        
                        # 5. 订单执行阶段
                        with patch('src.trading.execution.order_executor.OrderExecutor.execute_order') as mock_execute:
                            mock_execute.return_value = {
                                'order_id': 'ORDER_123',
                                'status': 'filled',
                                'executed_price': 45000.0,
                                'executed_quantity': 0.05,
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            # 执行完整流程
                            result = await trading_engine.process_trading_cycle()
                            
                            # 验证结果
                            assert result['status'] == 'success'
                            assert 'order_id' in result
                            assert result['executed_quantity'] == 0.05
                            
                            # 验证所有组件都被调用
                            mock_collect.assert_called_once()
                            mock_analyze.assert_called_once()
                            mock_decision.assert_called_once()
                            mock_risk.assert_called_once()
                            mock_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_error_handling_in_workflow(self, trading_engine):
        """测试工作流程中的错误处理"""
        
        # 模拟数据收集失败
        with patch('src.data.collectors.market_data_collector.MarketDataCollector.collect_data') as mock_collect:
            mock_collect.side_effect = Exception("Market data unavailable")
            
            result = await trading_engine.process_trading_cycle()
            
            # 验证错误处理
            assert result['status'] == 'error'
            assert 'Market data unavailable' in result['error']
            assert result['recovery_action'] == 'retry_with_backup_source'
    
    @pytest.mark.asyncio
    async def test_risk_management_rejection(self, trading_engine, mock_market_data):
        """测试风险管理拒绝交易的情况"""
        
        with patch('src.data.collectors.market_data_collector.MarketDataCollector.collect_data') as mock_collect:
            mock_collect.return_value = mock_market_data
            
            with patch('src.ai.reasoning.market_analyzer.MarketAnalyzer.analyze_market') as mock_analyze:
                mock_analyze.return_value = {'trend': 'bullish', 'confidence': 0.8}
                
                with patch('src.ai.reasoning.decision_maker.DecisionMaker.make_decision') as mock_decision:
                    mock_decision.return_value = {
                        'action': 'buy',
                        'symbol': 'BTC/USDT',
                        'quantity': 1.0,  # 过大的量
                        'price': 45000.0
                    }
                    
                    # 风险管理拒绝
                    with patch('src.risk.control.risk_manager.RiskManager.validate_order') as mock_risk:
                        mock_risk.return_value = {
                            'approved': False,
                            'reason': 'Position size too large',
                            'max_allowed': 0.1
                        }
                        
                        result = await trading_engine.process_trading_cycle()
                        
                        # 验证拒绝结果
                        assert result['status'] == 'rejected'
                        assert 'Position size too large' in result['reason']
                        assert result['alternative_action'] == 'reduce_position_size'
    
    @pytest.mark.asyncio
    async def test_system_monitoring_integration(self, trading_engine):
        """测试系统监控集成"""
        
        with patch('src.monitoring.system_monitor.SystemMonitor.get_system_metrics') as mock_metrics:
            mock_metrics.return_value = {
                'cpu_usage': 85.0,  # 高CPU使用率
                'memory_usage': 90.0,  # 高内存使用率
                'disk_usage': 70.0,
                'network_latency': 50.0
            }
            
            result = await trading_engine.check_system_health()
            
            # 验证系统健康检查
            assert result['status'] == 'warning'
            assert result['cpu_usage'] == 85.0
            assert result['memory_usage'] == 90.0
            assert 'performance_degradation' in result['warnings']
    
    @pytest.mark.asyncio
    async def test_concurrent_trading_cycles(self, trading_engine):
        """测试并发交易周期"""
        
        # 模拟多个交易对的并发处理
        symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
        
        with patch('src.data.collectors.market_data_collector.MarketDataCollector.collect_data') as mock_collect:
            mock_collect.return_value = {'symbol': 'BTC/USDT', 'price': 45000.0}
            
            # 并发执行多个交易周期
            tasks = []
            for symbol in symbols:
                task = asyncio.create_task(trading_engine.process_trading_cycle(symbol))
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 验证所有任务都成功完成
            successful_results = [r for r in results if not isinstance(r, Exception)]
            assert len(successful_results) == len(symbols)
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self, trading_engine):
        """测试高负载下的性能"""
        
        import time
        
        # 记录开始时间
        start_time = time.time()
        
        # 模拟高频交易场景
        tasks = []
        for i in range(100):
            task = asyncio.create_task(trading_engine.process_trading_cycle())
            tasks.append(task)
        
        # 执行所有任务
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 记录结束时间
        end_time = time.time()
        execution_time = end_time - start_time
        
        # 验证性能指标
        assert execution_time < 30.0  # 100个交易周期应在30秒内完成
        
        # 验证成功率
        successful_results = [r for r in results if not isinstance(r, Exception)]
        success_rate = len(successful_results) / len(results)
        assert success_rate > 0.95  # 成功率应大于95%
    
    @pytest.mark.asyncio
    async def test_database_integration(self, trading_engine):
        """测试数据库集成"""
        
        with patch('src.data.storage.data_storage.DataStorage.save_trade_record') as mock_save:
            mock_save.return_value = True
            
            with patch('src.data.storage.data_storage.DataStorage.get_trade_history') as mock_get:
                mock_get.return_value = [
                    {
                        'id': 1,
                        'symbol': 'BTC/USDT',
                        'action': 'buy',
                        'quantity': 0.05,
                        'price': 45000.0,
                        'timestamp': datetime.now().isoformat()
                    }
                ]
                
                # 测试数据保存
                trade_record = {
                    'symbol': 'BTC/USDT',
                    'action': 'buy',
                    'quantity': 0.05,
                    'price': 45000.0
                }
                
                result = await trading_engine.save_trade_record(trade_record)
                assert result is True
                
                # 测试数据检索
                history = await trading_engine.get_trade_history('BTC/USDT')
                assert len(history) == 1
                assert history[0]['symbol'] == 'BTC/USDT'
    
    @pytest.mark.asyncio
    async def test_api_integration(self, trading_engine):
        """测试API集成"""
        
        with patch('src.api.main.app') as mock_app:
            # 模拟API调用
            mock_response = {
                'status': 'success',
                'data': {
                    'positions': {'BTC/USDT': {'quantity': 0.1}},
                    'balance': 10000.0
                }
            }
            
            # 测试获取投资组合
            result = await trading_engine.get_portfolio_via_api()
            assert result['status'] == 'success'
            assert 'positions' in result['data']
    
    @pytest.mark.asyncio
    async def test_market_data_quality(self, trading_engine):
        """测试市场数据质量"""
        
        # 模拟各种数据质量问题
        test_cases = [
            {'price': None, 'expected': 'invalid_price'},
            {'price': -100, 'expected': 'negative_price'},
            {'timestamp': None, 'expected': 'missing_timestamp'},
            {'volume': 0, 'expected': 'zero_volume'},
        ]
        
        for test_case in test_cases:
            with patch('src.data.collectors.market_data_collector.MarketDataCollector.collect_data') as mock_collect:
                mock_collect.return_value = test_case
                
                result = await trading_engine.validate_market_data()
                assert result['status'] == 'error'
                assert test_case['expected'] in result['error_type']
    
    @pytest.mark.asyncio
    async def test_recovery_mechanisms(self, trading_engine):
        """测试恢复机制"""
        
        # 模拟系统故障和恢复
        with patch('src.monitoring.system_monitor.SystemMonitor.detect_failure') as mock_detect:
            mock_detect.return_value = {
                'failure_type': 'network_disconnection',
                'severity': 'high',
                'recovery_strategy': 'reconnect_with_exponential_backoff'
            }
            
            with patch('src.core.engine.trading_engine.TradingEngine.execute_recovery') as mock_recovery:
                mock_recovery.return_value = {
                    'status': 'recovered',
                    'time_to_recovery': 15.0,
                    'data_integrity': 'verified'
                }
                
                result = await trading_engine.handle_system_failure()
                
                # 验证恢复机制
                assert result['status'] == 'recovered'
                assert result['time_to_recovery'] <= 30.0
                assert result['data_integrity'] == 'verified'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])