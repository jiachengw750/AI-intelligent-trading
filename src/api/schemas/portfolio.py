"""
投资组合相关数据模式
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from decimal import Decimal
from enum import Enum


class AssetType(str, Enum):
    """资产类型枚举"""
    SPOT = "spot"
    FUTURES = "futures"
    OPTIONS = "options"
    PERPETUAL = "perpetual"
    MARGIN = "margin"


class PortfolioType(str, Enum):
    """投资组合类型枚举"""
    MAIN = "main"
    TRADING = "trading"
    MARGIN = "margin"
    FUTURES = "futures"
    OPTIONS = "options"


class HoldingInfo(BaseModel):
    """持仓信息模型"""
    symbol: str = Field(..., description="交易对符号")
    asset_type: AssetType = Field(..., description="资产类型")
    quantity: Decimal = Field(..., description="持仓数量")
    average_price: Decimal = Field(..., description="平均价格")
    current_price: Decimal = Field(..., description="当前价格")
    market_value: Decimal = Field(..., description="市场价值")
    unrealized_pnl: Decimal = Field(..., description="未实现盈亏")
    realized_pnl: Decimal = Field(..., description="已实现盈亏")
    percentage: Decimal = Field(..., description="占比")
    cost_basis: Decimal = Field(..., description="成本基础")
    last_updated: datetime = Field(..., description="最后更新时间")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class PortfolioInfo(BaseModel):
    """投资组合信息模型"""
    portfolio_id: str = Field(..., description="投资组合ID")
    name: str = Field(..., description="投资组合名称")
    type: PortfolioType = Field(..., description="投资组合类型")
    total_value: Decimal = Field(..., description="总价值")
    available_balance: Decimal = Field(..., description="可用余额")
    locked_balance: Decimal = Field(..., description="冻结余额")
    unrealized_pnl: Decimal = Field(..., description="未实现盈亏")
    realized_pnl: Decimal = Field(..., description="已实现盈亏")
    total_pnl: Decimal = Field(..., description="总盈亏")
    pnl_percentage: Decimal = Field(..., description="盈亏百分比")
    holdings: List[HoldingInfo] = Field(..., description="持仓列表")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class CreatePortfolioRequest(BaseModel):
    """创建投资组合请求模型"""
    name: str = Field(..., min_length=1, max_length=100, description="投资组合名称")
    type: PortfolioType = Field(..., description="投资组合类型")
    description: Optional[str] = Field(None, max_length=500, description="描述")
    initial_balance: Decimal = Field(..., gt=0, description="初始余额")
    base_currency: str = Field(default="USDT", description="基础货币")


class UpdatePortfolioRequest(BaseModel):
    """更新投资组合请求模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="投资组合名称")
    description: Optional[str] = Field(None, max_length=500, description="描述")
    is_active: Optional[bool] = Field(None, description="是否激活")


class PortfolioAllocation(BaseModel):
    """投资组合配置模型"""
    asset_class: str = Field(..., description="资产类别")
    symbol: str = Field(..., description="交易对符号")
    target_percentage: Decimal = Field(..., ge=0, le=100, description="目标百分比")
    current_percentage: Decimal = Field(..., ge=0, le=100, description="当前百分比")
    deviation: Decimal = Field(..., description="偏差")
    rebalance_needed: bool = Field(..., description="是否需要再平衡")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class PortfolioAllocationRequest(BaseModel):
    """投资组合配置请求模型"""
    allocations: List[PortfolioAllocation] = Field(..., description="配置列表")
    
    @validator('allocations')
    def validate_total_percentage(cls, v):
        total = sum(allocation.target_percentage for allocation in v)
        if total > 100:
            raise ValueError('总配置比例不能超过100%')
        return v


