"""
风险管理相关数据模式
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from decimal import Decimal
from enum import Enum


class RiskLevel(str, Enum):
    """风险级别枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskType(str, Enum):
    """风险类型枚举"""
    MARKET = "market"
    LIQUIDITY = "liquidity"
    CREDIT = "credit"
    OPERATIONAL = "operational"
    SYSTEMIC = "systemic"


class RiskControlAction(str, Enum):
    """风险控制行为枚举"""
    ALERT = "alert"
    REDUCE_POSITION = "reduce_position"
    CLOSE_POSITION = "close_position"
    STOP_TRADING = "stop_trading"
    FORCE_LIQUIDATION = "force_liquidation"


class RiskMetrics(BaseModel):
    """风险指标模型"""
    portfolio_value: Decimal = Field(..., description="投资组合价值")
    total_exposure: Decimal = Field(..., description="总敞口")
    max_drawdown: Decimal = Field(..., description="最大回撤")
    var_1d: Decimal = Field(..., description="1日风险价值")
    var_5d: Decimal = Field(..., description="5日风险价值")
    cvar_1d: Decimal = Field(..., description="1日条件风险价值")
    cvar_5d: Decimal = Field(..., description="5日条件风险价值")
    sharpe_ratio: Decimal = Field(..., description="夏普比率")
    sortino_ratio: Decimal = Field(..., description="索提诺比率")
    beta: Decimal = Field(..., description="贝塔系数")
    alpha: Decimal = Field(..., description="阿尔法系数")
    volatility: Decimal = Field(..., description="波动率")
    correlation: Dict[str, Decimal] = Field(..., description="相关性")
    timestamp: datetime = Field(..., description="时间戳")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class RiskLimit(BaseModel):
    """风险限制模型"""
    limit_id: str = Field(..., description="限制ID")
    name: str = Field(..., description="限制名称")
    description: str = Field(..., description="限制描述")
    risk_type: RiskType = Field(..., description="风险类型")
    metric_name: str = Field(..., description="指标名称")
    limit_value: Decimal = Field(..., description="限制值")
    current_value: Decimal = Field(..., description="当前值")
    utilization: Decimal = Field(..., description="利用率")
    threshold_warning: Decimal = Field(..., description="警告阈值")
    threshold_critical: Decimal = Field(..., description="严重阈值")
    action: RiskControlAction = Field(..., description="控制行为")
    is_active: bool = Field(..., description="是否激活")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class CreateRiskLimitRequest(BaseModel):
    """创建风险限制请求模型"""
    name: str = Field(..., min_length=1, max_length=100, description="限制名称")
    description: str = Field(..., min_length=1, max_length=500, description="限制描述")
    risk_type: RiskType = Field(..., description="风险类型")
    metric_name: str = Field(..., description="指标名称")
    limit_value: Decimal = Field(..., gt=0, description="限制值")
    threshold_warning: Decimal = Field(..., gt=0, le=1, description="警告阈值")
    threshold_critical: Decimal = Field(..., gt=0, le=1, description="严重阈值")
    action: RiskControlAction = Field(..., description="控制行为")
    
    @validator('threshold_critical')
    def validate_thresholds(cls, v, values):
        if v and values.get('threshold_warning') and v <= values['threshold_warning']:
            raise ValueError('严重阈值必须大于警告阈值')
        return v


