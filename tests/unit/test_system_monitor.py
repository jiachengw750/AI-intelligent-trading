#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统监控器单元测试
"""

import unittest
import time
import tempfile
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.monitoring.system_monitor import (
    SystemMonitor, SystemStatus, ComponentType, AlertLevel,
    SystemMetrics, ComponentStatus, SystemAlert, HealthCheckResult
)


class TestSystemMonitor(unittest.TestCase):
    """系统监控器测试类"""
    
    def setUp(self):
        """测试前设置"""
        self.monitor = SystemMonitor(
            check_interval=1,
            metrics_retention_days=1,
            alert_retention_days=1
        )
        
        # 创建模拟健康检查函数
        self.mock_health_check = Mock()
        self.mock_health_check.return_value = HealthCheckResult(
            component="test_component",
            status=SystemStatus.HEALTHY,
            message="测试正常"
        )
        
        # 创建模拟通知处理器
        self.mock_notification_handler = Mock()
        
        # 创建模拟恢复处理器
        self.mock_recovery_handler = Mock()
        self.mock_recovery_handler.return_value = True
    
    def tearDown(self):
        """测试后清理"""
        if self.monitor.is_running:
            self.monitor.stop()
    
    def test_init(self):
        """测试初始化"""
        self.assertIsNotNone(self.monitor)
        self.assertFalse(self.monitor.is_running)
        self.assertEqual(self.monitor.check_interval, 1)
        self.assertEqual(self.monitor.metrics_retention_days, 1)
        self.assertEqual(self.monitor.alert_retention_days, 1)
    
    def test_register_health_check(self):
        """测试注册健康检查"""
        self.monitor.register_health_check("test_component", self.mock_health_check)
        
        self.assertIn("test_component", self.monitor.health_checks)
        self.assertEqual(self.monitor.health_checks["test_component"], self.mock_health_check)
    
    def test_register_notification_handler(self):
        """测试注册通知处理器"""
        self.monitor.register_notification_handler(self.mock_notification_handler)
        
        self.assertIn(self.mock_notification_handler, self.monitor.notification_handlers)
    
    def test_register_recovery_handler(self):
        """测试注册恢复处理器"""
        self.monitor.register_recovery_handler("test_component", self.mock_recovery_handler)
        
        self.assertIn("test_component", self.monitor.recovery_handlers)
        self.assertEqual(self.monitor.recovery_handlers["test_component"], self.mock_recovery_handler)
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.net_io_counters')
    @patch('psutil.pids')
    @patch('psutil.boot_time')
    @patch('psutil.getloadavg')
    def test_collect_system_metrics(self, mock_loadavg, mock_boot_time, mock_pids, 
                                  mock_net_io, mock_disk, mock_memory, mock_cpu):
        """测试收集系统指标"""
        # 设置模拟返回值
        mock_cpu.return_value = 50.0
        mock_memory.return_value = Mock(percent=60.0, available=4000000000, 
                                      total=8000000000, used=4000000000)
        mock_disk.return_value = Mock(percent=70.0, free=100000000000, 
                                    total=200000000000, used=100000000000)
        mock_net_io.return_value = Mock(bytes_sent=1000000, bytes_recv=2000000,
                                      packets_sent=1000, packets_recv=2000)
        mock_pids.return_value = [1, 2, 3, 4, 5]
        mock_boot_time.return_value = time.time() - 3600  # 1小时前启动
        mock_loadavg.return_value = (0.5, 0.8, 1.0)
        
        # 执行收集
        self.monitor._collect_system_metrics()
        
        # 验证指标已收集
        self.assertEqual(len(self.monitor.metrics_history), 1)
        
        metrics = self.monitor.metrics_history[0]
        self.assertEqual(metrics.cpu_usage, 50.0)
        self.assertEqual(metrics.memory_usage, 60.0)
        self.assertEqual(metrics.disk_usage, 70.0)
        self.assertEqual(metrics.process_count, 5)
    
    def test_run_health_checks(self):
        """测试执行健康检查"""
        # 注册健康检查
        self.monitor.register_health_check("test_component", self.mock_health_check)
        
        # 执行健康检查
        self.monitor._run_health_checks()
        
        # 验证健康检查被调用
        self.mock_health_check.assert_called_once()
        
        # 验证组件状态已更新
        self.assertIn("test_component", self.monitor.component_statuses)
        status = self.monitor.component_statuses["test_component"]
        self.assertEqual(status.status, SystemStatus.HEALTHY)
    
    def test_health_check_failure(self):
        """测试健康检查失败"""
        # 模拟健康检查抛出异常
        self.mock_health_check.side_effect = Exception("健康检查失败")
        
        self.monitor.register_health_check("test_component", self.mock_health_check)
        self.monitor._run_health_checks()
        
        # 验证组件状态为CRITICAL
        status = self.monitor.component_statuses["test_component"]
        self.assertEqual(status.status, SystemStatus.CRITICAL)
        self.assertIn("健康检查失败", status.error_message)
    
    def test_create_alert(self):
        """测试创建告警"""
        # 注册通知处理器
        self.monitor.register_notification_handler(self.mock_notification_handler)
        
        # 创建告警
        self.monitor._create_alert(
            AlertLevel.WARNING,
            "test_component",
            "测试告警",
            {"test_key": "test_value"}
        )
        
        # 验证告警已创建
        self.assertEqual(len(self.monitor.alerts), 1)
        alert = self.monitor.alerts[0]
        self.assertEqual(alert.level, AlertLevel.WARNING)
        self.assertEqual(alert.component, "test_component")
        self.assertEqual(alert.message, "测试告警")
        
        # 验证通知处理器被调用
        self.mock_notification_handler.assert_called_once()
    
    def test_duplicate_alert_prevention(self):
        """测试重复告警防止"""
        # 注册通知处理器
        self.monitor.register_notification_handler(self.mock_notification_handler)
        
        # 创建两个相同的告警
        for _ in range(2):
            self.monitor._create_alert(
                AlertLevel.WARNING,
                "test_component",
                "测试告警"
            )
        
        # 验证只创建了一个告警
        self.assertEqual(len(self.monitor.alerts), 1)
        # 验证通知处理器只被调用一次
        self.assertEqual(self.mock_notification_handler.call_count, 1)
    
    def test_auto_recovery(self):
        """测试自动恢复"""
        # 注册恢复处理器
        self.monitor.register_recovery_handler("test_component", self.mock_recovery_handler)
        
        # 创建告警
        self.monitor._create_alert(
            AlertLevel.CRITICAL,
            "test_component",
            "测试告警"
        )
        
        # 验证恢复处理器被调用
        self.mock_recovery_handler.assert_called_once()
        
        # 验证告警被解决
        alert = self.monitor.alerts[0]
        self.assertTrue(alert.resolved)
    
    def test_get_system_status(self):
        """测试获取系统状态"""
        # 没有组件时应该返回UNKNOWN
        self.assertEqual(self.monitor.get_system_status(), SystemStatus.UNKNOWN)
        
        # 添加健康组件
        self.monitor.component_statuses["component1"] = ComponentStatus(
            name="component1",
            component_type=ComponentType.API,
            status=SystemStatus.HEALTHY
        )
        self.assertEqual(self.monitor.get_system_status(), SystemStatus.HEALTHY)
        
        # 添加警告组件
        self.monitor.component_statuses["component2"] = ComponentStatus(
            name="component2",
            component_type=ComponentType.API,
            status=SystemStatus.WARNING
        )
        self.assertEqual(self.monitor.get_system_status(), SystemStatus.WARNING)
        
        # 添加严重组件
        self.monitor.component_statuses["component3"] = ComponentStatus(
            name="component3",
            component_type=ComponentType.API,
            status=SystemStatus.CRITICAL
        )
        self.assertEqual(self.monitor.get_system_status(), SystemStatus.CRITICAL)
    
    def test_get_latest_metrics(self):
        """测试获取最新指标"""
        # 没有指标时应该返回None
        self.assertIsNone(self.monitor.get_latest_metrics())
        
        # 添加指标
        metrics = SystemMetrics(cpu_usage=50.0, memory_usage=60.0)
        self.monitor.metrics_history.append(metrics)
        
        # 获取最新指标
        latest = self.monitor.get_latest_metrics()
        self.assertEqual(latest, metrics)
    
    def test_get_component_status(self):
        """测试获取组件状态"""
        # 不存在的组件应该返回None
        self.assertIsNone(self.monitor.get_component_status("nonexistent"))
        
        # 添加组件状态
        status = ComponentStatus(
            name="test_component",
            component_type=ComponentType.API,
            status=SystemStatus.HEALTHY
        )
        self.monitor.component_statuses["test_component"] = status
        
        # 获取组件状态
        retrieved = self.monitor.get_component_status("test_component")
        self.assertEqual(retrieved, status)
    
    def test_get_active_alerts(self):
        """测试获取活跃告警"""
        # 没有告警时应该返回空列表
        self.assertEqual(self.monitor.get_active_alerts(), [])
        
        # 添加告警
        alert1 = SystemAlert(
            id="alert1",
            level=AlertLevel.WARNING,
            component="component1",
            message="告警1"
        )
        alert2 = SystemAlert(
            id="alert2",
            level=AlertLevel.ERROR,
            component="component2",
            message="告警2",
            resolved=True
        )
        
        self.monitor.alerts.extend([alert1, alert2])
        
        # 获取活跃告警
        active = self.monitor.get_active_alerts()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0], alert1)
    
    def test_resolve_alert(self):
        """测试解决告警"""
        # 添加告警
        alert = SystemAlert(
            id="test_alert",
            level=AlertLevel.WARNING,
            component="test_component",
            message="测试告警"
        )
        self.monitor.alerts.append(alert)
        
        # 解决告警
        result = self.monitor.resolve_alert("test_alert")
        self.assertTrue(result)
        self.assertTrue(alert.resolved)
        self.assertIsNotNone(alert.resolved_time)
        
        # 再次解决已解决的告警
        result = self.monitor.resolve_alert("test_alert")
        self.assertFalse(result)
        
        # 解决不存在的告警
        result = self.monitor.resolve_alert("nonexistent")
        self.assertFalse(result)
    
    def test_update_alert_thresholds(self):
        """测试更新告警阈值"""
        new_thresholds = {
            'cpu_usage': 90.0,
            'memory_usage': 95.0
        }
        
        self.monitor.update_alert_thresholds(new_thresholds)
        
        self.assertEqual(self.monitor.alert_thresholds['cpu_usage'], 90.0)
        self.assertEqual(self.monitor.alert_thresholds['memory_usage'], 95.0)
    
    def test_export_metrics(self):
        """测试导出指标"""
        # 添加指标
        metrics = SystemMetrics(
            cpu_usage=50.0,
            memory_usage=60.0,
            disk_usage=70.0
        )
        self.monitor.metrics_history.append(metrics)
        
        # 导出到临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            self.monitor.export_metrics(temp_path)
            
            # 验证文件存在且内容正确
            self.assertTrue(Path(temp_path).exists())
            
            with open(temp_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]['cpu_usage'], 50.0)
            self.assertEqual(data[0]['memory_usage'], 60.0)
            self.assertEqual(data[0]['disk_usage'], 70.0)
            
        finally:
            # 清理临时文件
            Path(temp_path).unlink(missing_ok=True)
    
    def test_get_system_summary(self):
        """测试获取系统摘要"""
        # 添加指标
        metrics = SystemMetrics(
            cpu_usage=50.0,
            memory_usage=60.0,
            disk_usage=70.0,
            process_count=100,
            uptime=3600
        )
        self.monitor.metrics_history.append(metrics)
        
        # 添加组件状态
        self.monitor.component_statuses["test_component"] = ComponentStatus(
            name="test_component",
            component_type=ComponentType.API,
            status=SystemStatus.HEALTHY,
            response_time=0.1
        )
        
        # 添加告警
        alert = SystemAlert(
            id="test_alert",
            level=AlertLevel.WARNING,
            component="test_component",
            message="测试告警"
        )
        self.monitor.alerts.append(alert)
        
        # 获取摘要
        summary = self.monitor.get_system_summary()
        
        # 验证摘要内容
        self.assertIn('system_status', summary)
        self.assertIn('timestamp', summary)
        self.assertIn('metrics', summary)
        self.assertIn('components', summary)
        self.assertIn('alerts', summary)
        
        # 验证指标
        self.assertEqual(summary['metrics']['cpu_usage'], 50.0)
        self.assertEqual(summary['metrics']['memory_usage'], 60.0)
        
        # 验证组件
        self.assertIn('test_component', summary['components'])
        self.assertEqual(summary['components']['test_component']['status'], 'healthy')
        
        # 验证告警统计
        self.assertEqual(summary['alerts']['total'], 1)
        self.assertEqual(summary['alerts']['warning'], 1)
    
    def test_cleanup_old_data(self):
        """测试清理过期数据"""
        # 添加过期指标
        old_metrics = SystemMetrics(
            timestamp=datetime.now() - timedelta(days=2),
            cpu_usage=50.0
        )
        new_metrics = SystemMetrics(cpu_usage=60.0)
        
        self.monitor.metrics_history.extend([old_metrics, new_metrics])
        
        # 添加过期告警
        old_alert = SystemAlert(
            id="old_alert",
            level=AlertLevel.WARNING,
            component="test_component",
            message="过期告警",
            timestamp=datetime.now() - timedelta(days=2)
        )
        new_alert = SystemAlert(
            id="new_alert",
            level=AlertLevel.WARNING,
            component="test_component",
            message="新告警"
        )
        
        self.monitor.alerts.extend([old_alert, new_alert])
        
        # 清理过期数据
        self.monitor._cleanup_old_data()
        
        # 验证过期数据被清理
        self.assertEqual(len(self.monitor.metrics_history), 1)
        self.assertEqual(self.monitor.metrics_history[0], new_metrics)
        
        self.assertEqual(len(self.monitor.alerts), 1)
        self.assertEqual(self.monitor.alerts[0], new_alert)
    
    def test_start_stop_monitoring(self):
        """测试启动和停止监控"""
        # 启动监控
        self.monitor.start()
        self.assertTrue(self.monitor.is_running)
        self.assertIsNotNone(self.monitor.monitoring_thread)
        
        # 等待一小段时间确保监控循环启动
        time.sleep(0.1)
        
        # 停止监控
        self.monitor.stop()
        self.assertFalse(self.monitor.is_running)
        
        # 再次启动测试重复启动
        self.monitor.start()
        self.assertTrue(self.monitor.is_running)
        
        # 清理
        self.monitor.stop()


class TestSystemMetrics(unittest.TestCase):
    """系统指标测试类"""
    
    def test_system_metrics_creation(self):
        """测试系统指标创建"""
        metrics = SystemMetrics(
            cpu_usage=50.0,
            memory_usage=60.0,
            disk_usage=70.0
        )
        
        self.assertEqual(metrics.cpu_usage, 50.0)
        self.assertEqual(metrics.memory_usage, 60.0)
        self.assertEqual(metrics.disk_usage, 70.0)
        self.assertIsInstance(metrics.timestamp, datetime)


class TestComponentStatus(unittest.TestCase):
    """组件状态测试类"""
    
    def test_component_status_creation(self):
        """测试组件状态创建"""
        status = ComponentStatus(
            name="test_component",
            component_type=ComponentType.API,
            status=SystemStatus.HEALTHY,
            response_time=0.1
        )
        
        self.assertEqual(status.name, "test_component")
        self.assertEqual(status.component_type, ComponentType.API)
        self.assertEqual(status.status, SystemStatus.HEALTHY)
        self.assertEqual(status.response_time, 0.1)
        self.assertIsInstance(status.last_check, datetime)


class TestSystemAlert(unittest.TestCase):
    """系统告警测试类"""
    
    def test_system_alert_creation(self):
        """测试系统告警创建"""
        alert = SystemAlert(
            id="test_alert",
            level=AlertLevel.WARNING,
            component="test_component",
            message="测试告警"
        )
        
        self.assertEqual(alert.id, "test_alert")
        self.assertEqual(alert.level, AlertLevel.WARNING)
        self.assertEqual(alert.component, "test_component")
        self.assertEqual(alert.message, "测试告警")
        self.assertFalse(alert.resolved)
        self.assertIsNone(alert.resolved_time)
        self.assertIsInstance(alert.timestamp, datetime)


class TestHealthCheckResult(unittest.TestCase):
    """健康检查结果测试类"""
    
    def test_health_check_result_creation(self):
        """测试健康检查结果创建"""
        result = HealthCheckResult(
            component="test_component",
            status=SystemStatus.HEALTHY,
            message="测试正常",
            details={"key": "value"}
        )
        
        self.assertEqual(result.component, "test_component")
        self.assertEqual(result.status, SystemStatus.HEALTHY)
        self.assertEqual(result.message, "测试正常")
        self.assertEqual(result.details, {"key": "value"})
        self.assertIsInstance(result.timestamp, datetime)


if __name__ == '__main__':
    unittest.main()