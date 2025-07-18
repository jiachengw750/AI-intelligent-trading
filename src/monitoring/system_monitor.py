# -*- coding: utf-8 -*-
"""
系统监控器模块
用于监控系统状态、健康检查、资源监控等
"""

import asyncio
import logging
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor
import traceback
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from ..utils.helpers.logger import setup_logger


class SystemStatus(Enum):
    """系统状态枚举"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ComponentType(Enum):
    """组件类型枚举"""
    DATABASE = "database"
    API = "api"
    EXCHANGE = "exchange"
    AI_MODEL = "ai_model"
    TRADING_ENGINE = "trading_engine"
    RISK_MANAGER = "risk_manager"
    DATA_COLLECTOR = "data_collector"
    CACHE = "cache"
    MESSAGING = "messaging"
    STORAGE = "storage"


class AlertLevel(Enum):
    """告警级别枚举"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class SystemMetrics:
    """系统指标数据类"""
    timestamp: datetime = field(default_factory=datetime.now)
    
    # CPU指标
    cpu_usage: float = 0.0
    cpu_count: int = 0
    cpu_load_1m: float = 0.0
    cpu_load_5m: float = 0.0
    cpu_load_15m: float = 0.0
    
    # 内存指标
    memory_usage: float = 0.0
    memory_available: int = 0
    memory_total: int = 0
    memory_used: int = 0
    
    # 磁盘指标
    disk_usage: float = 0.0
    disk_free: int = 0
    disk_total: int = 0
    disk_used: int = 0
    
    # 网络指标
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0
    network_packets_sent: int = 0
    network_packets_recv: int = 0
    
    # 进程指标
    process_count: int = 0
    thread_count: int = 0
    
    # 系统指标
    uptime: float = 0.0
    boot_time: datetime = field(default_factory=datetime.now)


