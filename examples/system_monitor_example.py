#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统监控器使用示例
"""

import asyncio
import time
import requests
from datetime import datetime
from pathlib import Path
import sys

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent))

from src.monitoring.system_monitor import (
    SystemMonitor, SystemStatus, ComponentType, AlertLevel,
    HealthCheckResult, system_monitor
)


def database_health_check() -> HealthCheckResult:
    """数据库健康检查示例"""
    try:
        # 模拟数据库连接检查
        # 这里可以替换为实际的数据库连接测试
        time.sleep(0.1)  # 模拟响应时间
        
        # 随机模拟健康状态
        import random
        if random.random() > 0.1:  # 90%的概率健康
            return HealthCheckResult(
                component="database",
                status=SystemStatus.HEALTHY,
                message="数据库连接正常",
                details={
                    "connection_pool_size": 10,
                    "active_connections": 3,
                    "query_response_time": 0.05
                }
            )
        else:
            return HealthCheckResult(
                component="database",
                status=SystemStatus.WARNING,
                message="数据库连接池使用率较高",
                details={
                    "connection_pool_size": 10,
                    "active_connections": 8,
                    "query_response_time": 0.2
                }
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
        # 模拟API健康检查
        time.sleep(0.05)  # 模拟响应时间
        
        return HealthCheckResult(
            component="api",
            status=SystemStatus.HEALTHY,
            message="API服务正常",
            details={
                "endpoint": "/health",
                "response_time": 0.05,
                "status_code": 200
            }
        )
    except Exception as e:
        return HealthCheckResult(
            component="api",
            status=SystemStatus.CRITICAL,
            message=f"API服务异常: {str(e)}"
        )


def exchange_health_check() -> HealthCheckResult:
    """交易所连接健康检查示例"""
    try:
        # 模拟交易所连接检查
        time.sleep(0.2)  # 模拟响应时间
        
        import random
        if random.random() > 0.05:  # 95%的概率健康
            return HealthCheckResult(
                component="exchange",
                status=SystemStatus.HEALTHY,
                message="交易所连接正常",
                details={
                    "exchange": "binance",
                    "ws_connected": True,
                    "api_latency": 0.15,
                    "rate_limit_remaining": 1000
                }
            )
        else:
            return HealthCheckResult(
                component="exchange",
                status=SystemStatus.WARNING,
                message="交易所连接延迟较高",
                details={
                    "exchange": "binance",
                    "ws_connected": True,
                    "api_latency": 0.5,
                    "rate_limit_remaining": 100
                }
            )
    except Exception as e:
        return HealthCheckResult(
            component="exchange",
            status=SystemStatus.CRITICAL,
            message=f"交易所连接失败: {str(e)}"
        )


def trading_engine_health_check() -> HealthCheckResult:
    """交易引擎健康检查示例"""
    try:
        # 模拟交易引擎健康检查
        time.sleep(0.1)
        
        return HealthCheckResult(
            component="trading_engine",
            status=SystemStatus.HEALTHY,
            message="交易引擎运行正常",
            details={
                "active_strategies": 3,
                "pending_orders": 5,
                "execution_latency": 0.08,
                "error_rate": 0.001
            }
        )
    except Exception as e:
        return HealthCheckResult(
            component="trading_engine",
            status=SystemStatus.CRITICAL,
            message=f"交易引擎异常: {str(e)}"
        )


def email_notification_handler(alert):
    """邮件通知处理器"""
    print(f"📧 邮件通知: [{alert.level.value.upper()}] {alert.component}")
    print(f"   消息: {alert.message}")
    print(f"   时间: {alert.timestamp}")
    print(f"   详情: {alert.metadata}")
    print("-" * 50)


def slack_notification_handler(alert):
    """Slack通知处理器"""
    emoji_map = {
        AlertLevel.INFO: "ℹ️",
        AlertLevel.WARNING: "⚠️",
        AlertLevel.ERROR: "❌",
        AlertLevel.CRITICAL: "🚨"
    }
    
    emoji = emoji_map.get(alert.level, "📢")
    print(f"{emoji} Slack通知: [{alert.level.value.upper()}] {alert.component}")
    print(f"   消息: {alert.message}")
    print(f"   时间: {alert.timestamp}")
    print("-" * 50)


def database_recovery_handler(alert) -> bool:
    """数据库恢复处理器"""
    print(f"🔧 尝试恢复数据库连接...")
    try:
        # 模拟数据库重连逻辑
        time.sleep(1)
        print("✅ 数据库连接已恢复")
        return True
    except Exception as e:
        print(f"❌ 数据库恢复失败: {e}")
        return False


def trading_engine_recovery_handler(alert) -> bool:
    """交易引擎恢复处理器"""
    print(f"🔧 尝试重启交易引擎...")
    try:
        # 模拟交易引擎重启逻辑
        time.sleep(2)
        print("✅ 交易引擎已重启")
        return True
    except Exception as e:
        print(f"❌ 交易引擎重启失败: {e}")
        return False


def main():
    """主函数"""
    print("🚀 启动系统监控器示例")
    print("=" * 60)
    
    # 创建系统监控器实例
    monitor = SystemMonitor(
        check_interval=5,  # 5秒检查一次
        metrics_retention_days=1,
        alert_retention_days=7
    )
    
    # 注册健康检查
    print("📋 注册健康检查...")
    monitor.register_health_check("database", database_health_check)
    monitor.register_health_check("api", api_health_check)
    monitor.register_health_check("exchange", exchange_health_check)
    monitor.register_health_check("trading_engine", trading_engine_health_check)
    
    # 注册通知处理器
    print("📢 注册通知处理器...")
    monitor.register_notification_handler(email_notification_handler)
    monitor.register_notification_handler(slack_notification_handler)
    
    # 注册恢复处理器
    print("🔧 注册恢复处理器...")
    monitor.register_recovery_handler("database", database_recovery_handler)
    monitor.register_recovery_handler("trading_engine", trading_engine_recovery_handler)
    
    # 设置告警阈值
    print("⚙️  设置告警阈值...")
    monitor.update_alert_thresholds({
        'cpu_usage': 70.0,        # CPU使用率70%告警
        'memory_usage': 80.0,     # 内存使用率80%告警
        'disk_usage': 85.0,       # 磁盘使用率85%告警
        'response_time': 3.0      # 响应时间3秒告警
    })
    
    # 启动监控
    print("🎯 启动系统监控...")
    monitor.start()
    
    try:
        # 运行监控循环
        print("📊 开始监控系统状态...")
        print("Press Ctrl+C to stop")
        print("=" * 60)
        
        for i in range(12):  # 运行1分钟（12次 * 5秒）
            time.sleep(5)
            
            # 显示当前状态
            print(f"\n⏰ 第 {i+1} 次检查 ({datetime.now().strftime('%H:%M:%S')})")
            print("-" * 40)
            
            # 获取系统状态
            system_status = monitor.get_system_status()
            print(f"📊 系统状态: {system_status.value}")
            
            # 获取最新指标
            metrics = monitor.get_latest_metrics()
            if metrics:
                print(f"💻 CPU使用率: {metrics.cpu_usage:.1f}%")
                print(f"🧠 内存使用率: {metrics.memory_usage:.1f}%")
                print(f"💾 磁盘使用率: {metrics.disk_usage:.1f}%")
                print(f"⚡ 进程数: {metrics.process_count}")
                print(f"⏲️  系统运行时间: {metrics.uptime/3600:.1f}小时")
            
            # 显示组件状态
            print("\n🔍 组件状态:")
            for name, status in monitor.component_statuses.items():
                status_emoji = {
                    SystemStatus.HEALTHY: "✅",
                    SystemStatus.WARNING: "⚠️",
                    SystemStatus.CRITICAL: "❌",
                    SystemStatus.UNKNOWN: "❓"
                }.get(status.status, "❓")
                
                print(f"  {status_emoji} {name}: {status.status.value} "
                      f"(响应时间: {status.response_time:.3f}s)")
            
            # 显示活跃告警
            active_alerts = monitor.get_active_alerts()
            if active_alerts:
                print(f"\n🚨 活跃告警 ({len(active_alerts)}):")
                for alert in active_alerts[-3:]:  # 显示最近3个告警
                    print(f"  • [{alert.level.value.upper()}] {alert.component}: {alert.message}")
            else:
                print("\n✅ 无活跃告警")
            
            print("-" * 40)
        
        # 显示系统摘要
        print("\n📋 系统摘要:")
        print("=" * 60)
        summary = monitor.get_system_summary()
        
        print(f"系统状态: {summary['system_status']}")
        print(f"检查时间: {summary['timestamp']}")
        
        if summary['metrics']:
            print(f"CPU使用率: {summary['metrics']['cpu_usage']:.1f}%")
            print(f"内存使用率: {summary['metrics']['memory_usage']:.1f}%")
            print(f"磁盘使用率: {summary['metrics']['disk_usage']:.1f}%")
        
        print(f"组件状态:")
        for name, status in summary['components'].items():
            print(f"  • {name}: {status['status']} (响应时间: {status['response_time']:.3f}s)")
        
        print(f"告警统计:")
        alerts = summary['alerts']
        print(f"  • 总计: {alerts['total']}")
        print(f"  • 严重: {alerts['critical']}")
        print(f"  • 错误: {alerts['error']}")
        print(f"  • 警告: {alerts['warning']}")
        
        # 导出指标数据
        export_file = "/tmp/system_metrics.json"
        monitor.export_metrics(export_file)
        print(f"\n📄 指标数据已导出到: {export_file}")
        
    except KeyboardInterrupt:
        print("\n\n⏹️  用户中断，正在停止监控...")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
    finally:
        # 停止监控
        monitor.stop()
        print("🏁 系统监控器已停止")
        print("=" * 60)


if __name__ == "__main__":
    main()