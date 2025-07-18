# -*- coding: utf-8 -*-
"""
交易监控器使用示例
"""

import asyncio
import time
import random
from src.monitoring.trade_monitor import (
    TradeMonitor, TradeExecution, PositionInfo, TradeAlert, AlertLevel
)


async def alert_callback(alert: TradeAlert):
    """告警回调函数"""
    print(f"[{alert.level.value.upper()}] {alert.symbol}: {alert.message}")


async def main():
    """主函数"""
    # 创建交易监控器
    monitor = TradeMonitor(monitoring_interval=2.0)
    
    # 添加告警回调
    monitor.add_alert_callback(alert_callback)
    
    # 启动监控
    await monitor.start_monitoring()
    
    # 模拟交易执行
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    
    for i in range(20):
        symbol = random.choice(symbols)
        side = random.choice(["BUY", "SELL"])
        amount = random.uniform(0.1, 2.0)
        price = random.uniform(20000, 50000) if symbol == "BTCUSDT" else random.uniform(1000, 3000)
        
        # 模拟交易执行
        execution = TradeExecution(
            execution_id=f"exec_{i}",
            symbol=symbol,
            side=side,
            amount=amount,
            price=price,
            execution_time=random.uniform(0.1, 3.0),
            timestamp=time.time(),
            order_id=f"order_{i}",
            pnl=random.uniform(-100, 200),
            slippage=random.uniform(-0.01, 0.01),
            fees=amount * price * 0.001
        )
        
        # 记录交易执行
        await monitor.record_trade_execution(execution)
        
        # 模拟持仓更新
        position = PositionInfo(
            symbol=symbol,
            side=side,
            size=amount,
            avg_price=price,
            unrealized_pnl=random.uniform(-50, 100),
            realized_pnl=random.uniform(-100, 200),
            timestamp=time.time()
        )
        
        await monitor.update_position(position)
        
        # 等待一段时间
        await asyncio.sleep(1)
        
        # 每隔几次打印监控摘要
        if i % 5 == 0:
            print("\n=== 性能摘要 ===")
            summary = monitor.get_performance_summary()
            print(f"总交易数: {summary['total_trades']}")
            print(f"总成交量: {summary['total_volume']:.2f}")
            print(f"总PnL: {summary['total_pnl']:.2f}")
            print(f"平均胜率: {summary['avg_win_rate']:.1f}%")
            print(f"活跃告警: {summary['active_alerts']}")
            
            print("\n=== 风险摘要 ===")
            risk_summary = monitor.get_risk_summary()
            print(f"总敞口: {risk_summary['total_exposure']:.2f}")
            print(f"最大回撤: {risk_summary['max_drawdown']:.2%}")
            print(f"当前回撤: {risk_summary['current_drawdown']:.2%}")
            
            print("\n=== 交易指标 ===")
            for symbol, metrics in monitor.get_trade_metrics().items():
                print(f"{symbol}: 交易数={metrics.total_trades}, "
                      f"胜率={metrics.win_rate:.1f}%, "
                      f"PnL={metrics.total_pnl:.2f}")
                      
            print("\n=== 活跃告警 ===")
            alerts = monitor.get_active_alerts()
            for alert in alerts:
                print(f"- [{alert.level.value}] {alert.symbol}: {alert.message}")
                
            print("=" * 50)
    
    # 停止监控
    await monitor.stop_monitoring()
    
    # 最终摘要
    print("\n=== 最终摘要 ===")
    final_summary = monitor.get_performance_summary()
    print(f"监控时长: {final_summary['uptime']:.1f}秒")
    print(f"总交易数: {final_summary['total_trades']}")
    print(f"总成交量: {final_summary['total_volume']:.2f}")
    print(f"总PnL: {final_summary['total_pnl']:.2f}")
    print(f"平均胜率: {final_summary['avg_win_rate']:.1f}%")


if __name__ == "__main__":
    asyncio.run(main())