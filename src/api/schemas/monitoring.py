"""
监控相关数据模式
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from decimal import Decimal
from enum import Enum


class MonitoringMetricType(str, Enum):
    """监控指标类型枚举"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class AlertLevel(str, Enum):
    """告警级别枚举"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """告警状态枚举"""
    ACTIVE = "active"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class SystemStatus(str, Enum):
    """系统状态枚举"""
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class SystemMetrics(BaseModel):
    """系统指标模型"""
    cpu_usage: float = Field(..., ge=0, le=100, description="CPU使用率")
    memory_usage: float = Field(..., ge=0, le=100, description="内存使用率")
    disk_usage: float = Field(..., ge=0, le=100, description="磁盘使用率")
    network_io: Dict[str, float] = Field(..., description="网络IO")
    load_average: List[float] = Field(..., description="负载均衡")
    timestamp: datetime = Field(..., description="时间戳")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TradingMetrics(BaseModel):
    """交易指标模型"""
    total_orders: int = Field(..., description="总订单数")
    active_orders: int = Field(..., description="活跃订单数")
    filled_orders: int = Field(..., description="已成交订单数")
    cancelled_orders: int = Field(..., description="已取消订单数")
    success_rate: float = Field(..., ge=0, le=100, description="成功率")
    average_fill_time: float = Field(..., description="平均成交时间")
    total_volume: Decimal = Field(..., description="总成交量")
    total_value: Decimal = Field(..., description="总成交额")
    profit_loss: Decimal = Field(..., description="盈亏")
    timestamp: datetime = Field(..., description="时间戳")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class PerformanceMetrics(BaseModel):
    """性能指标模型"""
    api_latency: float = Field(..., description="API延迟")
    order_latency: float = Field(..., description="订单延迟")
    data_feed_latency: float = Field(..., description="数据馈送延迟")
    throughput: float = Field(..., description="吞吐量")
    error_rate: float = Field(..., ge=0, le=100, description="错误率")
    uptime: float = Field(..., ge=0, le=100, description="运行时间")
    timestamp: datetime = Field(..., description="时间戳")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AlertInfo(BaseModel):
    """告警信息模型"""
    alert_id: str = Field(..., description="告警ID")
    name: str = Field(..., description="告警名称")
    description: str = Field(..., description="告警描述")
    level: AlertLevel = Field(..., description="告警级别")
    status: AlertStatus = Field(..., description="告警状态")
    source: str = Field(..., description="告警源")
    metric_name: str = Field(..., description="指标名称")
    metric_value: Union[float, int, str] = Field(..., description="指标值")
    threshold: Union[float, int, str] = Field(..., description="阈值")
    triggered_at: datetime = Field(..., description="触发时间")
    resolved_at: Optional[datetime] = Field(None, description="解决时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CreateAlertRequest(BaseModel):
    """创建告警请求模型"""
    name: str = Field(..., min_length=1, max_length=100, description="告警名称")
    description: str = Field(..., min_length=1, max_length=500, description="告警描述")
    metric_name: str = Field(..., description="指标名称")
    threshold: Union[float, int, str] = Field(..., description="阈值")
    condition: str = Field(..., regex="^(>|<|>=|<=|==|!=)$", description="条件")
    level: AlertLevel = Field(..., description="告警级别")
    enabled: bool = Field(default=True, description="是否启用")


class UpdateAlertRequest(BaseModel):
    """更新告警请求模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="告警名称")
    description: Optional[str] = Field(None, min_length=1, max_length=500, description="告警描述")
    threshold: Optional[Union[float, int, str]] = Field(None, description="阈值")
    condition: Optional[str] = Field(None, regex="^(>|<|>=|<=|==|!=)$", description="条件")
    level: Optional[AlertLevel] = Field(None, description="告警级别")
    enabled: Optional[bool] = Field(None, description="是否启用")


class MetricQuery(BaseModel):
    """指标查询模型"""
    metric_name: str = Field(..., description="指标名称")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime = Field(..., description="结束时间")
    interval: str = Field(default="1m", description="时间间隔")
    aggregation: str = Field(default="avg", regex="^(avg|min|max|sum|count)$", description="聚合方式")
    
    @validator('end_time')
    def validate_time_range(cls, v, values):
        if v and values.get('start_time') and v <= values['start_time']:
            raise ValueError('结束时间必须晚于开始时间')
        return v


class MetricData(BaseModel):
    """指标数据模型"""
    metric_name: str = Field(..., description="指标名称")
    timestamp: datetime = Field(..., description="时间戳")
    value: Union[float, int] = Field(..., description="指标值")
    labels: Dict[str, str] = Field(default_factory=dict, description="标签")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class HealthCheckResult(BaseModel):
    """健康检查结果模型"""
    service_name: str = Field(..., description="服务名称")
    status: SystemStatus = Field(..., description="状态")
    message: str = Field(..., description="状态消息")
    details: Dict[str, Any] = Field(default_factory=dict, description="详细信息")
    timestamp: datetime = Field(..., description="检查时间")
    response_time: float = Field(..., description="响应时间")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SystemHealthResponse(BaseModel):
    """系统健康状况响应模型"""
    overall_status: SystemStatus = Field(..., description="整体状态")
    services: List[HealthCheckResult] = Field(..., description="服务状态")
    timestamp: datetime = Field(..., description="检查时间")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class LogEntry(BaseModel):
    """日志条目模型"""
    timestamp: datetime = Field(..., description="时间戳")
    level: str = Field(..., description="日志级别")
    logger: str = Field(..., description="日志器")
    message: str = Field(..., description="日志消息")
    module: str = Field(..., description="模块")
    function: str = Field(..., description="函数")
    line: int = Field(..., description="行号")
    extra: Dict[str, Any] = Field(default_factory=dict, description="额外信息")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class LogQuery(BaseModel):
    """日志查询模型"""
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime = Field(..., description="结束时间")
    level: Optional[str] = Field(None, description="日志级别")
    logger: Optional[str] = Field(None, description="日志器")
    message: Optional[str] = Field(None, description="消息关键词")
    limit: int = Field(default=1000, ge=1, le=10000, description="条数限制")
    
    @validator('end_time')
    def validate_time_range(cls, v, values):
        if v and values.get('start_time') and v <= values['start_time']:
            raise ValueError('结束时间必须晚于开始时间')
        return v


class DashboardWidget(BaseModel):
    """仪表盘小部件模型"""
    widget_id: str = Field(..., description="小部件ID")
    widget_type: str = Field(..., description="小部件类型")
    title: str = Field(..., description="标题")
    config: Dict[str, Any] = Field(..., description="配置")
    position: Dict[str, int] = Field(..., description="位置")
    size: Dict[str, int] = Field(..., description="尺寸")


class DashboardConfig(BaseModel):
    """仪表盘配置模型"""
    dashboard_id: str = Field(..., description="仪表盘ID")
    name: str = Field(..., description="名称")
    description: str = Field(..., description="描述")
    widgets: List[DashboardWidget] = Field(..., description="小部件列表")
    layout: Dict[str, Any] = Field(..., description="布局配置")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }