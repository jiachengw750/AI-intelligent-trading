"""
基础数据模式定义
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, Union, Any, Dict, List
from datetime import datetime
from decimal import Decimal
from enum import Enum


class ResponseStatus(str, Enum):
    """响应状态枚举"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"


class BaseResponse(BaseModel):
    """基础响应模型"""
    status: ResponseStatus = ResponseStatus.SUCCESS
    message: str = "操作成功"
    data: Optional[Union[Dict[str, Any], List[Any], Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ErrorResponse(BaseResponse):
    """错误响应模型"""
    status: ResponseStatus = ResponseStatus.ERROR
    error_code: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页大小")
    
    @property
    def skip(self) -> int:
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        return self.page_size


class PaginatedResponse(BaseResponse):
    """分页响应模型"""
    pagination: Dict[str, Any] = Field(default_factory=dict)
    
    def set_pagination(self, total: int, page: int, page_size: int):
        """设置分页信息"""
        self.pagination = {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "has_next": page * page_size < total,
            "has_prev": page > 1
        }


class DateRangeFilter(BaseModel):
    """日期范围过滤器"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        if v and values.get('start_date') and v < values['start_date']:
            raise ValueError('结束日期不能早于开始日期')
        return v


class SortParams(BaseModel):
    """排序参数"""
    sort_by: str = Field(default="created_at", description="排序字段")
    sort_order: str = Field(default="desc", regex="^(asc|desc)$", description="排序顺序")