#!/usr/bin/env python3
"""
AI智能交易大脑API使用示例
"""
import asyncio
import httpx
import json
from typing import Dict, Any, Optional
from datetime import datetime


class APIClient:
    """API客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url)
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers
    
    async def login(self, username: str, password: str) -> Dict[str, Any]:
        """登录"""
        data = {
            "username": username,
            "password": password
        }
        
        response = await self.client.post(
            "/api/v1/auth/login",
            json=data
        )
        
        if response.status_code == 200:
            result = response.json()
            self.access_token = result["access_token"]
            self.refresh_token = result["refresh_token"]
            print("✅ 登录成功")
            return result
        else:
            print(f"❌ 登录失败: {response.text}")
            return {}
    
    async def get_user_info(self) -> Dict[str, Any]:
        """获取用户信息"""
        response = await self.client.get(
            "/api/v1/auth/me",
            headers=self._get_headers()
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 获取用户信息成功")
            return result
        else:
            print(f"❌ 获取用户信息失败: {response.text}")
            return {}
    
    async def create_order(self, symbol: str, side: str, order_type: str, 
                          quantity: float, price: float = None) -> Dict[str, Any]:
        """创建订单"""
        data = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": str(quantity),
            "time_in_force": "GTC"
        }
        
        if price:
            data["price"] = str(price)
        
        response = await self.client.post(
            "/api/v1/trading/orders",
            json=data,
            headers=self._get_headers()
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 创建订单成功: {result['data']['order_id']}")
            return result
        else:
            print(f"❌ 创建订单失败: {response.text}")
            return {}
    
    async def get_orders(self, symbol: str = None, limit: int = 20) -> Dict[str, Any]:
        """获取订单列表"""
        params = {"page_size": limit}
        if symbol:
            params["symbol"] = symbol
        
        response = await self.client.get(
            "/api/v1/trading/orders",
            params=params,
            headers=self._get_headers()
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 获取订单列表成功: {len(result['data'])} 个订单")
            return result
        else:
            print(f"❌ 获取订单列表失败: {response.text}")
            return {}
    
    async def get_positions(self) -> Dict[str, Any]:
        """获取持仓信息"""
        response = await self.client.get(
            "/api/v1/trading/positions",
            headers=self._get_headers()
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 获取持仓信息成功: {len(result['data'])} 个持仓")
            return result
        else:
            print(f"❌ 获取持仓信息失败: {response.text}")
            return {}
    
    async def get_portfolios(self) -> Dict[str, Any]:
        """获取投资组合列表"""
        response = await self.client.get(
            "/api/v1/portfolio/portfolios",
            headers=self._get_headers()
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 获取投资组合列表成功: {len(result['data'])} 个投资组合")
            return result
        else:
            print(f"❌ 获取投资组合列表失败: {response.text}")
            return {}
    
    async def create_portfolio(self, name: str, initial_balance: float) -> Dict[str, Any]:
        """创建投资组合"""
        data = {
            "name": name,
            "type": "main",
            "initial_balance": str(initial_balance),
            "base_currency": "USDT"
        }
        
        response = await self.client.post(
            "/api/v1/portfolio/portfolios",
            json=data,
            headers=self._get_headers()
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 创建投资组合成功: {result['data']['portfolio_id']}")
            return result
        else:
            print(f"❌ 创建投资组合失败: {response.text}")
            return {}
    
    async def get_risk_metrics(self) -> Dict[str, Any]:
        """获取风险指标"""
        response = await self.client.get(
            "/api/v1/risk/metrics",
            headers=self._get_headers()
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 获取风险指标成功")
            return result
        else:
            print(f"❌ 获取风险指标失败: {response.text}")
            return {}
    
    async def get_system_health(self) -> Dict[str, Any]:
        """获取系统健康状况"""
        response = await self.client.get(
            "/api/v1/monitoring/health",
            headers=self._get_headers()
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 获取系统健康状况成功")
            return result
        else:
            print(f"❌ 获取系统健康状况失败: {response.text}")
            return {}


async def main():
    """主函数"""
    print("🚀 AI智能交易大脑API使用示例")
    print("=" * 60)
    
    async with APIClient() as client:
        # 1. 登录
        print("1. 用户登录")
        login_result = await client.login("admin", "admin123")
        if not login_result:
            print("登录失败，退出程序")
            return
        
        print(f"   访问令牌: {login_result['access_token'][:20]}...")
        print(f"   用户信息: {login_result['user_info']}")
        print()
        
        # 2. 获取用户信息
        print("2. 获取用户信息")
        user_info = await client.get_user_info()
        if user_info:
            print(f"   用户ID: {user_info['data']['id']}")
            print(f"   用户名: {user_info['data']['username']}")
            print(f"   角色: {user_info['data']['role']}")
            print(f"   权限: {len(user_info['data']['permissions'])} 个权限")
        print()
        
        # 3. 创建订单
        print("3. 创建交易订单")
        order_result = await client.create_order(
            symbol="BTC/USDT",
            side="buy",
            order_type="limit",
            quantity=0.1,
            price=50000
        )
        if order_result:
            print(f"   订单ID: {order_result['data']['order_id']}")
            print(f"   交易对: {order_result['data']['symbol']}")
            print(f"   订单类型: {order_result['data']['type']}")
            print(f"   数量: {order_result['data']['quantity']}")
            print(f"   价格: {order_result['data']['price']}")
        print()
        
        # 4. 获取订单列表
        print("4. 获取订单列表")
        orders = await client.get_orders(limit=5)
        if orders:
            print(f"   总数: {len(orders['data'])} 个订单")
            for order in orders['data'][:3]:  # 显示前3个
                print(f"   - {order['order_id']}: {order['symbol']} {order['side']} {order['status']}")
        print()
        
        # 5. 获取持仓信息
        print("5. 获取持仓信息")
        positions = await client.get_positions()
        if positions:
            print(f"   总数: {len(positions['data'])} 个持仓")
            for position in positions['data'][:3]:  # 显示前3个
                print(f"   - {position['symbol']}: {position['side']} {position['size']} ({position['unrealized_pnl']} PnL)")
        print()
        
        # 6. 创建投资组合
        print("6. 创建投资组合")
        portfolio_result = await client.create_portfolio(
            name="测试投资组合",
            initial_balance=100000
        )
        if portfolio_result:
            print(f"   投资组合ID: {portfolio_result['data']['portfolio_id']}")
            print(f"   名称: {portfolio_result['data']['name']}")
            print(f"   总价值: {portfolio_result['data']['total_value']}")
        print()
        
        # 7. 获取投资组合列表
        print("7. 获取投资组合列表")
        portfolios = await client.get_portfolios()
        if portfolios:
            print(f"   总数: {len(portfolios['data'])} 个投资组合")
            for portfolio in portfolios['data'][:3]:  # 显示前3个
                print(f"   - {portfolio['portfolio_id']}: {portfolio['name']} ({portfolio['total_value']})")
        print()
        
        # 8. 获取风险指标
        print("8. 获取风险指标")
        risk_metrics = await client.get_risk_metrics()
        if risk_metrics:
            data = risk_metrics['data']
            print(f"   投资组合价值: {data['portfolio_value']}")
            print(f"   总敞口: {data['total_exposure']}")
            print(f"   最大回撤: {data['max_drawdown']}")
            print(f"   1日VaR: {data['var_1d']}")
            print(f"   夏普比率: {data['sharpe_ratio']}")
        print()
        
        # 9. 获取系统健康状况
        print("9. 获取系统健康状况")
        health = await client.get_system_health()
        if health:
            print(f"   整体状态: {health['overall_status']}")
            print(f"   服务数量: {len(health['services'])} 个服务")
            for service in health['services']:
                print(f"   - {service['service_name']}: {service['status']} ({service['message']})")
        print()
        
        print("✅ 所有API调用完成！")


if __name__ == "__main__":
    asyncio.run(main())