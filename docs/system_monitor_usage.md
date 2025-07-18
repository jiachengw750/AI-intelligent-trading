# 系统监控器使用指南

## 概述

系统监控器（SystemMonitor）是AI智能交易大脑项目中的核心监控组件，负责实时监控系统状态、组件健康、资源使用情况，并在发生异常时自动告警和恢复。

## 主要功能

### 1. 系统指标监控
- **CPU使用率**：实时监控CPU使用情况
- **内存使用率**：监控内存使用情况和可用空间
- **磁盘使用率**：监控磁盘空间使用情况
- **网络I/O**：监控网络传输状态
- **进程数量**：监控系统进程数量
- **系统运行时间**：监控系统运行时间

### 2. 组件健康检查
- **自定义健康检查**：支持注册自定义健康检查函数
- **响应时间监控**：监控组件响应时间
- **状态跟踪**：跟踪组件状态变化
- **故障检测**：自动检测组件故障

### 3. 告警系统
- **多级告警**：支持INFO、WARNING、ERROR、CRITICAL四个级别
- **告警去重**：避免重复告警
- **告警历史**：保存告警历史记录
- **自动解决**：支持告警自动解决

### 4. 通知机制
- **多种通知方式**：支持邮件、Slack等通知方式
- **自定义通知处理器**：支持自定义通知处理逻辑
- **异步通知**：支持异步通知发送

### 5. 自动恢复
- **故障自动恢复**：支持组件故障自动恢复
- **自定义恢复策略**：支持自定义恢复处理逻辑
- **恢复状态跟踪**：跟踪恢复操作结果

## 快速开始

### 1. 基本使用

```python
from src.monitoring.system_monitor import SystemMonitor, SystemStatus, HealthCheckResult

# 创建系统监控器实例
monitor = SystemMonitor(
    check_interval=30,  # 检查间隔30秒
    metrics_retention_days=7,  # 指标保留7天
    alert_retention_days=30    # 告警保留30天
)

# 启动监控
monitor.start()

# 运行一段时间后停止
monitor.stop()
```

### 2. 注册健康检查

```python
def database_health_check() -> HealthCheckResult:
    """数据库健康检查"""
    try:
        # 执行数据库连接测试
        # ...
        return HealthCheckResult(
            component="database",
            status=SystemStatus.HEALTHY,
            message="数据库连接正常",
            details={"connection_pool": 10, "active_connections": 3}
        )
    except Exception as e:
        return HealthCheckResult(
            component="database",
            status=SystemStatus.CRITICAL,
            message=f"数据库连接失败: {str(e)}"
        )

# 注册健康检查
monitor.register_health_check("database", database_health_check)
```

### 3. 注册通知处理器

```python
def email_notification(alert):
    """邮件通知处理器"""
    print(f"发送邮件通知: {alert.message}")
    # 实际的邮件发送逻辑
    # ...

def slack_notification(alert):
    """Slack通知处理器"""
    print(f"发送Slack通知: {alert.message}")
    # 实际的Slack通知逻辑
    # ...

# 注册通知处理器
monitor.register_notification_handler(email_notification)
monitor.register_notification_handler(slack_notification)
```

### 4. 注册恢复处理器

```python
def database_recovery(alert) -> bool:
    """数据库恢复处理器"""
    try:
        # 执行数据库重连逻辑
        # ...
        return True  # 恢复成功
    except Exception as e:
        return False  # 恢复失败

# 注册恢复处理器
monitor.register_recovery_handler("database", database_recovery)
```

## 高级用法

### 1. 自定义告警阈值

```python
# 更新告警阈值
monitor.update_alert_thresholds({
    'cpu_usage': 80.0,        # CPU使用率80%告警
    'memory_usage': 85.0,     # 内存使用率85%告警
    'disk_usage': 90.0,       # 磁盘使用率90%告警
    'response_time': 5.0      # 响应时间5秒告警
})
```

### 2. 获取系统状态

```python
# 获取系统整体状态
system_status = monitor.get_system_status()
print(f"系统状态: {system_status.value}")

# 获取最新指标
metrics = monitor.get_latest_metrics()
if metrics:
    print(f"CPU使用率: {metrics.cpu_usage}%")
    print(f"内存使用率: {metrics.memory_usage}%")
    print(f"磁盘使用率: {metrics.disk_usage}%")

# 获取组件状态
database_status = monitor.get_component_status("database")
if database_status:
    print(f"数据库状态: {database_status.status.value}")
    print(f"响应时间: {database_status.response_time}s")
```

### 3. 获取告警信息

```python
# 获取活跃告警
active_alerts = monitor.get_active_alerts()
for alert in active_alerts:
    print(f"告警: {alert.level.value} - {alert.component} - {alert.message}")

# 手动解决告警
monitor.resolve_alert("alert_id")
```

### 4. 指标历史查询

```python
from datetime import datetime, timedelta

# 获取最近1小时的指标
end_time = datetime.now()
start_time = end_time - timedelta(hours=1)
metrics_history = monitor.get_metrics_history(start_time, end_time)

for metrics in metrics_history:
    print(f"时间: {metrics.timestamp}, CPU: {metrics.cpu_usage}%")
```

### 5. 导出指标数据

```python
# 导出指标数据到JSON文件
monitor.export_metrics("/path/to/metrics.json")
```

### 6. 获取系统摘要

```python
# 获取系统摘要
summary = monitor.get_system_summary()
print(f"系统状态: {summary['system_status']}")
print(f"组件数量: {len(summary['components'])}")
print(f"活跃告警: {summary['alerts']['total']}")
```

## 集成示例

### 1. 在交易系统中使用

```python
from src.monitoring.system_monitor import system_monitor
from src.trading.exchanges.base_exchange import BaseExchange

class TradingSystem:
    def __init__(self):
        self.monitor = system_monitor
        self.exchange = BaseExchange()
        
        # 注册健康检查
        self.monitor.register_health_check("exchange", self._exchange_health_check)
        self.monitor.register_health_check("trading_engine", self._trading_engine_health_check)
        
        # 注册通知处理器
        self.monitor.register_notification_handler(self._send_alert_notification)
        
        # 注册恢复处理器
        self.monitor.register_recovery_handler("exchange", self._recover_exchange)
        
        # 启动监控
        self.monitor.start()
    
    def _exchange_health_check(self):
        """交易所健康检查"""
        try:
            # 检查交易所连接
            if self.exchange.is_connected():
                return HealthCheckResult(
                    component="exchange",
                    status=SystemStatus.HEALTHY,
                    message="交易所连接正常"
                )
            else:
                return HealthCheckResult(
                    component="exchange",
                    status=SystemStatus.CRITICAL,
                    message="交易所连接断开"
                )
        except Exception as e:
            return HealthCheckResult(
                component="exchange",
                status=SystemStatus.CRITICAL,
                message=f"交易所检查失败: {str(e)}"
            )
    
    def _trading_engine_health_check(self):
        """交易引擎健康检查"""
        # 实现交易引擎健康检查逻辑
        pass
    
    def _send_alert_notification(self, alert):
        """发送告警通知"""
        # 实现告警通知逻辑
        pass
    
    def _recover_exchange(self, alert):
        """恢复交易所连接"""
        try:
            self.exchange.reconnect()
            return True
        except Exception as e:
            return False
```

### 2. 在Web API中使用

```python
from flask import Flask, jsonify
from src.monitoring.system_monitor import system_monitor

app = Flask(__name__)

@app.route('/health')
def health_check():
    """健康检查端点"""
    system_status = system_monitor.get_system_status()
    return jsonify({
        'status': system_status.value,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/metrics')
def get_metrics():
    """获取系统指标"""
    metrics = system_monitor.get_latest_metrics()
    if metrics:
        return jsonify({
            'cpu_usage': metrics.cpu_usage,
            'memory_usage': metrics.memory_usage,
            'disk_usage': metrics.disk_usage,
            'timestamp': metrics.timestamp.isoformat()
        })
    return jsonify({'error': '暂无指标数据'})

@app.route('/alerts')
def get_alerts():
    """获取活跃告警"""
    alerts = system_monitor.get_active_alerts()
    return jsonify([{
        'id': alert.id,
        'level': alert.level.value,
        'component': alert.component,
        'message': alert.message,
        'timestamp': alert.timestamp.isoformat()
    } for alert in alerts])

@app.route('/summary')
def get_summary():
    """获取系统摘要"""
    summary = system_monitor.get_system_summary()
    return jsonify(summary)
```

## 最佳实践

### 1. 健康检查设计
- **快速响应**：健康检查应该快速响应，避免阻塞监控循环
- **有意义的检查**：检查应该能够真实反映组件的健康状态
- **错误处理**：健康检查函数应该包含适当的错误处理

### 2. 告警策略
- **合理阈值**：根据实际情况设置合理的告警阈值
- **告警分级**：不同严重程度的问题应该使用不同的告警级别
- **避免告警风暴**：使用告警去重机制避免告警风暴

### 3. 通知配置
- **多渠道通知**：配置多种通知渠道确保告警及时送达
- **分级通知**：不同级别的告警可以发送到不同的通知渠道
- **静默时间**：配置适当的静默时间避免频繁通知

### 4. 恢复策略
- **安全恢复**：恢复操作应该是安全的，不会造成更大的问题
- **恢复验证**：恢复操作后应该验证是否真正解决了问题
- **恢复记录**：记录恢复操作的结果和过程

### 5. 性能优化
- **异步操作**：使用异步操作避免阻塞主线程
- **资源管理**：合理管理内存和存储资源
- **监控性能**：监控监控系统本身的性能

## 故障排除

### 1. 监控器启动失败
- 检查依赖包是否正确安装
- 检查权限是否足够
- 检查日志文件中的错误信息

### 2. 健康检查失败
- 检查健康检查函数是否正确实现
- 检查组件是否正常运行
- 检查网络连接是否正常

### 3. 告警未发送
- 检查通知处理器是否正确注册
- 检查告警阈值是否合理
- 检查通知渠道是否正常

### 4. 自动恢复失败
- 检查恢复处理器是否正确实现
- 检查恢复操作是否有足够权限
- 检查恢复逻辑是否正确

## 配置参数

### 系统监控器参数
- `check_interval`：检查间隔时间（秒），默认30秒
- `metrics_retention_days`：指标保留天数，默认7天
- `alert_retention_days`：告警保留天数，默认30天

### 告警阈值参数
- `cpu_usage`：CPU使用率告警阈值，默认80%
- `memory_usage`：内存使用率告警阈值，默认85%
- `disk_usage`：磁盘使用率告警阈值，默认90%
- `response_time`：响应时间告警阈值，默认5秒

## 总结

系统监控器提供了完整的系统监控解决方案，包括指标收集、健康检查、告警通知和自动恢复。通过合理配置和使用，可以大大提高系统的稳定性和可靠性。

更多详细信息请参考源代码注释和测试用例。