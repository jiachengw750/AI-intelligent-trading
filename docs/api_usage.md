# AI智能交易大脑API使用文档

## 概述

AI智能交易大脑API是一个专业的量化交易平台接口，提供完整的交易、风险管理、投资组合管理和系统监控功能。

## 快速开始

### 1. 启动API服务

```bash
# 方式1：使用启动脚本
python run_api.py

# 方式2：使用uvicorn直接启动
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# 方式3：生产环境启动
python run_api.py --env production --workers 4 --port 8000
```

### 2. 访问API文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

### 3. 基本信息

- API根路径: http://localhost:8000/
- 健康检查: http://localhost:8000/health
- 版本信息: http://localhost:8000/version

## 认证和授权

### 用户登录

```python
import httpx

async def login():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/auth/login",
            json={
                "username": "admin",
                "password": "admin123"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            access_token = data["access_token"]
            refresh_token = data["refresh_token"]
            return access_token, refresh_token
        else:
            raise Exception("登录失败")
```

### 使用访问令牌

```python
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

response = await client.get(
    "http://localhost:8000/api/v1/auth/me",
    headers=headers
)
```

### API密钥认证

```python
# 创建API密钥
response = await client.post(
    "http://localhost:8000/api/v1/auth/api-keys",
    json={
        "name": "Trading Bot",
        "permissions": ["trading:read", "trading:create"]
    },
    headers=headers
)

# 使用API密钥
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}
```

## 主要功能模块

### 1. 交易管理 (/api/v1/trading)

#### 创建订单

```python
order_data = {
    "symbol": "BTC/USDT",
    "side": "buy",
    "type": "limit",
    "quantity": "0.1",
    "price": "50000",
    "time_in_force": "GTC"
}

response = await client.post(
    "http://localhost:8000/api/v1/trading/orders",
    json=order_data,
    headers=headers
)
```

#### 获取订单列表

```python
params = {
    "symbol": "BTC/USDT",
    "status": "open",
    "page": 1,
    "page_size": 20
}

response = await client.get(
    "http://localhost:8000/api/v1/trading/orders",
    params=params,
    headers=headers
)
```

#### 取消订单

```python
response = await client.delete(
    f"http://localhost:8000/api/v1/trading/orders/{order_id}",
    headers=headers
)
```

#### 获取持仓信息

```python
response = await client.get(
    "http://localhost:8000/api/v1/trading/positions",
    headers=headers
)
```

#### 获取账户余额

```python
response = await client.get(
    "http://localhost:8000/api/v1/trading/balances",
    headers=headers
)
```

### 2. 投资组合管理 (/api/v1/portfolio)

#### 创建投资组合

```python
portfolio_data = {
    "name": "主要投资组合",
    "type": "main",
    "initial_balance": "100000",
    "base_currency": "USDT"
}

response = await client.post(
    "http://localhost:8000/api/v1/portfolio/portfolios",
    json=portfolio_data,
    headers=headers
)
```

#### 获取投资组合列表

```python
response = await client.get(
    "http://localhost:8000/api/v1/portfolio/portfolios",
    headers=headers
)
```

#### 获取投资组合详情

```python
response = await client.get(
    f"http://localhost:8000/api/v1/portfolio/portfolios/{portfolio_id}",
    headers=headers
)
```

#### 获取投资组合表现

```python
params = {
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-12-31T23:59:59Z"
}

response = await client.get(
    f"http://localhost:8000/api/v1/portfolio/portfolios/{portfolio_id}/performance",
    params=params,
    headers=headers
)
```

#### 投资组合再平衡

```python
rebalance_data = {
    "portfolio_id": portfolio_id,
    "method": "threshold",
    "threshold": "5",
    "max_trades": 10,
    "dry_run": True
}

response = await client.post(
    f"http://localhost:8000/api/v1/portfolio/portfolios/{portfolio_id}/rebalance",
    json=rebalance_data,
    headers=headers
)
```

### 3. 风险管理 (/api/v1/risk)

#### 获取风险指标

```python
response = await client.get(
    "http://localhost:8000/api/v1/risk/metrics",
    headers=headers
)
```

#### 获取投资组合风险

```python
response = await client.get(
    "http://localhost:8000/api/v1/risk/portfolio",
    headers=headers
)
```

#### 创建风险限制

```python
risk_limit_data = {
    "name": "最大仓位限制",
    "description": "单个交易对最大仓位不超过10%",
    "risk_type": "market",
    "metric_name": "position_concentration",
    "limit_value": "0.1",
    "threshold_warning": "0.8",
    "threshold_critical": "0.9",
    "action": "alert"
}

response = await client.post(
    "http://localhost:8000/api/v1/risk/limits",
    json=risk_limit_data,
    headers=headers
)
```

#### 运行压力测试

```python
stress_test_data = {
    "scenario_id": "market_crash",
    "custom_shocks": {
        "BTC": "-0.3",
        "ETH": "-0.35"
    }
}

response = await client.post(
    "http://localhost:8000/api/v1/risk/stress-test/run",
    json=stress_test_data,
    headers=headers
)
```

### 4. 系统监控 (/api/v1/monitoring)

#### 获取系统健康状况

```python
response = await client.get(
    "http://localhost:8000/api/v1/monitoring/health",
    headers=headers
)
```

#### 获取系统指标

```python
response = await client.get(
    "http://localhost:8000/api/v1/monitoring/metrics/system",
    headers=headers
)
```

#### 获取交易指标

```python
response = await client.get(
    "http://localhost:8000/api/v1/monitoring/metrics/trading",
    headers=headers
)
```

#### 查询指标数据

```python
metric_query = {
    "metric_name": "cpu_usage",
    "start_time": "2024-01-01T00:00:00Z",
    "end_time": "2024-01-02T00:00:00Z",
    "interval": "1m",
    "aggregation": "avg"
}

response = await client.post(
    "http://localhost:8000/api/v1/monitoring/metrics/query",
    json=metric_query,
    headers=headers
)
```

#### 创建告警规则

```python
alert_data = {
    "name": "CPU使用率过高",
    "description": "CPU使用率超过90%时触发告警",
    "metric_name": "cpu_usage",
    "threshold": "90",
    "condition": ">",
    "level": "warning",
    "enabled": True
}

response = await client.post(
    "http://localhost:8000/api/v1/monitoring/alerts",
    json=alert_data,
    headers=headers
)
```

## 错误处理

### 标准错误响应格式

```json
{
    "status": "error",
    "message": "错误描述",
    "data": null,
    "timestamp": "2024-01-01T00:00:00Z",
    "error_code": "ERROR_CODE",
    "error_details": {
        "type": "ValidationError",
        "message": "详细错误信息"
    }
}
```

### 常见错误代码

- `400` - 请求参数错误
- `401` - 未授权，需要登录
- `403` - 权限不足
- `404` - 资源不存在
- `429` - 请求过于频繁，触发限流
- `500` - 服务器内部错误

### 错误处理示例

```python
try:
    response = await client.post(url, json=data, headers=headers)
    response.raise_for_status()
    result = response.json()
    
    if result["status"] == "error":
        print(f"API错误: {result['message']}")
        if "error_code" in result:
            print(f"错误代码: {result['error_code']}")
    else:
        return result["data"]
        
except httpx.HTTPStatusError as e:
    print(f"HTTP错误: {e.response.status_code}")
    print(f"响应内容: {e.response.text}")
except httpx.RequestError as e:
    print(f"请求错误: {e}")
```

## 限流机制

### 限流规则

- 全局限流：每分钟1000次请求
- API限流：每分钟100次请求
- 交易限流：每分钟50次请求
- 登录限流：每5分钟5次请求

### 限流响应头

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
Retry-After: 60
```

### 处理限流

```python
if response.status_code == 429:
    retry_after = int(response.headers.get("Retry-After", 60))
    print(f"请求过于频繁，请等待{retry_after}秒后重试")
    await asyncio.sleep(retry_after)
    # 重试请求
```

## 分页处理

### 分页参数

```python
params = {
    "page": 1,
    "page_size": 20
}
```

### 分页响应

```json
{
    "status": "success",
    "message": "获取数据成功",
    "data": [...],
    "pagination": {
        "total": 100,
        "page": 1,
        "page_size": 20,
        "total_pages": 5,
        "has_next": true,
        "has_prev": false
    }
}
```

## 实时数据

### WebSocket连接

```python
import websockets
import json

async def websocket_client():
    uri = "ws://localhost:8000/ws"
    
    async with websockets.connect(uri) as websocket:
        # 订阅实时数据
        subscribe_msg = {
            "action": "subscribe",
            "channels": ["orders", "positions", "market_data"]
        }
        await websocket.send(json.dumps(subscribe_msg))
        
        # 接收实时数据
        async for message in websocket:
            data = json.loads(message)
            print(f"收到实时数据: {data}")
```

## 最佳实践

### 1. 连接管理

```python
class APIClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = httpx.AsyncClient(
            base_url=base_url,
            timeout=30.0,
            limits=httpx.Limits(max_connections=100)
        )
    
    async def close(self):
        await self.session.aclose()
```

### 2. 错误重试

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def api_call_with_retry(client, method, url, **kwargs):
    response = await client.request(method, url, **kwargs)
    response.raise_for_status()
    return response.json()
```

### 3. 批量操作

```python
# 批量创建订单
orders = [
    {"symbol": "BTC/USDT", "side": "buy", "type": "limit", "quantity": "0.1", "price": "50000"},
    {"symbol": "ETH/USDT", "side": "buy", "type": "limit", "quantity": "1.0", "price": "3000"}
]

response = await client.post(
    "http://localhost:8000/api/v1/trading/orders/batch",
    json={"orders": orders},
    headers=headers
)
```

### 4. 数据缓存

```python
import time
from functools import wraps

def cache_result(expire_time=300):
    def decorator(func):
        cache = {}
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            now = time.time()
            
            if key in cache and now - cache[key]["time"] < expire_time:
                return cache[key]["data"]
            
            result = await func(*args, **kwargs)
            cache[key] = {"data": result, "time": now}
            return result
        
        return wrapper
    return decorator

@cache_result(expire_time=60)
async def get_market_data(symbol):
    # 获取市场数据
    pass
```

## 完整示例

参考 `examples/api_example.py` 文件获取完整的使用示例。

## 故障排除

### 1. 连接问题

```python
# 检查API服务是否启动
response = await client.get("http://localhost:8000/health")
print(response.json())
```

### 2. 认证问题

```python
# 检查令牌是否有效
response = await client.get(
    "http://localhost:8000/api/v1/auth/me",
    headers=headers
)
```

### 3. 权限问题

```python
# 检查用户权限
user_info = await client.get("http://localhost:8000/api/v1/auth/me", headers=headers)
permissions = user_info["data"]["permissions"]
print(f"用户权限: {permissions}")
```

## 支持

如需技术支持，请联系：

- 邮箱：support@ai-trading-brain.com
- 文档：http://localhost:8000/docs
- GitHub：https://github.com/ai-trading-brain/api