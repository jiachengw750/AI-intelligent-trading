# -*- coding: utf-8 -*-
"""
交易监控器集成测试
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from src.monitoring.trade_monitor import TradeMonitor, TradeExecution, PositionInfo, AlertLevel
from src.monitoring.performance_monitor import PerformanceMonitor
from src.trading.orders.order_manager import OrderManager, OrderEvent


class TestTradeMonitorIntegration:
    """交易监控器集成测试类"""
    
    @pytest.fixture
    def trade_monitor(self):
        """创建交易监控器实例"""
        return TradeMonitor(monitoring_interval=0.1)
    
    @pytest.fixture
    def performance_monitor(self):
        """创建性能监控器实例"""
        return PerformanceMonitor(collection_interval=0.1)
    
    @pytest.fixture
    def order_manager(self):
        """创建订单管理器实例"""
        return OrderManager()
    
    @pytest.mark.asyncio
    async def test_trade_monitor_with_performance_monitor(self, trade_monitor, performance_monitor):
        """测试交易监控器与性能监控器的集成"""
        # 启动监控器
        await trade_monitor.start_monitoring()
        await performance_monitor.start_monitoring()
        
        # 创建测试数据
        execution = TradeExecution(
            execution_id="test_exec_1",
            symbol="BTCUSDT",
            side="BUY",
            amount=1.0,
            price=50000.0,
            execution_time=0.5,
            timestamp=time.time(),
            order_id="test_order_1",
            pnl=100.0,
            slippage=0.001,
            fees=25.0
        )
        
        # 记录交易执行到交易监控器
        await trade_monitor.record_trade_execution(execution)
        
        # 记录执行时间到性能监控器
        performance_monitor.record_trade_execution(
            execution_time=execution.execution_time,
            success=True,
            pnl=execution.pnl
        )
        
        # 等待监控器处理
        await asyncio.sleep(0.2)
        
        # 验证交易监控器数据
        executions = trade_monitor.get_trade_executions("BTCUSDT")
        assert len(executions) == 1
        assert executions[0].execution_id == "test_exec_1"
        
        # 验证性能监控器数据
        perf_summary = performance_monitor.get_performance_summary()
        assert perf_summary["total_trades"] == 1
        assert perf_summary["successful_trades"] == 1
        assert perf_summary["total_pnl"] == 100.0
        
        # 停止监控器
        await trade_monitor.stop_monitoring()
        await performance_monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_trade_monitor_with_order_events(self, trade_monitor):
        """测试交易监控器处理订单事件"""
        # 创建事件回调来模拟订单事件处理
        event_callback = Mock()
        trade_monitor.add_event_callback(event_callback)
        
        # 启动监控器
        await trade_monitor.start_monitoring()
        
        # 模拟订单成交事件
        order_event = OrderEvent(
            event_type="order_filled",
            order_id="test_order_1",
            symbol="BTCUSDT",
            timestamp=time.time(),
            data={
                "side": "BUY",
                "amount": 1.0,
                "price": 50000.0,
                "filled_amount": 1.0,
                "avg_price": 50000.0
            }
        )
        
        # 基于订单事件创建交易执行记录
        execution = TradeExecution(
            execution_id=f"exec_{order_event.order_id}",
            symbol=order_event.symbol,
            side=order_event.data["side"],
            amount=order_event.data["amount"],
            price=order_event.data["price"],
            execution_time=0.5,
            timestamp=order_event.timestamp,
            order_id=order_event.order_id,
            pnl=100.0,
            slippage=0.001,
            fees=25.0
        )
        
        # 记录交易执行
        await trade_monitor.record_trade_execution(execution)
        
        # 等待事件处理
        await asyncio.sleep(0.2)
        
        # 验证事件回调被调用
        assert event_callback.called
        
        # 验证交易记录
        executions = trade_monitor.get_trade_executions("BTCUSDT")
        assert len(executions) == 1
        assert executions[0].order_id == "test_order_1"
        
        # 停止监控器
        await trade_monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_alert_system_integration(self, trade_monitor):
        """测试告警系统集成"""
        # 创建告警处理器
        alert_handler = Mock()
        trade_monitor.add_alert_callback(alert_handler)
        
        # 设置低风险阈值以触发告警
        trade_monitor.update_risk_thresholds({
            "max_drawdown": 0.01,  # 1%
            "execution_time_limit": 0.1  # 0.1秒
        })
        
        # 启动监控器
        await trade_monitor.start_monitoring()
        
        # 创建会触发告警的交易执行
        executions = []
        for i in range(10):
            execution = TradeExecution(
                execution_id=f"exec_{i}",
                symbol="BTCUSDT",
                side="BUY",
                amount=1.0,
                price=50000.0,
                execution_time=0.5,  # 超过阈值
                timestamp=time.time(),
                order_id=f"order_{i}",
                pnl=-100.0,  # 亏损，会导致回撤
                slippage=0.001,
                fees=25.0
            )
            executions.append(execution)
            await trade_monitor.record_trade_execution(execution)
        
        # 等待监控器处理并触发告警
        await asyncio.sleep(0.5)
        
        # 验证告警被触发
        assert alert_handler.called
        
        # 检查活跃告警
        active_alerts = trade_monitor.get_active_alerts()
        assert len(active_alerts) > 0
        
        # 验证告警类型
        alert_types = [alert.alert_type for alert in active_alerts]
        assert any("drawdown" in alert_type or "execution" in alert_type for alert_type in alert_types)
        
        # 停止监控器
        await trade_monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_real_time_monitoring_workflow(self, trade_monitor):
        """测试实时监控工作流程"""
        # 创建数据收集器
        collected_data = []
        
        def data_collector(data):
            collected_data.append(data)
        
        # 添加回调
        trade_monitor.add_event_callback(data_collector)
        
        # 启动监控器
        await trade_monitor.start_monitoring()
        
        # 模拟实时交易流程
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
        
        for i in range(15):
            symbol = symbols[i % len(symbols)]
            
            # 创建交易执行
            execution = TradeExecution(
                execution_id=f"exec_{i}",
                symbol=symbol,
                side="BUY" if i % 2 == 0 else "SELL",
                amount=1.0 + i * 0.1,
                price=50000.0 + i * 100,
                execution_time=0.1 + i * 0.01,
                timestamp=time.time(),
                order_id=f"order_{i}",
                pnl=100.0 - i * 10,
                slippage=0.001,
                fees=25.0 + i
            )
            
            # 记录交易执行
            await trade_monitor.record_trade_execution(execution)
            
            # 创建持仓信息
            position = PositionInfo(
                symbol=symbol,
                side="LONG" if i % 2 == 0 else "SHORT",
                size=1.0 + i * 0.1,
                avg_price=50000.0 + i * 100,
                unrealized_pnl=50.0 - i * 5,
                realized_pnl=100.0 - i * 10,
                timestamp=time.time()
            )
            
            # 更新持仓
            await trade_monitor.update_position(position)
            
            # 短暂等待
            await asyncio.sleep(0.05)
        
        # 等待监控器处理
        await asyncio.sleep(0.3)
        
        # 验证数据收集
        assert len(collected_data) > 0
        
        # 验证交易指标
        for symbol in symbols:
            metrics = trade_monitor.get_trade_metrics(symbol)
            if metrics:
                assert metrics.total_trades > 0
                assert metrics.total_volume > 0
                assert isinstance(metrics.win_rate, float)
                assert isinstance(metrics.sharpe_ratio, float)
        
        # 验证性能摘要
        summary = trade_monitor.get_performance_summary()
        assert summary["total_trades"] == 15
        assert summary["total_symbols"] == 3
        assert summary["monitoring_status"] == True
        
        # 验证风险摘要
        risk_summary = trade_monitor.get_risk_summary()
        assert isinstance(risk_summary["total_exposure"], float)
        assert isinstance(risk_summary["max_drawdown"], float)
        
        # 停止监控器
        await trade_monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_multi_symbol_monitoring(self, trade_monitor):
        """测试多符号监控"""
        # 启动监控器
        await trade_monitor.start_monitoring()
        
        # 创建多个符号的交易数据
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "DOTUSDT"]
        
        for symbol in symbols:
            for i in range(5):
                execution = TradeExecution(
                    execution_id=f"{symbol}_exec_{i}",
                    symbol=symbol,
                    side="BUY" if i % 2 == 0 else "SELL",
                    amount=1.0 + i * 0.1,
                    price=1000.0 + i * 100,
                    execution_time=0.1 + i * 0.01,
                    timestamp=time.time(),
                    order_id=f"{symbol}_order_{i}",
                    pnl=100.0 - i * 20,
                    slippage=0.001,
                    fees=5.0 + i
                )
                
                await trade_monitor.record_trade_execution(execution)
                
                # 创建持仓
                position = PositionInfo(
                    symbol=symbol,
                    side="LONG" if i % 2 == 0 else "SHORT",
                    size=1.0 + i * 0.1,
                    avg_price=1000.0 + i * 100,
                    unrealized_pnl=50.0 - i * 10,
                    realized_pnl=100.0 - i * 20,
                    timestamp=time.time()
                )
                
                await trade_monitor.update_position(position)
        
        # 等待监控器处理
        await asyncio.sleep(0.3)
        
        # 验证每个符号的数据
        for symbol in symbols:
            executions = trade_monitor.get_trade_executions(symbol)
            assert len(executions) == 5
            
            metrics = trade_monitor.get_trade_metrics(symbol)
            assert metrics is not None
            assert metrics.symbol == symbol
            assert metrics.total_trades == 5
            
            position = trade_monitor.get_position_info(symbol)
            assert position is not None
            assert position.symbol == symbol
        
        # 验证整体统计
        summary = trade_monitor.get_performance_summary()
        assert summary["total_trades"] == 25  # 5 symbols * 5 trades
        assert summary["total_symbols"] == 5
        
        # 停止监控器
        await trade_monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, trade_monitor):
        """测试错误处理和恢复"""
        # 创建会抛出异常的回调
        error_callback = Mock(side_effect=Exception("Test error"))
        trade_monitor.add_event_callback(error_callback)
        
        # 添加正常的回调
        normal_callback = Mock()
        trade_monitor.add_event_callback(normal_callback)
        
        # 启动监控器
        await trade_monitor.start_monitoring()
        
        # 创建交易执行
        execution = TradeExecution(
            execution_id="test_exec_1",
            symbol="BTCUSDT",
            side="BUY",
            amount=1.0,
            price=50000.0,
            execution_time=0.5,
            timestamp=time.time(),
            order_id="test_order_1",
            pnl=100.0,
            slippage=0.001,
            fees=25.0
        )
        
        # 记录交易执行（应该不会因为错误回调而失败）
        await trade_monitor.record_trade_execution(execution)
        
        # 等待处理
        await asyncio.sleep(0.2)
        
        # 验证错误回调被调用了
        assert error_callback.called
        
        # 验证正常回调也被调用了（错误不应该影响其他回调）
        assert normal_callback.called
        
        # 验证交易记录仍然正常
        executions = trade_monitor.get_trade_executions("BTCUSDT")
        assert len(executions) == 1
        assert executions[0].execution_id == "test_exec_1"
        
        # 验证监控器仍在运行
        assert trade_monitor.is_monitoring == True
        
        # 停止监控器
        await trade_monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self, trade_monitor):
        """测试高负载下的性能"""
        # 启动监控器
        await trade_monitor.start_monitoring()
        
        # 记录开始时间
        start_time = time.time()
        
        # 创建大量交易数据
        tasks = []
        for i in range(100):
            execution = TradeExecution(
                execution_id=f"exec_{i}",
                symbol="BTCUSDT",
                side="BUY" if i % 2 == 0 else "SELL",
                amount=1.0,
                price=50000.0 + i,
                execution_time=0.1,
                timestamp=time.time(),
                order_id=f"order_{i}",
                pnl=100.0 - i,
                slippage=0.001,
                fees=25.0
            )
            
            task = trade_monitor.record_trade_execution(execution)
            tasks.append(task)
        
        # 等待所有任务完成
        await asyncio.gather(*tasks)
        
        # 记录结束时间
        end_time = time.time()
        processing_time = end_time - start_time
        
        # 验证性能（应该在合理时间内完成）
        assert processing_time < 5.0  # 5秒内完成
        
        # 验证数据完整性
        executions = trade_monitor.get_trade_executions("BTCUSDT")
        assert len(executions) == 100
        
        # 验证指标计算
        metrics = trade_monitor.get_trade_metrics("BTCUSDT")
        assert metrics is not None
        assert metrics.total_trades == 100
        
        # 停止监控器
        await trade_monitor.stop_monitoring()
        
        print(f"处理100个交易记录耗时: {processing_time:.2f}秒")