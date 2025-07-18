#!/bin/bash
set -e

# AI智能交易大脑 - Docker入口脚本

# 环境变量设置
export PYTHONPATH=/app:$PYTHONPATH

# 日志配置
LOG_LEVEL=${LOG_LEVEL:-INFO}
LOG_FORMAT=${LOG_FORMAT:-json}

# 数据库配置
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_NAME=${DB_NAME:-trading_db}
DB_USER=${DB_USER:-trading_user}

# Redis配置
REDIS_HOST=${REDIS_HOST:-localhost}
REDIS_PORT=${REDIS_PORT:-6379}

# 服务配置
SERVICE_TYPE=${SERVICE_TYPE:-api}
API_HOST=${API_HOST:-0.0.0.0}
API_PORT=${API_PORT:-8000}
API_WORKERS=${API_WORKERS:-4}

# 创建必要目录
mkdir -p /app/logs /app/data

# 等待数据库连接
wait_for_db() {
    echo "Waiting for database connection..."
    while ! nc -z $DB_HOST $DB_PORT; do
        sleep 1
    done
    echo "Database is ready!"
}

# 等待Redis连接
wait_for_redis() {
    echo "Waiting for Redis connection..."
    while ! nc -z $REDIS_HOST $REDIS_PORT; do
        sleep 1
    done
    echo "Redis is ready!"
}

# 数据库迁移
run_migrations() {
    echo "Running database migrations..."
    python -m alembic upgrade head
}

# 初始化数据
init_data() {
    echo "Initializing data..."
    python -c "
from src.data.storage.data_storage import DataStorage
import asyncio

async def init():
    storage = DataStorage()
    await storage.initialize()
    print('Data initialization completed')

asyncio.run(init())
"
}

# 启动API服务
start_api() {
    echo "Starting API service..."
    exec python -m uvicorn src.api.main:app \
        --host $API_HOST \
        --port $API_PORT \
        --workers $API_WORKERS \
        --log-level $LOG_LEVEL
}

# 启动工作进程
start_worker() {
    echo "Starting worker process..."
    exec python main.py
}

# 启动监控服务
start_monitoring() {
    echo "Starting monitoring service..."
    exec python -m src.monitoring.system_monitor
}

# 启动数据收集器
start_collector() {
    echo "Starting data collector..."
    exec python -m src.data.collectors.collector_manager
}

# 启动AI分析器
start_analyzer() {
    echo "Starting AI analyzer..."
    exec python -m src.ai.reasoning.market_analyzer
}

# 运行测试
run_tests() {
    echo "Running tests..."
    python -m pytest tests/ -v --cov=src --cov-report=html
}

# 健康检查
health_check() {
    case $SERVICE_TYPE in
        api)
            curl -f http://localhost:$API_PORT/health || exit 1
            ;;
        worker)
            python -c "
import sys
from src.monitoring.system_monitor import SystemMonitor
monitor = SystemMonitor()
if monitor.is_healthy():
    sys.exit(0)
else:
    sys.exit(1)
"
            ;;
        *)
            echo "Service is running"
            ;;
    esac
}

# 主函数
main() {
    echo "Starting AI智能交易大脑..."
    echo "Service Type: $SERVICE_TYPE"
    echo "Log Level: $LOG_LEVEL"
    
    # 等待依赖服务
    wait_for_db
    wait_for_redis
    
    # 根据服务类型启动相应服务
    case $SERVICE_TYPE in
        api)
            run_migrations
            init_data
            start_api
            ;;
        worker)
            start_worker
            ;;
        monitoring)
            start_monitoring
            ;;
        collector)
            start_collector
            ;;
        analyzer)
            start_analyzer
            ;;
        test)
            run_tests
            ;;
        migrate)
            run_migrations
            ;;
        init)
            init_data
            ;;
        health)
            health_check
            ;;
        *)
            echo "Unknown service type: $SERVICE_TYPE"
            echo "Available types: api, worker, monitoring, collector, analyzer, test, migrate, init, health"
            exit 1
            ;;
    esac
}

# 信号处理
handle_signal() {
    echo "Received signal, shutting down gracefully..."
    # 这里可以添加优雅关闭的逻辑
    exit 0
}

# 注册信号处理器
trap handle_signal SIGTERM SIGINT

# 如果没有参数，运行主函数
if [ $# -eq 0 ]; then
    main
else
    # 执行传入的命令
    exec "$@"
fi