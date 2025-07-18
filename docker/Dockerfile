# AI智能交易大脑 - 多阶段Docker构建
FROM python:3.11-slim as base

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    pkg-config \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 升级pip
RUN pip install --upgrade pip

# 复制requirements文件
COPY requirements.txt ./

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 开发阶段
FROM base as development

# 安装开发依赖
COPY requirements/ ./requirements/
RUN pip install --no-cache-dir -r requirements/api.txt

# 复制源代码
COPY . .

# 创建非root用户
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --gid 1001 appuser

# 设置权限
RUN chown -R appuser:appgroup /app

# 切换到非root用户
USER appuser

# 暴露端口
EXPOSE 8000

# 开发模式启动命令
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# 生产构建阶段
FROM base as production-build

# 复制源代码
COPY . .

# 编译Python字节码
RUN python -m compileall src/

# 生产运行阶段
FROM python:3.11-slim as production

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装运行时依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制Python环境
COPY --from=base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=base /usr/local/bin /usr/local/bin

# 从构建阶段复制应用代码
COPY --from=production-build /app .

# 创建非root用户
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --gid 1001 appuser

# 创建必要的目录
RUN mkdir -p logs data && \
    chown -R appuser:appgroup /app

# 切换到非root用户
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000

# 生产模式启动命令
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# 测试阶段
FROM development as test

# 安装测试依赖
RUN pip install --no-cache-dir pytest pytest-asyncio pytest-cov pytest-mock

# 运行测试
RUN python -m pytest tests/ -v --cov=src --cov-report=html

# 测试命令
CMD ["python", "-m", "pytest", "tests/", "-v"]

# 监控阶段
FROM production as monitoring

# 安装监控工具
RUN pip install --no-cache-dir prometheus-client grafana-api

# 复制监控配置
COPY monitoring/ ./monitoring/

# 暴露监控端口
EXPOSE 9090

# 启动监控
CMD ["python", "-m", "src.monitoring.system_monitor"]