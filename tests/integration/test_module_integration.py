#!/usr/bin/env python3
"""
模块集成测试
测试各个模块之间的集成和协作
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, List, Any

# 导入各个模块
from src.data.collectors.market_data_collector import MarketDataCollector
from src.data.processors.market_processor import MarketProcessor
from src.ai.models.model_manager import ModelManager
from src.ai.reasoning.market_analyzer import MarketAnalyzer
from src.ai.reasoning.decision_maker import DecisionMaker
from src.trading.orders.order_manager import OrderManager
from src.trading.portfolio.portfolio_manager import PortfolioManager
from src.risk.control.risk_manager import RiskManager
from src.monitoring.system_monitor import SystemMonitor
from src.data.storage.data_storage import DataStorage


class TestModuleIntegration:
    """模块集成测试"""
    
    @pytest.fixture
    def sample_market_data(self):
        """示例市场数据"""
        return {
            'symbol': 'BTC/USDT',
            'timestamp': datetime.now().isoformat(),
            'price': 45000.0,
            'volume': 1000.0,
            'high': 45500.0,
            'low': 44500.0,
            'open': 44800.0,
            'close': 45000.0,
            'bid': 44950.0,
            'ask': 45050.0
        }
    
    @pytest.fixture
    def sample_portfolio(self):
        """示例投资组合"""
        return {
            'cash_balance': 10000.0,
            'positions': {
                'BTC/USDT': {
                    'quantity': 0.1,
                    'average_price': 44000.0,
                    'current_price': 45000.0,
                    'unrealized_pnl': 100.0,
                    'realized_pnl': 0.0
                }
            },
            'total_value': 14500.0,
            'total_pnl': 100.0
        }
    
    @pytest.mark.asyncio
    async def test_data_collection_and_processing_integration(self, sample_market_data):
        """测试数据收集和处理模块的集成"""
        
        # 创建模块实例
        collector = MarketDataCollector()
        processor = MarketProcessor()
        
        # 模拟数据收集
        with patch.object(collector, 'collect_data', return_value=sample_market_data) as mock_collect:
            # 模拟数据处理
            with patch.object(processor, 'process_data') as mock_process:
                processed_data = {
                    **sample_market_data,
                    'indicators': {
                        'sma_20': 44500.0,
                        'rsi': 65.0,
                        'macd': 0.15,
                        'bollinger_upper': 45200.0,
                        'bollinger_lower': 44300.0
                    }
                }
                mock_process.return_value = processed_data
                
                # 执行数据收集和处理流程
                raw_data = await collector.collect_data('BTC/USDT')
                processed_result = await processor.process_data(raw_data)
                
                # 验证集成结果
                assert processed_result['symbol'] == 'BTC/USDT'
                assert processed_result['price'] == 45000.0
                assert 'indicators' in processed_result
                assert processed_result['indicators']['rsi'] == 65.0
                
                # 验证调用序列
                mock_collect.assert_called_once_with('BTC/USDT')
                mock_process.assert_called_once_with(raw_data)
    
    @pytest.mark.asyncio
    async def test_ai_analysis_integration(self, sample_market_data):
        """测试AI分析模块的集成"""
        
        # 创建AI模块实例
        model_manager = ModelManager()
        market_analyzer = MarketAnalyzer(model_manager)
        decision_maker = DecisionMaker(model_manager)
        
        # 模拟市场分析
        with patch.object(market_analyzer, 'analyze_market') as mock_analyze:
            analysis_result = {
                'trend': 'bullish',
                'confidence': 0.75,
                'support_levels': [44000.0, 43500.0],
                'resistance_levels': [45500.0, 46000.0],
                'indicators': {
                    'rsi': 65.0,
                    'macd_signal': 'buy',
                    'bollinger_position': 'upper'
                }
            }
            mock_analyze.return_value = analysis_result
            
            # 模拟决策制定
            with patch.object(decision_maker, 'make_decision') as mock_decision:
                decision_result = {
                    'action': 'buy',
                    'symbol': 'BTC/USDT',
                    'quantity': 0.05,
                    'price': 45000.0,
                    'confidence': 0.8,
                    'reasoning': 'Bullish trend with strong indicators'
                }
                mock_decision.return_value = decision_result
                
                # 执行AI分析流程
                analysis = await market_analyzer.analyze_market(sample_market_data)
                decision = await decision_maker.make_decision(analysis, sample_market_data)
                
                # 验证集成结果
                assert decision['action'] == 'buy'
                assert decision['symbol'] == 'BTC/USDT'
                assert decision['confidence'] == 0.8
                
                # 验证分析结果传递给决策器
                mock_analyze.assert_called_once_with(sample_market_data)
                mock_decision.assert_called_once_with(analysis, sample_market_data)
    
    @pytest.mark.asyncio
    async def test_risk_management_integration(self, sample_portfolio):
        """测试风险管理模块的集成"""
        
        # 创建风险管理模块实例
        risk_manager = RiskManager()
        portfolio_manager = PortfolioManager()
        
        # 模拟投资组合状态
        with patch.object(portfolio_manager, 'get_portfolio', return_value=sample_portfolio):
            # 模拟风险评估
            with patch.object(risk_manager, 'assess_risk') as mock_assess:
                risk_assessment = {
                    'total_risk_score': 0.3,
                    'position_risk': 0.25,
                    'portfolio_risk': 0.2,
                    'market_risk': 0.35,
                    'max_position_size': 0.1,
                    'recommended_stop_loss': 0.05
                }
                mock_assess.return_value = risk_assessment
                
                # 模拟订单验证
                with patch.object(risk_manager, 'validate_order') as mock_validate:
                    order_validation = {
                        'approved': True,
                        'adjusted_quantity': 0.05,
                        'risk_score': 0.3,
                        'warnings': ['Position concentration high']
                    }
                    mock_validate.return_value = order_validation
                    
                    # 执行风险管理流程
                    test_order = {
                        'symbol': 'BTC/USDT',
                        'action': 'buy',
                        'quantity': 0.08,
                        'price': 45000.0
                    }
                    
                    portfolio = await portfolio_manager.get_portfolio()
                    risk_assessment = await risk_manager.assess_risk(portfolio)
                    validation = await risk_manager.validate_order(test_order, risk_assessment)
                    
                    # 验证风险管理结果
                    assert validation['approved'] is True
                    assert validation['adjusted_quantity'] == 0.05
                    assert risk_assessment['total_risk_score'] == 0.3
    
    @pytest.mark.asyncio
    async def test_trading_execution_integration(self, sample_portfolio):
        """测试交易执行模块的集成"""
        
        # 创建交易执行模块实例
        order_manager = OrderManager()
        portfolio_manager = PortfolioManager()
        
        # 模拟订单创建
        with patch.object(order_manager, 'create_order') as mock_create:
            order_result = {
                'order_id': 'ORDER_123',
                'symbol': 'BTC/USDT',
                'action': 'buy',
                'quantity': 0.05,
                'price': 45000.0,
                'status': 'pending',
                'timestamp': datetime.now().isoformat()
            }
            mock_create.return_value = order_result
            
            # 模拟订单执行
            with patch.object(order_manager, 'execute_order') as mock_execute:
                execution_result = {
                    'order_id': 'ORDER_123',
                    'status': 'filled',
                    'executed_price': 45000.0,
                    'executed_quantity': 0.05,
                    'fees': 2.25,
                    'timestamp': datetime.now().isoformat()
                }
                mock_execute.return_value = execution_result
                
                # 模拟投资组合更新
                with patch.object(portfolio_manager, 'update_portfolio') as mock_update:
                    updated_portfolio = {
                        **sample_portfolio,
                        'cash_balance': 7747.75,  # 减去购买金额和费用
                        'positions': {
                            'BTC/USDT': {
                                'quantity': 0.15,  # 增加持仓
                                'average_price': 44333.33,
                                'current_price': 45000.0,
                                'unrealized_pnl': 100.0
                            }
                        }
                    }
                    mock_update.return_value = updated_portfolio
                    
                    # 执行交易执行流程
                    order_request = {
                        'symbol': 'BTC/USDT',
                        'action': 'buy',
                        'quantity': 0.05,
                        'price': 45000.0
                    }
                    
                    order = await order_manager.create_order(order_request)
                    execution = await order_manager.execute_order(order['order_id'])
                    updated_portfolio = await portfolio_manager.update_portfolio(execution)
                    
                    # 验证交易执行结果
                    assert execution['status'] == 'filled'
                    assert execution['executed_quantity'] == 0.05
                    assert updated_portfolio['positions']['BTC/USDT']['quantity'] == 0.15
    
    @pytest.mark.asyncio
    async def test_monitoring_integration(self):
        """测试监控模块的集成"""
        
        # 创建监控模块实例
        system_monitor = SystemMonitor()
        data_storage = DataStorage()
        
        # 模拟系统指标收集
        with patch.object(system_monitor, 'collect_metrics') as mock_collect:
            metrics = {
                'cpu_usage': 75.0,
                'memory_usage': 80.0,
                'disk_usage': 60.0,
                'network_latency': 25.0,
                'active_connections': 15,
                'timestamp': datetime.now().isoformat()
            }
            mock_collect.return_value = metrics
            
            # 模拟数据存储
            with patch.object(data_storage, 'save_metrics') as mock_save:
                mock_save.return_value = True
                
                # 模拟告警检查
                with patch.object(system_monitor, 'check_alerts') as mock_alerts:
                    alerts = [
                        {
                            'type': 'warning',
                            'message': 'High CPU usage detected',
                            'value': 75.0,
                            'threshold': 70.0,
                            'timestamp': datetime.now().isoformat()
                        }
                    ]
                    mock_alerts.return_value = alerts
                    
                    # 执行监控流程
                    collected_metrics = await system_monitor.collect_metrics()
                    save_result = await data_storage.save_metrics(collected_metrics)
                    triggered_alerts = await system_monitor.check_alerts(collected_metrics)
                    
                    # 验证监控集成结果
                    assert collected_metrics['cpu_usage'] == 75.0
                    assert save_result is True
                    assert len(triggered_alerts) == 1
                    assert triggered_alerts[0]['type'] == 'warning'
    
    @pytest.mark.asyncio
    async def test_data_storage_integration(self, sample_market_data):
        """测试数据存储模块的集成"""
        
        # 创建数据存储实例
        data_storage = DataStorage()
        
        # 模拟数据保存
        with patch.object(data_storage, 'save_market_data') as mock_save_market:
            mock_save_market.return_value = True
            
            # 模拟交易记录保存
            with patch.object(data_storage, 'save_trade_record') as mock_save_trade:
                mock_save_trade.return_value = True
                
                # 模拟数据查询
                with patch.object(data_storage, 'get_historical_data') as mock_get_history:
                    historical_data = [
                        {**sample_market_data, 'timestamp': (datetime.now() - timedelta(minutes=i)).isoformat()}
                        for i in range(5)
                    ]
                    mock_get_history.return_value = historical_data
                    
                    # 执行数据存储流程
                    market_save_result = await data_storage.save_market_data(sample_market_data)
                    
                    trade_record = {
                        'symbol': 'BTC/USDT',
                        'action': 'buy',
                        'quantity': 0.05,
                        'price': 45000.0,
                        'timestamp': datetime.now().isoformat()
                    }
                    trade_save_result = await data_storage.save_trade_record(trade_record)
                    
                    history = await data_storage.get_historical_data('BTC/USDT', limit=5)
                    
                    # 验证数据存储集成结果
                    assert market_save_result is True
                    assert trade_save_result is True
                    assert len(history) == 5
                    assert all(item['symbol'] == 'BTC/USDT' for item in history)
    
    @pytest.mark.asyncio
    async def test_cross_module_event_flow(self):
        """测试跨模块事件流"""
        
        # 创建所有相关模块实例
        collector = MarketDataCollector()
        processor = MarketProcessor()
        analyzer = MarketAnalyzer(ModelManager())
        decision_maker = DecisionMaker(ModelManager())
        risk_manager = RiskManager()
        order_manager = OrderManager()
        portfolio_manager = PortfolioManager()
        system_monitor = SystemMonitor()
        
        # 模拟完整的事件流
        market_data = {
            'symbol': 'BTC/USDT',
            'price': 45000.0,
            'volume': 1000.0,
            'timestamp': datetime.now().isoformat()
        }
        
        # 1. 数据收集 -> 处理
        with patch.object(collector, 'collect_data', return_value=market_data):
            with patch.object(processor, 'process_data', return_value={**market_data, 'indicators': {'rsi': 65}}):
                
                # 2. 处理 -> 分析
                with patch.object(analyzer, 'analyze_market', return_value={'trend': 'bullish', 'confidence': 0.8}):
                    
                    # 3. 分析 -> 决策
                    with patch.object(decision_maker, 'make_decision', return_value={'action': 'buy', 'quantity': 0.05}):
                        
                        # 4. 决策 -> 风险管理
                        with patch.object(risk_manager, 'validate_order', return_value={'approved': True}):
                            
                            # 5. 风险管理 -> 订单执行
                            with patch.object(order_manager, 'execute_order', return_value={'status': 'filled'}):
                                
                                # 6. 执行 -> 投资组合更新
                                with patch.object(portfolio_manager, 'update_portfolio', return_value={'updated': True}):
                                    
                                    # 7. 全程监控
                                    with patch.object(system_monitor, 'log_event', return_value=True):
                                        
                                        # 执行完整流程
                                        raw_data = await collector.collect_data('BTC/USDT')
                                        processed_data = await processor.process_data(raw_data)
                                        analysis = await analyzer.analyze_market(processed_data)
                                        decision = await decision_maker.make_decision(analysis, processed_data)
                                        risk_check = await risk_manager.validate_order(decision)
                                        
                                        if risk_check['approved']:
                                            execution = await order_manager.execute_order(decision)
                                            portfolio_update = await portfolio_manager.update_portfolio(execution)
                                            await system_monitor.log_event('trade_completed', execution)
                                        
                                        # 验证完整流程
                                        assert raw_data['symbol'] == 'BTC/USDT'
                                        assert 'indicators' in processed_data
                                        assert analysis['trend'] == 'bullish'
                                        assert decision['action'] == 'buy'
                                        assert risk_check['approved'] is True
                                        assert execution['status'] == 'filled'
                                        assert portfolio_update['updated'] is True
    
    @pytest.mark.asyncio
    async def test_error_propagation_across_modules(self):
        """测试错误在模块间的传播"""
        
        collector = MarketDataCollector()
        processor = MarketProcessor()
        analyzer = MarketAnalyzer(ModelManager())
        
        # 模拟数据收集失败
        with patch.object(collector, 'collect_data', side_effect=Exception("Data source unavailable")):
            
            # 模拟处理器的错误处理
            with patch.object(processor, 'handle_error') as mock_handle:
                mock_handle.return_value = {
                    'error_type': 'data_collection_failure',
                    'recovery_action': 'use_cached_data',
                    'fallback_data': {'symbol': 'BTC/USDT', 'price': 44000.0}
                }
                
                # 模拟分析器的错误处理
                with patch.object(analyzer, 'analyze_market') as mock_analyze:
                    mock_analyze.return_value = {
                        'trend': 'uncertain',
                        'confidence': 0.1,
                        'error_adjusted': True
                    }
                    
                    try:
                        # 尝试数据收集
                        await collector.collect_data('BTC/USDT')
                    except Exception as e:
                        # 处理错误
                        error_response = await processor.handle_error(e)
                        
                        # 使用回退数据进行分析
                        analysis = await analyzer.analyze_market(error_response['fallback_data'])
                        
                        # 验证错误处理
                        assert error_response['error_type'] == 'data_collection_failure'
                        assert analysis['error_adjusted'] is True
                        assert analysis['confidence'] == 0.1
    
    @pytest.mark.asyncio
    async def test_performance_across_modules(self):
        """测试跨模块性能"""
        
        import time
        
        # 创建轻量级模块实例
        modules = {
            'collector': MarketDataCollector(),
            'processor': MarketProcessor(),
            'analyzer': MarketAnalyzer(ModelManager()),
            'decision_maker': DecisionMaker(ModelManager()),
            'risk_manager': RiskManager(),
            'order_manager': OrderManager()
        }
        
        # 测试各模块的响应时间
        performance_results = {}
        
        for module_name, module in modules.items():
            start_time = time.time()
            
            # 模拟模块操作
            if hasattr(module, 'process_data'):
                with patch.object(module, 'process_data', return_value={'processed': True}):
                    await module.process_data({'test': 'data'})
            elif hasattr(module, 'collect_data'):
                with patch.object(module, 'collect_data', return_value={'collected': True}):
                    await module.collect_data('BTC/USDT')
            elif hasattr(module, 'analyze_market'):
                with patch.object(module, 'analyze_market', return_value={'analyzed': True}):
                    await module.analyze_market({'test': 'data'})
            
            end_time = time.time()
            performance_results[module_name] = end_time - start_time
        
        # 验证性能要求
        for module_name, execution_time in performance_results.items():
            assert execution_time < 1.0, f"{module_name} took {execution_time:.2f}s, should be < 1.0s"
        
        # 验证总体性能
        total_time = sum(performance_results.values())
        assert total_time < 5.0, f"Total module execution time {total_time:.2f}s should be < 5.0s"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])