class UpdateRiskLimitRequest(BaseModel):
    """更新风险限制请求模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="限制名称")
    description: Optional[str] = Field(None, min_length=1, max_length=500, description="限制描述")
    limit_value: Optional[Decimal] = Field(None, gt=0, description="限制值")
    threshold_warning: Optional[Decimal] = Field(None, gt=0, le=1, description="警告阈值")
    threshold_critical: Optional[Decimal] = Field(None, gt=0, le=1, description="严重阈值")
    action: Optional[RiskControlAction] = Field(None, description="控制行为")
    is_active: Optional[bool] = Field(None, description="是否激活")


class RiskAlert(BaseModel):
    """风险告警模型"""
    alert_id: str = Field(..., description="告警ID")
    limit_id: str = Field(..., description="限制ID")
    risk_type: RiskType = Field(..., description="风险类型")
    level: RiskLevel = Field(..., description="风险级别")
    message: str = Field(..., description="告警消息")
    metric_name: str = Field(..., description="指标名称")
    current_value: Decimal = Field(..., description="当前值")
    limit_value: Decimal = Field(..., description="限制值")
    threshold_breached: Decimal = Field(..., description="突破阈值")
    action_taken: Optional[RiskControlAction] = Field(None, description="采取的行为")
    is_resolved: bool = Field(default=False, description="是否已解决")
    created_at: datetime = Field(..., description="创建时间")
    resolved_at: Optional[datetime] = Field(None, description="解决时间")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class PositionRisk(BaseModel):
    """持仓风险模型"""
    symbol: str = Field(..., description="交易对符号")
    position_size: Decimal = Field(..., description="持仓规模")
    market_value: Decimal = Field(..., description="市场价值")
    exposure: Decimal = Field(..., description="敞口")
    leverage: Decimal = Field(..., description="杠杆")
    margin: Decimal = Field(..., description="保证金")
    unrealized_pnl: Decimal = Field(..., description="未实现盈亏")
    var_1d: Decimal = Field(..., description="1日风险价值")
    liquidation_price: Optional[Decimal] = Field(None, description="强平价格")
    risk_level: RiskLevel = Field(..., description="风险级别")
    concentration_risk: Decimal = Field(..., description="集中度风险")
    correlation_risk: Decimal = Field(..., description="相关性风险")
    timestamp: datetime = Field(..., description="时间戳")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class PortfolioRisk(BaseModel):
    """投资组合风险模型"""
    total_value: Decimal = Field(..., description="总价值")
    total_exposure: Decimal = Field(..., description="总敞口")
    diversification_ratio: Decimal = Field(..., description="分散化比率")
    concentration_index: Decimal = Field(..., description="集中度指数")
    var_1d: Decimal = Field(..., description="1日风险价值")
    var_5d: Decimal = Field(..., description="5日风险价值")
    expected_shortfall: Decimal = Field(..., description="预期缺口")
    max_drawdown: Decimal = Field(..., description="最大回撤")
    downside_deviation: Decimal = Field(..., description="下行偏差")
    positions: List[PositionRisk] = Field(..., description="持仓风险")
    timestamp: datetime = Field(..., description="时间戳")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class StressTestScenario(BaseModel):
    """压力测试场景模型"""
    scenario_id: str = Field(..., description="场景ID")
    name: str = Field(..., description="场景名称")
    description: str = Field(..., description="场景描述")
    market_shocks: Dict[str, Decimal] = Field(..., description="市场冲击")
    correlation_changes: Dict[str, Decimal] = Field(..., description="相关性变化")
    volatility_changes: Dict[str, Decimal] = Field(..., description="波动率变化")
    is_active: bool = Field(..., description="是否激活")
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class StressTestResult(BaseModel):
    """压力测试结果模型"""
    test_id: str = Field(..., description="测试ID")
    scenario_id: str = Field(..., description="场景ID")
    scenario_name: str = Field(..., description="场景名称")
    portfolio_value_before: Decimal = Field(..., description="测试前组合价值")
    portfolio_value_after: Decimal = Field(..., description="测试后组合价值")
    absolute_loss: Decimal = Field(..., description="绝对损失")
    relative_loss: Decimal = Field(..., description="相对损失")
    max_loss: Decimal = Field(..., description="最大损失")
    worst_position: str = Field(..., description="最差持仓")
    best_position: str = Field(..., description="最佳持仓")
    risk_level: RiskLevel = Field(..., description="风险级别")
    position_impacts: Dict[str, Decimal] = Field(..., description="持仓影响")
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class CreateStressTestRequest(BaseModel):
    """创建压力测试请求模型"""
    scenario_id: str = Field(..., description="场景ID")
    portfolio_snapshot: Optional[Dict[str, Any]] = Field(None, description="投资组合快照")
    custom_shocks: Optional[Dict[str, Decimal]] = Field(None, description="自定义冲击")


class RiskReport(BaseModel):
    """风险报告模型"""
    report_id: str = Field(..., description="报告ID")
    report_type: str = Field(..., description="报告类型")
    period_start: datetime = Field(..., description="报告期开始")
    period_end: datetime = Field(..., description="报告期结束")
    summary: Dict[str, Any] = Field(..., description="摘要")
    metrics: RiskMetrics = Field(..., description="风险指标")
    portfolio_risk: PortfolioRisk = Field(..., description="投资组合风险")
    stress_test_results: List[StressTestResult] = Field(..., description="压力测试结果")
    risk_alerts: List[RiskAlert] = Field(..., description="风险告警")
    recommendations: List[str] = Field(..., description="建议")
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class BacktestResult(BaseModel):
    """回测结果模型"""
    backtest_id: str = Field(..., description="回测ID")
    strategy_name: str = Field(..., description="策略名称")
    start_date: datetime = Field(..., description="开始日期")
    end_date: datetime = Field(..., description="结束日期")
    initial_capital: Decimal = Field(..., description="初始资本")
    final_capital: Decimal = Field(..., description="最终资本")
    total_return: Decimal = Field(..., description="总收益")
    annualized_return: Decimal = Field(..., description="年化收益")
    max_drawdown: Decimal = Field(..., description="最大回撤")
    sharpe_ratio: Decimal = Field(..., description="夏普比率")
    sortino_ratio: Decimal = Field(..., description="索提诺比率")
    win_rate: Decimal = Field(..., description="胜率")
    total_trades: int = Field(..., description="总交易数")
    winning_trades: int = Field(..., description="盈利交易数")
    losing_trades: int = Field(..., description="亏损交易数")
    average_win: Decimal = Field(..., description="平均盈利")
    average_loss: Decimal = Field(..., description="平均亏损")
    profit_factor: Decimal = Field(..., description="利润因子")
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }