#!/usr/bin/env python3
"""
pytest配置文件
包含集成测试的共享固定数据和配置
"""

import pytest
import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.integration.test_data_manager import TestDataManager


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_data_manager():
    """创建测试数据管理器"""
    manager = TestDataManager()
    yield manager
    manager.cleanup_test_data()


@pytest.fixture(scope="session")
def test_fixtures(test_data_manager):
    """创建测试固定数据"""
    return test_data_manager.create_test_fixtures()


@pytest.fixture
def sample_market_data(test_data_manager):
    """生成示例市场数据"""
    return test_data_manager.generate_market_data('BTC/USDT', 20)


@pytest.fixture
def sample_trade_data(test_data_manager):
    """生成示例交易数据"""
    return test_data_manager.generate_trade_data('BTC/USDT', 10)


@pytest.fixture
def sample_portfolio(test_data_manager):
    """生成示例投资组合"""
    return test_data_manager.generate_portfolio_data(['BTC/USDT', 'ETH/USDT'])


@pytest.fixture
def sample_users(test_data_manager):
    """生成示例用户数据"""
    return test_data_manager.generate_user_data(5)


@pytest.fixture
def sample_orders(test_data_manager):
    """生成示例订单数据"""
    return test_data_manager.generate_order_data('BTC/USDT', 15)


@pytest.fixture
def sample_system_metrics(test_data_manager):
    """生成示例系统指标"""
    return test_data_manager.generate_system_metrics(30)


@pytest.fixture
def sample_ai_analysis(test_data_manager):
    """生成示例AI分析数据"""
    return test_data_manager.generate_ai_analysis_data('BTC/USDT', 10)


@pytest.fixture
def mock_database_config():
    """模拟数据库配置"""
    return {
        'host': 'localhost',
        'port': 5432,
        'database': 'test_trading_db',
        'username': 'test_user',
        'password': 'test_password',
        'schema': 'test_schema'
    }


@pytest.fixture
def mock_api_config():
    """模拟API配置"""
    return {
        'base_url': 'https://api.test.com',
        'api_key': 'test_api_key',
        'secret_key': 'test_secret_key',
        'timeout': 30,
        'max_retries': 3
    }


@pytest.fixture
def mock_redis_config():
    """模拟Redis配置"""
    return {
        'host': 'localhost',
        'port': 6379,
        'db': 0,
        'password': None,
        'decode_responses': True
    }


@pytest.fixture
def integration_test_config():
    """集成测试配置"""
    return {
        'test_duration': 60,
        'concurrent_users': 10,
        'max_response_time': 1.0,
        'max_error_rate': 0.01,
        'symbols': ['BTC/USDT', 'ETH/USDT', 'BNB/USDT'],
        'test_data_dir': '/tmp/integration_test_data'
    }


@pytest.fixture
async def market_data_stream(test_data_manager):
    """创建市场数据流"""
    return test_data_manager.create_market_data_stream('BTC/USDT', 0.1)


@pytest.fixture
async def trading_simulation(test_data_manager):
    """创建交易模拟"""
    return await test_data_manager.simulate_trading_scenario('normal_market', 30)


# 测试环境清理
@pytest.fixture(autouse=True)
def cleanup_test_environment():
    """自动清理测试环境"""
    yield
    # 清理临时文件
    test_dirs = ['/tmp/test_data', '/tmp/integration_test_data']
    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            import shutil
            shutil.rmtree(test_dir, ignore_errors=True)


# 标记配置
pytest_plugins = []

# 测试标记
def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )
    config.addinivalue_line(
        "markers", "stability: mark test as stability test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


# 测试收集配置
def pytest_collection_modifyitems(config, items):
    """修改测试收集"""
    for item in items:
        # 为集成测试添加标记
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        
        # 为性能测试添加标记
        if "performance" in item.nodeid:
            item.add_marker(pytest.mark.performance)
            item.add_marker(pytest.mark.slow)
        
        # 为稳定性测试添加标记
        if "stability" in item.nodeid:
            item.add_marker(pytest.mark.stability)
            item.add_marker(pytest.mark.slow)
        
        # 为端到端测试添加标记
        if "e2e" in item.nodeid:
            item.add_marker(pytest.mark.e2e)
            item.add_marker(pytest.mark.slow)