@dataclass
class ComponentStatus:
    """组件状态数据类"""
    name: str
    component_type: ComponentType
    status: SystemStatus
    last_check: datetime = field(default_factory=datetime.now)
    response_time: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemAlert:
    """系统告警数据类"""
    id: str
    level: AlertLevel
    component: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    resolved_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthCheckResult:
    """健康检查结果数据类"""
    component: str
    status: SystemStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class SystemMonitor:
    """系统监控器类"""
    
    def __init__(self, 
                 check_interval: int = 30,
                 metrics_retention_days: int = 7,
                 alert_retention_days: int = 30):
        """
        初始化系统监控器
        
        Args:
            check_interval: 检查间隔时间（秒）
            metrics_retention_days: 指标保留天数
            alert_retention_days: 告警保留天数
        """
        self.logger = setup_logger("system_monitor")
        self.check_interval = check_interval
        self.metrics_retention_days = metrics_retention_days
        self.alert_retention_days = alert_retention_days
        
        # 监控状态
        self.is_running = False
        self.monitoring_thread = None
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # 数据存储
        self.metrics_history: List[SystemMetrics] = []
        self.component_statuses: Dict[str, ComponentStatus] = {}
        self.alerts: List[SystemAlert] = []
        self.health_checks: Dict[str, Callable] = {}
        
        # 告警配置
        self.alert_thresholds = {
            'cpu_usage': 80.0,
            'memory_usage': 85.0,
            'disk_usage': 90.0,
            'response_time': 5.0
        }
        
        # 通知配置
        self.notification_handlers: List[Callable] = []
        
        # 故障恢复配置
        self.recovery_handlers: Dict[str, Callable] = {}
        
        # 监控锁
        self.metrics_lock = threading.Lock()
        self.alerts_lock = threading.Lock()
        
        self.logger.info("系统监控器初始化完成")
    
    def start(self):
        """启动系统监控"""
        if self.is_running:
            self.logger.warning("系统监控器已在运行")
            return
        
        self.is_running = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
        self.logger.info("系统监控器已启动")
    
    def stop(self):
        """停止系统监控"""
        if not self.is_running:
            self.logger.warning("系统监控器未在运行")
            return
        
        self.is_running = False
        
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        self.executor.shutdown(wait=True)
        self.logger.info("系统监控器已停止")
    
    def _monitoring_loop(self):
        """监控循环"""
        while self.is_running:
            try:
                # 收集系统指标
                self._collect_system_metrics()
                
                # 执行健康检查
                self._run_health_checks()
                
                # 检查告警条件
                self._check_alert_conditions()
                
                # 清理过期数据
                self._cleanup_old_data()
                
                # 等待下一次检查
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"监控循环发生错误: {e}")
                self.logger.error(traceback.format_exc())
                time.sleep(5)  # 错误后短暂等待
    
    def _collect_system_metrics(self):
        """收集系统指标"""
        try:
            # CPU指标
            cpu_usage = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
            
            # 内存指标
            memory = psutil.virtual_memory()
            
            # 磁盘指标
            disk = psutil.disk_usage('/')
            
            # 网络指标
            network = psutil.net_io_counters()
            
            # 进程指标
            process_count = len(psutil.pids())
            
            # 系统指标
            uptime = time.time() - psutil.boot_time()
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            
            # 创建指标对象
            metrics = SystemMetrics(
                cpu_usage=cpu_usage,
                cpu_count=cpu_count,
                cpu_load_1m=load_avg[0],
                cpu_load_5m=load_avg[1],
                cpu_load_15m=load_avg[2],
                memory_usage=memory.percent,
                memory_available=memory.available,
                memory_total=memory.total,
                memory_used=memory.used,
                disk_usage=disk.percent,
                disk_free=disk.free,
                disk_total=disk.total,
                disk_used=disk.used,
                network_bytes_sent=network.bytes_sent,
                network_bytes_recv=network.bytes_recv,
                network_packets_sent=network.packets_sent,
                network_packets_recv=network.packets_recv,
                process_count=process_count,
                uptime=uptime,
                boot_time=boot_time
            )
            
            # 保存指标
            with self.metrics_lock:
                self.metrics_history.append(metrics)
            
            self.logger.debug(f"收集系统指标: CPU={cpu_usage:.1f}%, 内存={memory.percent:.1f}%, 磁盘={disk.percent:.1f}%")
            
        except Exception as e:
            self.logger.error(f"收集系统指标失败: {e}")
    
    def _run_health_checks(self):
        """执行健康检查"""
        for component_name, check_func in self.health_checks.items():
            try:
                start_time = time.time()
                result = check_func()
                response_time = time.time() - start_time
                
                # 更新组件状态
                self.component_statuses[component_name] = ComponentStatus(
                    name=component_name,
                    component_type=ComponentType.API,  # 默认类型，可以在注册时指定
                    status=result.status,
                    response_time=response_time,
                    error_message=result.message if result.status != SystemStatus.HEALTHY else None,
                    metadata=result.details
                )
                
                self.logger.debug(f"健康检查 {component_name}: {result.status.value}")
                
            except Exception as e:
                self.logger.error(f"健康检查 {component_name} 失败: {e}")
                self.component_statuses[component_name] = ComponentStatus(
                    name=component_name,
                    component_type=ComponentType.API,
                    status=SystemStatus.CRITICAL,
                    error_message=str(e)
                )
    
    def _check_alert_conditions(self):
        """检查告警条件"""
        if not self.metrics_history:
            return
        
        latest_metrics = self.metrics_history[-1]
        
        # 检查CPU使用率
        if latest_metrics.cpu_usage > self.alert_thresholds['cpu_usage']:
            self._create_alert(
                AlertLevel.WARNING,
                "system",
                f"CPU使用率过高: {latest_metrics.cpu_usage:.1f}%",
                {"cpu_usage": latest_metrics.cpu_usage}
            )
        
        # 检查内存使用率
        if latest_metrics.memory_usage > self.alert_thresholds['memory_usage']:
            self._create_alert(
                AlertLevel.WARNING,
                "system",
                f"内存使用率过高: {latest_metrics.memory_usage:.1f}%",
                {"memory_usage": latest_metrics.memory_usage}
            )
        
        # 检查磁盘使用率
        if latest_metrics.disk_usage > self.alert_thresholds['disk_usage']:
            self._create_alert(
                AlertLevel.ERROR,
                "system",
                f"磁盘使用率过高: {latest_metrics.disk_usage:.1f}%",
                {"disk_usage": latest_metrics.disk_usage}
            )
        
        # 检查组件响应时间
        for component_name, status in self.component_statuses.items():
            if status.response_time > self.alert_thresholds['response_time']:
                self._create_alert(
                    AlertLevel.WARNING,
                    component_name,
                    f"组件响应时间过长: {status.response_time:.2f}s",
                    {"response_time": status.response_time}
                )
            
            # 检查组件状态
            if status.status == SystemStatus.CRITICAL:
                self._create_alert(
                    AlertLevel.CRITICAL,
                    component_name,
                    f"组件状态异常: {status.error_message}",
                    {"component_status": status.status.value}
                )
    
    def _create_alert(self, 
                     level: AlertLevel, 
                     component: str, 
                     message: str, 
                     metadata: Dict[str, Any] = None):
        """创建告警"""
        alert_id = f"{component}_{int(time.time())}"
        
        alert = SystemAlert(
            id=alert_id,
            level=level,
            component=component,
            message=message,
            metadata=metadata or {}
        )
        
        with self.alerts_lock:
            # 检查是否已存在类似告警
            similar_alerts = [
                a for a in self.alerts 
                if a.component == component and 
                   a.level == level and 
                   not a.resolved and
                   (datetime.now() - a.timestamp).seconds < 300  # 5分钟内
            ]
            
            if not similar_alerts:
                self.alerts.append(alert)
                self.logger.warning(f"创建告警: {level.value} - {component} - {message}")
                
                # 发送通知
                self._send_notification(alert)
                
                # 尝试自动恢复
                self._attempt_auto_recovery(alert)
    
    def _send_notification(self, alert: SystemAlert):
        """发送通知"""
        for handler in self.notification_handlers:
            try:
                handler(alert)
            except Exception as e:
                self.logger.error(f"发送通知失败: {e}")
    
    def _attempt_auto_recovery(self, alert: SystemAlert):
        """尝试自动恢复"""
        if alert.component in self.recovery_handlers:
            try:
                recovery_func = self.recovery_handlers[alert.component]
                success = recovery_func(alert)
                
                if success:
                    self.resolve_alert(alert.id)
                    self.logger.info(f"自动恢复成功: {alert.component}")
                else:
                    self.logger.warning(f"自动恢复失败: {alert.component}")
                    
            except Exception as e:
                self.logger.error(f"自动恢复过程中发生错误: {e}")
    
    def _cleanup_old_data(self):
        """清理过期数据"""
        now = datetime.now()
        
        # 清理过期指标
        with self.metrics_lock:
            cutoff_time = now - timedelta(days=self.metrics_retention_days)
            self.metrics_history = [
                m for m in self.metrics_history 
                if m.timestamp > cutoff_time
            ]
        
        # 清理过期告警
        with self.alerts_lock:
            cutoff_time = now - timedelta(days=self.alert_retention_days)
            self.alerts = [
                a for a in self.alerts 
                if a.timestamp > cutoff_time
            ]
    
    def register_health_check(self, 
                            component_name: str, 
                            check_func: Callable[[], HealthCheckResult],
                            component_type: ComponentType = ComponentType.API):
        """注册健康检查"""
        self.health_checks[component_name] = check_func
        self.logger.info(f"注册健康检查: {component_name}")
    
    def register_notification_handler(self, handler: Callable[[SystemAlert], None]):
        """注册通知处理器"""
        self.notification_handlers.append(handler)
        self.logger.info("注册通知处理器")
    
    def register_recovery_handler(self, 
                                component: str, 
                                handler: Callable[[SystemAlert], bool]):
        """注册恢复处理器"""
        self.recovery_handlers[component] = handler
        self.logger.info(f"注册恢复处理器: {component}")
    
    def get_system_status(self) -> SystemStatus:
        """获取系统整体状态"""
        if not self.component_statuses:
            return SystemStatus.UNKNOWN
        
        statuses = [status.status for status in self.component_statuses.values()]
        
        if SystemStatus.CRITICAL in statuses:
            return SystemStatus.CRITICAL
        elif SystemStatus.WARNING in statuses:
            return SystemStatus.WARNING
        elif all(status == SystemStatus.HEALTHY for status in statuses):
            return SystemStatus.HEALTHY
        else:
            return SystemStatus.UNKNOWN
    
    def get_latest_metrics(self) -> Optional[SystemMetrics]:
        """获取最新系统指标"""
        with self.metrics_lock:
            return self.metrics_history[-1] if self.metrics_history else None
    
    def get_component_status(self, component_name: str) -> Optional[ComponentStatus]:
        """获取组件状态"""
        return self.component_statuses.get(component_name)
    
    def get_active_alerts(self) -> List[SystemAlert]:
        """获取活跃告警"""
        with self.alerts_lock:
            return [alert for alert in self.alerts if not alert.resolved]
    
    def get_metrics_history(self, 
                          start_time: Optional[datetime] = None,
                          end_time: Optional[datetime] = None) -> List[SystemMetrics]:
        """获取指标历史"""
        with self.metrics_lock:
            metrics = self.metrics_history.copy()
        
        if start_time:
            metrics = [m for m in metrics if m.timestamp >= start_time]
        
        if end_time:
            metrics = [m for m in metrics if m.timestamp <= end_time]
        
        return metrics
    
    def resolve_alert(self, alert_id: str) -> bool:
        """解决告警"""
        with self.alerts_lock:
            for alert in self.alerts:
                if alert.id == alert_id and not alert.resolved:
                    alert.resolved = True
                    alert.resolved_time = datetime.now()
                    self.logger.info(f"告警已解决: {alert_id}")
                    return True
        
        return False
    
    def update_alert_thresholds(self, thresholds: Dict[str, float]):
        """更新告警阈值"""
        self.alert_thresholds.update(thresholds)
        self.logger.info(f"更新告警阈值: {thresholds}")
    
    def export_metrics(self, file_path: str):
        """导出指标数据"""
        try:
            with self.metrics_lock:
                metrics_data = []
                for metric in self.metrics_history:
                    metrics_data.append({
                        'timestamp': metric.timestamp.isoformat(),
                        'cpu_usage': metric.cpu_usage,
                        'memory_usage': metric.memory_usage,
                        'disk_usage': metric.disk_usage,
                        'network_bytes_sent': metric.network_bytes_sent,
                        'network_bytes_recv': metric.network_bytes_recv,
                        'process_count': metric.process_count,
                        'uptime': metric.uptime
                    })
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(metrics_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"指标数据已导出到: {file_path}")
            
        except Exception as e:
            self.logger.error(f"导出指标数据失败: {e}")
    
    def get_system_summary(self) -> Dict[str, Any]:
        """获取系统摘要"""
        latest_metrics = self.get_latest_metrics()
        system_status = self.get_system_status()
        active_alerts = self.get_active_alerts()
        
        summary = {
            'system_status': system_status.value,
            'timestamp': datetime.now().isoformat(),
            'metrics': None,
            'components': {},
            'alerts': {
                'total': len(active_alerts),
                'critical': len([a for a in active_alerts if a.level == AlertLevel.CRITICAL]),
                'error': len([a for a in active_alerts if a.level == AlertLevel.ERROR]),
                'warning': len([a for a in active_alerts if a.level == AlertLevel.WARNING])
            }
        }
        
        if latest_metrics:
            summary['metrics'] = {
                'cpu_usage': latest_metrics.cpu_usage,
                'memory_usage': latest_metrics.memory_usage,
                'disk_usage': latest_metrics.disk_usage,
                'process_count': latest_metrics.process_count,
                'uptime': latest_metrics.uptime
            }
        
        for name, status in self.component_statuses.items():
            summary['components'][name] = {
                'status': status.status.value,
                'response_time': status.response_time,
                'last_check': status.last_check.isoformat()
            }
        
        return summary


