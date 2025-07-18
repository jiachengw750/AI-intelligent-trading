# -*- coding: utf-8 -*-
"""
性能监控器
"""

import asyncio
import time
import psutil
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import numpy as np
from src.utils.helpers.logger import trading_logger
from src.utils.helpers.async_utils import async_utils


@dataclass
class SystemMetrics:
    """系统指标"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used: float
    memory_available: float
    disk_usage: float
    network_sent: float
    network_recv: float
    active_threads: int
    open_files: int
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp,
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_used": self.memory_used,
            "memory_available": self.memory_available,
            "disk_usage": self.disk_usage,
            "network_sent": self.network_sent,
            "network_recv": self.network_recv,
            "active_threads": self.active_threads,
            "open_files": self.open_files
        }


@dataclass
class PerformanceMetrics:
    """性能指标"""
    timestamp: float
    total_trades: int = 0
    successful_trades: int = 0
    failed_trades: int = 0
    avg_execution_time: float = 0.0
    max_execution_time: float = 0.0
    min_execution_time: float = 0.0
    total_volume: float = 0.0
    total_pnl: float = 0.0
    win_rate: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    api_requests: int = 0
    api_errors: int = 0
    api_latency: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp,
            "total_trades": self.total_trades,
            "successful_trades": self.successful_trades,
            "failed_trades": self.failed_trades,
            "avg_execution_time": self.avg_execution_time,
            "max_execution_time": self.max_execution_time,
            "min_execution_time": self.min_execution_time,
            "total_volume": self.total_volume,
            "total_pnl": self.total_pnl,
            "win_rate": self.win_rate,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "api_requests": self.api_requests,
            "api_errors": self.api_errors,
            "api_latency": self.api_latency
        }


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, collection_interval: float = 5.0):
        self.collection_interval = collection_interval
        self.is_monitoring = False
        
        # 指标存储
        self.system_metrics_history: List[SystemMetrics] = []
        self.performance_metrics_history: List[PerformanceMetrics] = []
        
        # 实时指标
        self.current_system_metrics: Optional[SystemMetrics] = None
        self.current_performance_metrics: Optional[PerformanceMetrics] = None
        
        # 性能计数器
        self.execution_times: List[float] = []
        self.api_response_times: List[float] = []
        self.trade_pnls: List[float] = []
        
        # 统计
        self.start_time = time.time()
        self.total_api_requests = 0
        self.total_api_errors = 0
        self.total_trades = 0
        self.successful_trades = 0
        
        # 回调函数
        self.alert_callbacks: List[Callable] = []
        
        # 性能阈值
        self.performance_thresholds = {
            "cpu_threshold": 80.0,          # CPU使用率阈值
            "memory_threshold": 85.0,       # 内存使用率阈值
            "disk_threshold": 90.0,         # 磁盘使用率阈值
            "execution_time_threshold": 5.0, # 执行时间阈值（秒）
            "api_latency_threshold": 2.0,   # API延迟阈值（秒）
            "error_rate_threshold": 0.05    # 错误率阈值（5%）
        }
        
    def add_alert_callback(self, callback: Callable):
        """添加告警回调"""
        self.alert_callbacks.append(callback)
        trading_logger.info(f"添加性能监控告警回调: {callback.__name__}")
        
    def remove_alert_callback(self, callback: Callable):
        """移除告警回调"""
        if callback in self.alert_callbacks:
            self.alert_callbacks.remove(callback)
            
    async def start_monitoring(self):
        """开始监控"""
        try:
            if self.is_monitoring:
                trading_logger.warning("性能监控已在运行")
                return
                
            self.is_monitoring = True
            self.start_time = time.time()
            
            # 启动监控任务
            asyncio.create_task(self._monitor_system_metrics())
            asyncio.create_task(self._monitor_performance_metrics())
            
            trading_logger.info("性能监控已启动")
            
        except Exception as e:
            trading_logger.error(f"启动性能监控失败: {e}")
            self.is_monitoring = False
            
    async def stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False
        trading_logger.info("性能监控已停止")
        
    async def _monitor_system_metrics(self):
        """监控系统指标"""
        while self.is_monitoring:
            try:
                metrics = await self._collect_system_metrics()
                self.current_system_metrics = metrics
                self.system_metrics_history.append(metrics)
                
                # 限制历史记录大小
                if len(self.system_metrics_history) > 1000:
                    self.system_metrics_history = self.system_metrics_history[-1000:]
                    
                # 检查告警
                await self._check_system_alerts(metrics)
                
                await asyncio.sleep(self.collection_interval)
                
            except Exception as e:
                trading_logger.error(f"监控系统指标失败: {e}")
                await asyncio.sleep(self.collection_interval)
                
    async def _monitor_performance_metrics(self):
        """监控性能指标"""
        while self.is_monitoring:
            try:
                metrics = await self._collect_performance_metrics()
                self.current_performance_metrics = metrics
                self.performance_metrics_history.append(metrics)
                
                # 限制历史记录大小
                if len(self.performance_metrics_history) > 1000:
                    self.performance_metrics_history = self.performance_metrics_history[-1000:]
                    
                # 检查告警
                await self._check_performance_alerts(metrics)
                
                await asyncio.sleep(self.collection_interval)
                
            except Exception as e:
                trading_logger.error(f"监控性能指标失败: {e}")
                await asyncio.sleep(self.collection_interval)
                
    async def _collect_system_metrics(self) -> SystemMetrics:
        """收集系统指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存使用情况
            memory = psutil.virtual_memory()
            
            # 磁盘使用情况
            disk = psutil.disk_usage('/')
            
            # 网络使用情况
            network = psutil.net_io_counters()
            
            # 进程信息
            process = psutil.Process()
            
            metrics = SystemMetrics(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used=memory.used / 1024 / 1024 / 1024,  # GB
                memory_available=memory.available / 1024 / 1024 / 1024,  # GB
                disk_usage=disk.percent,
                network_sent=network.bytes_sent / 1024 / 1024,  # MB
                network_recv=network.bytes_recv / 1024 / 1024,  # MB
                active_threads=threading.active_count(),
                open_files=len(process.open_files())
            )
            
            return metrics
            
        except Exception as e:
            trading_logger.error(f"收集系统指标失败: {e}")
            return SystemMetrics(timestamp=time.time(), cpu_percent=0, memory_percent=0,
                               memory_used=0, memory_available=0, disk_usage=0,
                               network_sent=0, network_recv=0, active_threads=0, open_files=0)
            
    async def _collect_performance_metrics(self) -> PerformanceMetrics:
        """收集性能指标"""
        try:
            # 计算执行时间统计
            avg_execution_time = np.mean(self.execution_times) if self.execution_times else 0.0
            max_execution_time = max(self.execution_times) if self.execution_times else 0.0
            min_execution_time = min(self.execution_times) if self.execution_times else 0.0
            
            # 计算API延迟
            avg_api_latency = np.mean(self.api_response_times) if self.api_response_times else 0.0
            
            # 计算胜率
            win_rate = (self.successful_trades / self.total_trades * 100) if self.total_trades > 0 else 0.0
            
            # 计算总盈亏
            total_pnl = sum(self.trade_pnls)
            
            # 计算夏普比率
            sharpe_ratio = self._calculate_sharpe_ratio()
            
            # 计算最大回撤
            max_drawdown = self._calculate_max_drawdown()
            
            metrics = PerformanceMetrics(
                timestamp=time.time(),
                total_trades=self.total_trades,
                successful_trades=self.successful_trades,
                failed_trades=self.total_trades - self.successful_trades,
                avg_execution_time=avg_execution_time,
                max_execution_time=max_execution_time,
                min_execution_time=min_execution_time,
                total_pnl=total_pnl,
                win_rate=win_rate,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                api_requests=self.total_api_requests,
                api_errors=self.total_api_errors,
                api_latency=avg_api_latency
            )
            
            return metrics
            
        except Exception as e:
            trading_logger.error(f"收集性能指标失败: {e}")
            return PerformanceMetrics(timestamp=time.time())
            
    def _calculate_sharpe_ratio(self) -> float:
        """计算夏普比率"""
        try:
            if len(self.trade_pnls) < 2:
                return 0.0
                
            returns = np.array(self.trade_pnls)
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            
            if std_return == 0:
                return 0.0
                
            # 简化的夏普比率计算（假设无风险利率为0）
            sharpe = mean_return / std_return
            return float(sharpe)
            
        except Exception as e:
            trading_logger.error(f"计算夏普比率失败: {e}")
            return 0.0
            
    def _calculate_max_drawdown(self) -> float:
        """计算最大回撤"""
        try:
            if len(self.trade_pnls) < 2:
                return 0.0
                
            # 计算累计收益曲线
            cumulative_pnl = np.cumsum(self.trade_pnls)
            
            # 计算运行最大值
            running_max = np.maximum.accumulate(cumulative_pnl)
            
            # 计算回撤
            drawdown = (running_max - cumulative_pnl) / (running_max + 1e-8)
            
            max_drawdown = np.max(drawdown)
            return float(max_drawdown)
            
        except Exception as e:
            trading_logger.error(f"计算最大回撤失败: {e}")
            return 0.0
            
    async def _check_system_alerts(self, metrics: SystemMetrics):
        """检查系统告警"""
        try:
            alerts = []
            
            # CPU告警
            if metrics.cpu_percent > self.performance_thresholds["cpu_threshold"]:
                alerts.append(f"CPU使用率过高: {metrics.cpu_percent:.1f}%")
                
            # 内存告警
            if metrics.memory_percent > self.performance_thresholds["memory_threshold"]:
                alerts.append(f"内存使用率过高: {metrics.memory_percent:.1f}%")
                
            # 磁盘告警
            if metrics.disk_usage > self.performance_thresholds["disk_threshold"]:
                alerts.append(f"磁盘使用率过高: {metrics.disk_usage:.1f}%")
                
            # 发送告警
            for alert_message in alerts:
                await self._send_alert("system", alert_message, metrics.to_dict())
                
        except Exception as e:
            trading_logger.error(f"检查系统告警失败: {e}")
            
    async def _check_performance_alerts(self, metrics: PerformanceMetrics):
        """检查性能告警"""
        try:
            alerts = []
            
            # 执行时间告警
            if metrics.avg_execution_time > self.performance_thresholds["execution_time_threshold"]:
                alerts.append(f"平均执行时间过长: {metrics.avg_execution_time:.2f}秒")
                
            # API延迟告警
            if metrics.api_latency > self.performance_thresholds["api_latency_threshold"]:
                alerts.append(f"API延迟过高: {metrics.api_latency:.2f}秒")
                
            # 错误率告警
            if metrics.api_requests > 0:
                error_rate = metrics.api_errors / metrics.api_requests
                if error_rate > self.performance_thresholds["error_rate_threshold"]:
                    alerts.append(f"API错误率过高: {error_rate:.2%}")
                    
            # 发送告警
            for alert_message in alerts:
                await self._send_alert("performance", alert_message, metrics.to_dict())
                
        except Exception as e:
            trading_logger.error(f"检查性能告警失败: {e}")
            
    async def _send_alert(self, alert_type: str, message: str, data: Dict[str, Any]):
        """发送告警"""
        alert_data = {
            "type": alert_type,
            "message": message,
            "timestamp": time.time(),
            "data": data
        }
        
        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert_data)
                else:
                    callback(alert_data)
            except Exception as e:
                trading_logger.error(f"告警回调执行失败: {e}")
                
        trading_logger.warning(f"性能告警: {message}")
        
    def record_trade_execution(self, execution_time: float, success: bool, pnl: float = 0.0):
        """记录交易执行"""
        try:
            self.execution_times.append(execution_time)
            self.total_trades += 1
            
            if success:
                self.successful_trades += 1
                
            if pnl != 0:
                self.trade_pnls.append(pnl)
                
            # 限制列表大小
            if len(self.execution_times) > 1000:
                self.execution_times = self.execution_times[-1000:]
                
            if len(self.trade_pnls) > 1000:
                self.trade_pnls = self.trade_pnls[-1000:]
                
        except Exception as e:
            trading_logger.error(f"记录交易执行失败: {e}")
            
    def record_api_request(self, response_time: float, success: bool = True):
        """记录API请求"""
        try:
            self.api_response_times.append(response_time)
            self.total_api_requests += 1
            
            if not success:
                self.total_api_errors += 1
                
            # 限制列表大小
            if len(self.api_response_times) > 1000:
                self.api_response_times = self.api_response_times[-1000:]
                
        except Exception as e:
            trading_logger.error(f"记录API请求失败: {e}")
            
    def get_current_metrics(self) -> Dict[str, Any]:
        """获取当前指标"""
        return {
            "system_metrics": self.current_system_metrics.to_dict() if self.current_system_metrics else {},
            "performance_metrics": self.current_performance_metrics.to_dict() if self.current_performance_metrics else {},
            "monitoring_status": self.is_monitoring,
            "uptime": time.time() - self.start_time
        }
        
    def get_metrics_history(self, metric_type: str = "all", limit: int = 100) -> Dict[str, List[Dict]]:
        """获取指标历史"""
        history = {}
        
        if metric_type in ["all", "system"]:
            history["system_metrics"] = [
                m.to_dict() for m in self.system_metrics_history[-limit:]
            ]
            
        if metric_type in ["all", "performance"]:
            history["performance_metrics"] = [
                m.to_dict() for m in self.performance_metrics_history[-limit:]
            ]
            
        return history
        
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        current_time = time.time()
        uptime = current_time - self.start_time
        
        return {
            "uptime_seconds": uptime,
            "uptime_formatted": self._format_uptime(uptime),
            "total_trades": self.total_trades,
            "successful_trades": self.successful_trades,
            "failed_trades": self.total_trades - self.successful_trades,
            "success_rate": (self.successful_trades / self.total_trades * 100) if self.total_trades > 0 else 0,
            "total_api_requests": self.total_api_requests,
            "api_errors": self.total_api_errors,
            "api_error_rate": (self.total_api_errors / self.total_api_requests * 100) if self.total_api_requests > 0 else 0,
            "avg_execution_time": np.mean(self.execution_times) if self.execution_times else 0,
            "avg_api_latency": np.mean(self.api_response_times) if self.api_response_times else 0,
            "total_pnl": sum(self.trade_pnls),
            "monitoring_status": self.is_monitoring
        }
        
    def _format_uptime(self, seconds: float) -> str:
        """格式化运行时间"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        
        if days > 0:
            return f"{days}天 {hours}小时 {minutes}分钟 {seconds}秒"
        elif hours > 0:
            return f"{hours}小时 {minutes}分钟 {seconds}秒"
        elif minutes > 0:
            return f"{minutes}分钟 {seconds}秒"
        else:
            return f"{seconds}秒"
            
    def update_thresholds(self, thresholds: Dict[str, float]):
        """更新告警阈值"""
        self.performance_thresholds.update(thresholds)
        trading_logger.info(f"更新性能告警阈值: {thresholds}")
        
    def reset_statistics(self):
        """重置统计信息"""
        self.execution_times.clear()
        self.api_response_times.clear()
        self.trade_pnls.clear()
        self.total_api_requests = 0
        self.total_api_errors = 0
        self.total_trades = 0
        self.successful_trades = 0
        self.start_time = time.time()
        
        trading_logger.info("性能统计信息已重置")


# 创建全局性能监控器
performance_monitor = PerformanceMonitor()