class PortfolioPerformance(BaseModel):
    """投资组合表现模型"""
    portfolio_id: str = Field(..., description="投资组合ID")
    period_start: datetime = Field(..., description="期间开始")
    period_end: datetime = Field(..., description="期间结束")
    initial_value: Decimal = Field(..., description="初始价值")
    final_value: Decimal = Field(..., description="最终价值")
    total_return: Decimal = Field(..., description="总收益")
    return_percentage: Decimal = Field(..., description="收益率")
    annualized_return: Decimal = Field(..., description="年化收益率")
    volatility: Decimal = Field(..., description="波动率")
    sharpe_ratio: Decimal = Field(..., description="夏普比率")
    max_drawdown: Decimal = Field(..., description="最大回撤")
    calmar_ratio: Decimal = Field(..., description="卡玛比率")
    sortino_ratio: Decimal = Field(..., description="索提诺比率")
    win_rate: Decimal = Field(..., description="胜率")
    best_day: Decimal = Field(..., description="最好的一天")
    worst_day: Decimal = Field(..., description="最坏的一天")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class PortfolioAnalysis(BaseModel):
    """投资组合分析模型"""
    portfolio_id: str = Field(..., description="投资组合ID")
    analysis_date: datetime = Field(..., description="分析日期")
    diversification_ratio: Decimal = Field(..., description="分散化比率")
    concentration_index: Decimal = Field(..., description="集中度指数")
    correlation_matrix: Dict[str, Dict[str, Decimal]] = Field(..., description="相关性矩阵")
    sector_allocation: Dict[str, Decimal] = Field(..., description="行业配置")
    geographic_allocation: Dict[str, Decimal] = Field(..., description="地理配置")
    market_cap_allocation: Dict[str, Decimal] = Field(..., description="市值配置")
    top_holdings: List[HoldingInfo] = Field(..., description="主要持仓")
    risk_metrics: Dict[str, Decimal] = Field(..., description="风险指标")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class RebalanceRecommendation(BaseModel):
    """再平衡建议模型"""
    symbol: str = Field(..., description="交易对符号")
    current_percentage: Decimal = Field(..., description="当前百分比")
    target_percentage: Decimal = Field(..., description="目标百分比")
    deviation: Decimal = Field(..., description="偏差")
    action: str = Field(..., description="建议行为")
    quantity_change: Decimal = Field(..., description="数量变化")
    estimated_cost: Decimal = Field(..., description="预估成本")
    priority: int = Field(..., description="优先级")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class RebalanceRequest(BaseModel):
    """再平衡请求模型"""
    portfolio_id: str = Field(..., description="投资组合ID")
    method: str = Field(default="threshold", description="再平衡方法")
    threshold: Decimal = Field(default=Decimal("5"), description="阈值")
    max_trades: int = Field(default=10, description="最大交易数")
    dry_run: bool = Field(default=True, description="是否为模拟运行")


class RebalanceResult(BaseModel):
    """再平衡结果模型"""
    rebalance_id: str = Field(..., description="再平衡ID")
    portfolio_id: str = Field(..., description="投资组合ID")
    execution_date: datetime = Field(..., description="执行日期")
    recommendations: List[RebalanceRecommendation] = Field(..., description="建议列表")
    total_trades: int = Field(..., description="总交易数")
    total_cost: Decimal = Field(..., description="总成本")
    status: str = Field(..., description="状态")
    executed_trades: int = Field(..., description="已执行交易数")
    failed_trades: int = Field(..., description="失败交易数")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class PortfolioTransaction(BaseModel):
    """投资组合交易模型"""
    transaction_id: str = Field(..., description="交易ID")
    portfolio_id: str = Field(..., description="投资组合ID")
    symbol: str = Field(..., description="交易对符号")
    transaction_type: str = Field(..., description="交易类型")
    quantity: Decimal = Field(..., description="数量")
    price: Decimal = Field(..., description="价格")
    value: Decimal = Field(..., description="价值")
    fee: Decimal = Field(..., description="手续费")
    timestamp: datetime = Field(..., description="时间戳")
    order_id: Optional[str] = Field(None, description="订单ID")
    notes: Optional[str] = Field(None, description="备注")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class PortfolioStatistics(BaseModel):
    """投资组合统计模型"""
    portfolio_id: str = Field(..., description="投资组合ID")
    total_assets: int = Field(..., description="总资产数")
    total_value: Decimal = Field(..., description="总价值")
    total_return: Decimal = Field(..., description="总收益")
    daily_return: Decimal = Field(..., description="日收益")
    monthly_return: Decimal = Field(..., description="月收益")
    yearly_return: Decimal = Field(..., description="年收益")
    max_drawdown: Decimal = Field(..., description="最大回撤")
    volatility: Decimal = Field(..., description="波动率")
    sharpe_ratio: Decimal = Field(..., description="夏普比率")
    total_trades: int = Field(..., description="总交易数")
    winning_trades: int = Field(..., description="盈利交易数")
    losing_trades: int = Field(..., description="亏损交易数")
    win_rate: Decimal = Field(..., description="胜率")
    average_win: Decimal = Field(..., description="平均盈利")
    average_loss: Decimal = Field(..., description="平均亏损")
    profit_factor: Decimal = Field(..., description="利润因子")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class PortfolioComparison(BaseModel):
    """投资组合比较模型"""
    portfolio_ids: List[str] = Field(..., description="投资组合ID列表")
    comparison_period: str = Field(..., description="比较期间")
    metrics: Dict[str, Dict[str, Decimal]] = Field(..., description="指标")
    rankings: Dict[str, List[str]] = Field(..., description="排名")
    analysis: Dict[str, Any] = Field(..., description="分析")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class PortfolioOptimization(BaseModel):
    """投资组合优化模型"""
    optimization_id: str = Field(..., description="优化ID")
    portfolio_id: str = Field(..., description="投资组合ID")
    optimization_type: str = Field(..., description="优化类型")
    objective: str = Field(..., description="目标")
    constraints: Dict[str, Any] = Field(..., description="约束")
    current_allocation: Dict[str, Decimal] = Field(..., description="当前配置")
    optimal_allocation: Dict[str, Decimal] = Field(..., description="最优配置")
    expected_return: Decimal = Field(..., description="预期收益")
    expected_risk: Decimal = Field(..., description="预期风险")
    improvement_score: Decimal = Field(..., description="改进得分")
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }