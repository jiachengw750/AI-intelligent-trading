# 交易监控器使用指南

## 概述

交易监控器 (`TradeMonitor`) 是AI智能交易大脑项目的核心组件之一，负责实时监控交易活动、分析交易性能、管理风险告警，并提供详细的交易统计数据。

## 主要功能

### 1. 交易执行监控
- 实时记录交易执行信息
- 跟踪订单状态变化
- 分析执行效率和滑点

### 2. 持仓管理
- 监控持仓大小和方向
- 计算未实现盈亏
- 跟踪持仓变化

### 3. 性能分析
- 计算胜率、盈利因子、夏普比率
- 分析最大回撤和当前回撤
- 统计交易频率和成交量

### 4. 风险监控
- 实时监控风险指标
- 设置风险阈值告警
- 计算VaR和敞口

### 5. 告警系统
- 多级别告警机制
- 自定义告警回调
- 告警历史记录

## 快速开始

### 基本用法

```python
import asyncio
from src.monitoring.trade_monitor import TradeMonitor, TradeExecution, PositionInfo

async def main():
    # 创建监控器实例
    monitor = TradeMonitor(monitoring_interval=1.0)
    
    # 添加告警回调
    async def alert_handler(alert):
        print(f"告警: {alert.message}")
    
    monitor.add_alert_callback(alert_handler)
    
    # 启动监控
    await monitor.start_monitoring()
    
    # 记录交易执行
    execution = TradeExecution(
        execution_id="exec_1",
        symbol="BTCUSDT",
        side="BUY",
        amount=1.0,
        price=50000.0,
        execution_time=0.5,
        timestamp=time.time(),
        order_id="order_1",
        pnl=100.0,
        slippage=0.001,
        fees=25.0
    )
    
    await monitor.record_trade_execution(execution)
    
    # 更新持仓
    position = PositionInfo(
        symbol="BTCUSDT",
        side="LONG",
        size=1.0,
        avg_price=50000.0,
        unrealized_pnl=100.0,
        realized_pnl=0.0,
        timestamp=time.time()
    )
    
    await monitor.update_position(position)
    
    # 获取监控数据
    summary = monitor.get_performance_summary()
    print(f"总交易数: {summary['total_trades']}")
    print(f"总PnL: {summary['total_pnl']}")
    
    # 停止监控
    await monitor.stop_monitoring()

if __name__ == "__main__":
    asyncio.run(main())
```

### 集成到交易系统

```python
from src.monitoring.trade_monitor import trade_monitor
from src.trading.orders.order_manager import order_manager

# 设置订单事件处理器
async def on_order_filled(event):
    # 从订单事件创建交易执行记录
    execution = TradeExecution(
        execution_id=f"exec_{event.order_id}",
        symbol=event.symbol,
        side=event.data["side"],
        amount=event.data["amount"],
        price=event.data["price"],
        execution_time=event.data.get("execution_time", 0.0),
        timestamp=event.timestamp,
        order_id=event.order_id,
        pnl=event.data.get("pnl", 0.0),
        slippage=event.data.get("slippage", 0.0),
        fees=event.data.get("fees", 0.0)
    )
    
    # 记录到交易监控器
    await trade_monitor.record_trade_execution(execution)

# 添加订单事件处理器
order_manager.add_event_handler("order_filled", on_order_filled)

# 启动监控
await trade_monitor.start_monitoring()
```

## 配置选项

### 监控间隔
```python
# 设置监控间隔为2秒
monitor = TradeMonitor(monitoring_interval=2.0)
```

### 风险阈值
```python
# 更新风险阈值
monitor.update_risk_thresholds({
    "max_drawdown": 0.15,        # 最大回撤15%
    "position_size_limit": 0.08,  # 单个持仓8%
    "daily_loss_limit": 0.03,    # 日损失3%
    "execution_time_limit": 3.0,  # 执行时间限制3秒
    "slippage_limit": 0.02       # 滑点限制2%
})
```

### 性能阈值
```python
# 更新性能阈值
monitor.update_performance_thresholds({
    "min_win_rate": 0.40,         # 最小胜率40%
    "min_profit_factor": 1.5,     # 最小盈利因子1.5
    "min_sharpe_ratio": 0.8,      # 最小夏普比率0.8
})
```

## 数据获取

### 获取交易指标
```python
# 获取特定符号的交易指标
metrics = monitor.get_trade_metrics("BTCUSDT")
print(f"胜率: {metrics.win_rate:.1f}%")
print(f"盈利因子: {metrics.profit_factor:.2f}")
print(f"夏普比率: {metrics.sharpe_ratio:.2f}")
print(f"最大回撤: {metrics.max_drawdown:.2%}")

# 获取所有符号的交易指标
all_metrics = monitor.get_trade_metrics()
for symbol, metrics in all_metrics.items():
    print(f"{symbol}: {metrics.total_trades} 交易")
```

### 获取持仓信息
```python
# 获取特定符号的持仓
position = monitor.get_position_info("BTCUSDT")
if position:
    print(f"持仓大小: {position.size}")
    print(f"未实现盈亏: {position.unrealized_pnl}")

# 获取所有持仓
all_positions = monitor.get_position_info()
for symbol, position in all_positions.items():
    print(f"{symbol}: {position.side} {position.size}")
```

### 获取交易执行记录
```python
# 获取最近100个交易执行
executions = monitor.get_trade_executions("BTCUSDT", limit=100)
for exec in executions:
    print(f"{exec.symbol} {exec.side} {exec.amount} @ {exec.price}")
```

### 获取告警信息
```python
# 获取活跃告警
alerts = monitor.get_active_alerts()
for alert in alerts:
    print(f"[{alert.level.value}] {alert.symbol}: {alert.message}")

# 获取特定符号的告警
btc_alerts = monitor.get_active_alerts("BTCUSDT")
```

## 告警处理

### 告警回调
```python
async def alert_callback(alert):
    """处理告警的回调函数"""
    if alert.level == AlertLevel.CRITICAL:
        # 处理严重告警
        print(f"严重告警: {alert.message}")
        # 可以发送邮件、短信或其他通知
    elif alert.level == AlertLevel.HIGH:
        # 处理高级告警
        print(f"高级告警: {alert.message}")
    else:
        # 处理其他告警
        print(f"告警: {alert.message}")

monitor.add_alert_callback(alert_callback)
```

### 清除告警
```python
# 清除特定告警
monitor.clear_alert("max_drawdown_BTCUSDT")

# 清除所有告警
monitor.clear_all_alerts()
```

## 事件处理

### 事件回调
```python
async def event_callback(event):
    """处理交易事件的回调函数"""
    if event.event_type == TradeEventType.TRADE_EXECUTION:
        print(f"交易执行: {event.symbol}")
    elif event.event_type == TradeEventType.POSITION_CHANGE:
        print(f"持仓变化: {event.symbol}")
    elif event.event_type == TradeEventType.RISK_ALERT:
        print(f"风险告警: {event.symbol}")

monitor.add_event_callback(event_callback)
```

## 性能优化

### 数据清理
```python
# 重置统计信息
monitor.reset_statistics()

# 清除历史数据
monitor.clear_all_alerts()
```

### 监控优化
```python
# 调整监控间隔
monitor.monitoring_interval = 0.5  # 更频繁的监控

# 限制历史数据大小（自动处理）
# 交易执行记录、指标历史等都会自动限制到1000条
```

## 集成示例

### 与风险管理系统集成
```python
from src.risk.control.risk_manager import risk_manager

async def risk_alert_handler(alert):
    """风险告警处理器"""
    if alert.alert_type == "max_drawdown_exceeded":
        # 暂停交易
        await risk_manager.pause_trading()
    elif alert.alert_type == "large_position":
        # 减少仓位
        await risk_manager.reduce_position(alert.symbol)

monitor.add_alert_callback(risk_alert_handler)
```

### 与数据存储集成
```python
from src.data.storage.data_storage import data_storage

async def data_persistence_handler(event):
    """数据持久化处理器"""
    if event.event_type == TradeEventType.TRADE_EXECUTION:
        # 保存交易执行数据
        await data_storage.save_trade_execution(event.data)
    elif event.event_type == TradeEventType.POSITION_CHANGE:
        # 保存持仓变化数据
        await data_storage.save_position_change(event.data)

monitor.add_event_callback(data_persistence_handler)
```

## 最佳实践

1. **监控间隔设置**: 根据交易频率调整监控间隔，高频交易建议使用较短间隔
2. **阈值设置**: 根据交易策略和风险偏好调整告警阈值
3. **回调处理**: 确保回调函数不会阻塞主线程，使用异步处理
4. **数据管理**: 定期清理历史数据，避免内存占用过高
5. **错误处理**: 在回调函数中添加适当的错误处理逻辑
6. **性能监控**: 监控监控器本身的性能，避免影响交易系统

## 常见问题

### Q: 如何处理大量交易数据？
A: 监控器会自动限制历史数据大小，可以通过调整监控间隔和使用数据持久化来优化性能。

### Q: 告警太多怎么办？
A: 可以调整告警阈值，或者在回调中添加告警过滤逻辑。

### Q: 如何确保监控数据的准确性？
A: 使用事务性记录，确保数据一致性，并添加数据验证逻辑。

### Q: 监控器会影响交易性能吗？
A: 监控器设计为非阻塞式，但在高频交易场景下建议适当调整监控间隔。

## 总结

交易监控器是一个强大的工具，可以帮助您实时监控交易活动、管理风险、分析性能。通过合理配置和使用，可以显著提升交易系统的稳定性和可靠性。