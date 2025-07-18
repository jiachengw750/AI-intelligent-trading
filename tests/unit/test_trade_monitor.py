# -*- coding: utf-8 -*-
"""
交易监控器单元测试
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch
from src.monitoring.trade_monitor import (
    TradeMonitor, TradeExecution, PositionInfo, TradeAlert, 
    AlertLevel, TradeEventType, TradeMetrics
)


class TestTradeMonitor:
    """交易监控器测试类"""
    
    @pytest.fixture
    def trade_monitor(self):
        """创建交易监控器实例"""
        return TradeMonitor(monitoring_interval=0.1)
    
    @pytest.fixture
    def sample_execution(self):
        """创建示例交易执行"""
        return TradeExecution(
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
    
    @pytest.fixture
    def sample_position(self):
        """创建示例持仓"""
        return PositionInfo(
            symbol="BTCUSDT",
            side="LONG",
            size=1.0,
            avg_price=50000.0,
            unrealized_pnl=100.0,
            realized_pnl=50.0,
            timestamp=time.time()
        )
    
    def test_init(self, trade_monitor):
        """测试初始化"""
        assert trade_monitor.monitoring_interval == 0.1
        assert trade_monitor.is_monitoring == False
        assert len(trade_monitor.trade_executions) == 0
        assert len(trade_monitor.position_info) == 0
        assert len(trade_monitor.active_alerts) == 0
        assert trade_monitor.total_trades == 0
        assert trade_monitor.total_volume == 0.0
        assert trade_monitor.total_pnl == 0.0
    
    def test_add_callbacks(self, trade_monitor):
        """测试添加回调函数"""
        alert_callback = Mock()
        event_callback = Mock()
        
        trade_monitor.add_alert_callback(alert_callback)
        trade_monitor.add_event_callback(event_callback)
        
        assert alert_callback in trade_monitor.alert_callbacks
        assert event_callback in trade_monitor.event_callbacks
    
    @pytest.mark.asyncio
    async def test_record_trade_execution(self, trade_monitor, sample_execution):
        """测试记录交易执行"""
        await trade_monitor.record_trade_execution(sample_execution)
        
        executions = trade_monitor.trade_executions["BTCUSDT"]
        assert len(executions) == 1
        assert executions[0].execution_id == "test_exec_1"
        assert executions[0].symbol == "BTCUSDT"
        assert executions[0].amount == 1.0
        assert executions[0].price == 50000.0
        assert executions[0].pnl == 100.0
    
    @pytest.mark.asyncio
    async def test_update_position(self, trade_monitor, sample_position):
        """测试更新持仓"""
        await trade_monitor.update_position(sample_position)
        
        position = trade_monitor.position_info["BTCUSDT"]
        assert position.symbol == "BTCUSDT"
        assert position.side == "LONG"
        assert position.size == 1.0
        assert position.avg_price == 50000.0
        assert position.unrealized_pnl == 100.0
        assert position.realized_pnl == 50.0
    
    def test_calculate_trade_metrics(self, trade_monitor):
        """测试计算交易指标"""
        # 创建多个交易执行记录
        executions = [
            TradeExecution(
                execution_id=f"exec_{i}",
                symbol="BTCUSDT",
                side="BUY",
                amount=1.0,
                price=50000.0,
                execution_time=0.5,
                timestamp=time.time(),
                order_id=f"order_{i}",
                pnl=100.0 if i % 2 == 0 else -50.0,
                slippage=0.001,
                fees=25.0
            )
            for i in range(10)
        ]
        
        # 计算指标
        metrics = trade_monitor._calculate_trade_metrics("BTCUSDT", executions)
        
        assert metrics.symbol == "BTCUSDT"
        assert metrics.total_trades == 10
        assert metrics.winning_trades == 5
        assert metrics.losing_trades == 5
        assert metrics.win_rate == 50.0
        assert metrics.total_volume == 10.0
        assert metrics.total_pnl == 250.0  # 5 * 100 - 5 * 50
        assert metrics.avg_win == 100.0
        assert metrics.avg_loss == -50.0
        assert metrics.profit_factor == 2.0  # 500 / 250
    
    def test_calculate_sharpe_ratio(self, trade_monitor):
        """测试计算夏普比率"""
        # 测试空列表
        assert trade_monitor._calculate_sharpe_ratio([]) == 0.0
        
        # 测试单个值
        assert trade_monitor._calculate_sharpe_ratio([100.0]) == 0.0
        
        # 测试正常情况
        returns = [100.0, -50.0, 200.0, -100.0, 150.0]
        sharpe = trade_monitor._calculate_sharpe_ratio(returns)
        assert isinstance(sharpe, float)
        assert sharpe != 0.0
        
        # 测试零标准差
        zero_std_returns = [100.0, 100.0, 100.0, 100.0]
        assert trade_monitor._calculate_sharpe_ratio(zero_std_returns) == 0.0
    
    def test_calculate_drawdown(self, trade_monitor):
        """测试计算回撤"""
        # 测试空列表
        max_dd, current_dd = trade_monitor._calculate_drawdown("BTCUSDT", [])
        assert max_dd == 0.0
        assert current_dd == 0.0
        
        # 测试单个值
        max_dd, current_dd = trade_monitor._calculate_drawdown("BTCUSDT", [100.0])
        assert max_dd == 0.0
        assert current_dd == 0.0
        
        # 测试正常情况
        returns = [100.0, -50.0, 200.0, -100.0, 150.0]
        max_dd, current_dd = trade_monitor._calculate_drawdown("BTCUSDT", returns)
        assert isinstance(max_dd, float)
        assert isinstance(current_dd, float)
        assert max_dd >= 0.0
        assert current_dd >= 0.0
    
    def test_get_trade_metrics(self, trade_monitor):
        """测试获取交易指标"""
        # 测试空状态
        assert trade_monitor.get_trade_metrics("BTCUSDT") is None
        assert trade_monitor.get_trade_metrics() == {}
        
        # 添加指标
        metrics = TradeMetrics(timestamp=time.time(), symbol="BTCUSDT")
        trade_monitor.trade_metrics["BTCUSDT"] = metrics
        
        # 测试获取指定符号的指标
        assert trade_monitor.get_trade_metrics("BTCUSDT") == metrics
        
        # 测试获取所有指标
        all_metrics = trade_monitor.get_trade_metrics()
        assert "BTCUSDT" in all_metrics
        assert all_metrics["BTCUSDT"] == metrics
    
    def test_get_active_alerts(self, trade_monitor):
        """测试获取活跃告警"""
        # 测试空状态
        assert trade_monitor.get_active_alerts() == []
        assert trade_monitor.get_active_alerts("BTCUSDT") == []
        
        # 添加告警
        alert = TradeAlert(
            alert_id="test_alert_1",
            alert_type="test_alert",
            level=AlertLevel.HIGH,
            message="Test alert",
            symbol="BTCUSDT",
            timestamp=time.time()
        )
        trade_monitor.active_alerts["test_alert_BTCUSDT"] = alert
        
        # 测试获取所有告警
        all_alerts = trade_monitor.get_active_alerts()
        assert len(all_alerts) == 1
        assert all_alerts[0] == alert
        
        # 测试获取指定符号的告警
        symbol_alerts = trade_monitor.get_active_alerts("BTCUSDT")
        assert len(symbol_alerts) == 1
        assert symbol_alerts[0] == alert
        
        # 测试获取其他符号的告警
        other_alerts = trade_monitor.get_active_alerts("ETHUSDT")
        assert len(other_alerts) == 0
    
    def test_get_position_info(self, trade_monitor, sample_position):
        """测试获取持仓信息"""
        # 测试空状态
        assert trade_monitor.get_position_info("BTCUSDT") is None
        assert trade_monitor.get_position_info() == {}
        
        # 添加持仓
        trade_monitor.position_info["BTCUSDT"] = sample_position
        
        # 测试获取指定符号的持仓
        assert trade_monitor.get_position_info("BTCUSDT") == sample_position
        
        # 测试获取所有持仓
        all_positions = trade_monitor.get_position_info()
        assert "BTCUSDT" in all_positions
        assert all_positions["BTCUSDT"] == sample_position
    
    def test_get_trade_executions(self, trade_monitor, sample_execution):
        """测试获取交易执行记录"""
        # 测试空状态
        assert trade_monitor.get_trade_executions("BTCUSDT") == []
        
        # 添加交易执行
        trade_monitor.trade_executions["BTCUSDT"].append(sample_execution)
        
        # 测试获取交易执行
        executions = trade_monitor.get_trade_executions("BTCUSDT")
        assert len(executions) == 1
        assert executions[0] == sample_execution
        
        # 测试限制数量
        for i in range(150):
            exec_record = TradeExecution(
                execution_id=f"exec_{i}",
                symbol="BTCUSDT",
                side="BUY",
                amount=1.0,
                price=50000.0,
                execution_time=0.5,
                timestamp=time.time(),
                order_id=f"order_{i}",
                pnl=100.0,
                slippage=0.001,
                fees=25.0
            )
            trade_monitor.trade_executions["BTCUSDT"].append(exec_record)
        
        # 测试默认限制
        executions = trade_monitor.get_trade_executions("BTCUSDT")
        assert len(executions) == 100
        
        # 测试自定义限制
        executions = trade_monitor.get_trade_executions("BTCUSDT", limit=50)
        assert len(executions) == 50
    
    def test_get_performance_summary(self, trade_monitor):
        """测试获取性能摘要"""
        summary = trade_monitor.get_performance_summary()
        
        # 检查必要的字段
        required_fields = [
            "uptime", "monitoring_status", "total_symbols", "total_trades",
            "total_volume", "total_realized_pnl", "total_unrealized_pnl",
            "total_pnl", "avg_win_rate", "active_alerts", "active_positions",
            "daily_stats"
        ]
        
        for field in required_fields:
            assert field in summary
            
        # 检查数据类型
        assert isinstance(summary["uptime"], float)
        assert isinstance(summary["monitoring_status"], bool)
        assert isinstance(summary["total_symbols"], int)
        assert isinstance(summary["total_trades"], int)
        assert isinstance(summary["total_volume"], float)
        assert isinstance(summary["daily_stats"], dict)
    
    def test_get_risk_summary(self, trade_monitor):
        """测试获取风险摘要"""
        summary = trade_monitor.get_risk_summary()
        
        # 检查必要的字段
        required_fields = [
            "total_exposure", "max_drawdown", "current_drawdown",
            "active_alerts", "risk_thresholds", "performance_thresholds"
        ]
        
        for field in required_fields:
            assert field in summary
            
        # 检查数据类型
        assert isinstance(summary["total_exposure"], float)
        assert isinstance(summary["max_drawdown"], float)
        assert isinstance(summary["current_drawdown"], float)
        assert isinstance(summary["active_alerts"], int)
        assert isinstance(summary["risk_thresholds"], dict)
        assert isinstance(summary["performance_thresholds"], dict)
    
    def test_clear_alert(self, trade_monitor):
        """测试清除告警"""
        # 添加告警
        alert = TradeAlert(
            alert_id="test_alert_1",
            alert_type="test_alert",
            level=AlertLevel.HIGH,
            message="Test alert",
            symbol="BTCUSDT",
            timestamp=time.time()
        )
        alert_key = "test_alert_BTCUSDT"
        trade_monitor.active_alerts[alert_key] = alert
        
        # 确认告警存在
        assert alert_key in trade_monitor.active_alerts
        
        # 清除告警
        trade_monitor.clear_alert(alert_key)
        
        # 确认告警已清除
        assert alert_key not in trade_monitor.active_alerts
        assert alert.is_active == False
    
    def test_clear_all_alerts(self, trade_monitor):
        """测试清除所有告警"""
        # 添加多个告警
        alerts = []
        for i in range(3):
            alert = TradeAlert(
                alert_id=f"test_alert_{i}",
                alert_type="test_alert",
                level=AlertLevel.HIGH,
                message=f"Test alert {i}",
                symbol="BTCUSDT",
                timestamp=time.time()
            )
            alerts.append(alert)
            trade_monitor.active_alerts[f"test_alert_{i}_BTCUSDT"] = alert
        
        # 确认告警存在
        assert len(trade_monitor.active_alerts) == 3
        
        # 清除所有告警
        trade_monitor.clear_all_alerts()
        
        # 确认所有告警已清除
        assert len(trade_monitor.active_alerts) == 0
        for alert in alerts:
            assert alert.is_active == False
    
    def test_update_thresholds(self, trade_monitor):
        """测试更新阈值"""
        # 测试更新风险阈值
        new_risk_thresholds = {
            "max_drawdown": 0.15,
            "position_size_limit": 0.08
        }
        trade_monitor.update_risk_thresholds(new_risk_thresholds)
        
        assert trade_monitor.risk_thresholds["max_drawdown"] == 0.15
        assert trade_monitor.risk_thresholds["position_size_limit"] == 0.08
        
        # 测试更新性能阈值
        new_performance_thresholds = {
            "min_win_rate": 0.40,
            "min_profit_factor": 1.5
        }
        trade_monitor.update_performance_thresholds(new_performance_thresholds)
        
        assert trade_monitor.performance_thresholds["min_win_rate"] == 0.40
        assert trade_monitor.performance_thresholds["min_profit_factor"] == 1.5
    
    def test_reset_statistics(self, trade_monitor, sample_execution, sample_position):
        """测试重置统计信息"""
        # 添加一些数据
        trade_monitor.trade_executions["BTCUSDT"].append(sample_execution)
        trade_monitor.position_info["BTCUSDT"] = sample_position
        trade_monitor.total_trades = 10
        trade_monitor.total_volume = 100.0
        trade_monitor.total_pnl = 500.0
        
        # 重置统计信息
        trade_monitor.reset_statistics()
        
        # 验证数据已重置
        assert len(trade_monitor.trade_executions) == 0
        assert len(trade_monitor.position_info) == 0
        assert len(trade_monitor.trade_metrics) == 0
        assert trade_monitor.total_trades == 0
        assert trade_monitor.total_volume == 0.0
        assert trade_monitor.total_pnl == 0.0
        assert trade_monitor.daily_stats["trades"] == 0
        assert trade_monitor.daily_stats["volume"] == 0.0
        assert trade_monitor.daily_stats["pnl"] == 0.0
    
    @pytest.mark.asyncio
    async def test_monitoring_lifecycle(self, trade_monitor):
        """测试监控生命周期"""
        # 初始状态
        assert trade_monitor.is_monitoring == False
        
        # 启动监控
        await trade_monitor.start_monitoring()
        assert trade_monitor.is_monitoring == True
        
        # 等待一段时间让监控任务运行
        await asyncio.sleep(0.2)
        
        # 停止监控
        await trade_monitor.stop_monitoring()
        assert trade_monitor.is_monitoring == False
    
    @pytest.mark.asyncio
    async def test_alert_callback_execution(self, trade_monitor):
        """测试告警回调执行"""
        # 创建mock回调
        alert_callback = Mock()
        trade_monitor.add_alert_callback(alert_callback)
        
        # 发送告警
        await trade_monitor._send_alert(
            "test_alert", AlertLevel.HIGH, "Test message", "BTCUSDT", {}
        )
        
        # 验证回调被调用
        assert alert_callback.called
        
        # 获取调用参数
        call_args = alert_callback.call_args[0]
        alert = call_args[0]
        assert isinstance(alert, TradeAlert)
        assert alert.alert_type == "test_alert"
        assert alert.level == AlertLevel.HIGH
        assert alert.message == "Test message"
        assert alert.symbol == "BTCUSDT"