# 创建全局系统监控器实例
system_monitor = SystemMonitor()


# 示例健康检查函数
def database_health_check() -> HealthCheckResult:
    """数据库健康检查示例"""
    try:
        # 这里应该是实际的数据库连接检查
        # 示例实现
        return HealthCheckResult(
            component="database",
            status=SystemStatus.HEALTHY,
            message="数据库连接正常"
        )
    except Exception as e:
        return HealthCheckResult(
            component="database",
            status=SystemStatus.CRITICAL,
            message=f"数据库连接失败: {str(e)}"
        )


def api_health_check() -> HealthCheckResult:
    """API健康检查示例"""
    try:
        # 这里应该是实际的API检查
        # 示例实现
        return HealthCheckResult(
            component="api",
            status=SystemStatus.HEALTHY,
            message="API服务正常"
        )
    except Exception as e:
        return HealthCheckResult(
            component="api",
            status=SystemStatus.CRITICAL,
            message=f"API服务异常: {str(e)}"
        )


# 示例通知处理器
def email_notification_handler(alert: SystemAlert):
    """邮件通知处理器示例"""
    # 这里应该是实际的邮件发送逻辑
    print(f"邮件通知: {alert.level.value} - {alert.component} - {alert.message}")


def slack_notification_handler(alert: SystemAlert):
    """Slack通知处理器示例"""
    # 这里应该是实际的Slack通知逻辑
    print(f"Slack通知: {alert.level.value} - {alert.component} - {alert.message}")


# 示例恢复处理器
def restart_component_handler(alert: SystemAlert) -> bool:
    """重启组件处理器示例"""
    try:
        # 这里应该是实际的重启逻辑
        print(f"尝试重启组件: {alert.component}")
        return True
    except Exception as e:
        print(f"重启组件失败: {e}")
        return False


if __name__ == "__main__":
    # 示例使用
    monitor = SystemMonitor(check_interval=10)
    
    # 注册健康检查
    monitor.register_health_check("database", database_health_check)
    monitor.register_health_check("api", api_health_check)
    
    # 注册通知处理器
    monitor.register_notification_handler(email_notification_handler)
    monitor.register_notification_handler(slack_notification_handler)
    
    # 注册恢复处理器
    monitor.register_recovery_handler("database", restart_component_handler)
    
    # 启动监控
    monitor.start()
    
    try:
        # 运行示例
        time.sleep(60)
        
        # 获取系统摘要
        summary = monitor.get_system_summary()
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        
    except KeyboardInterrupt:
        print("停止监控...")
    finally:
        monitor.stop()