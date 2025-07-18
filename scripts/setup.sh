#!/bin/bash

# AI智能交易大脑 - 环境设置脚本
# 用于初始化开发环境和配置

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 全局变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${PROJECT_DIR}/venv"
LOG_FILE="${PROJECT_DIR}/logs/setup.log"

# 确保日志目录存在
mkdir -p "${PROJECT_DIR}/logs"

# 日志函数
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "${LOG_FILE}"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "${LOG_FILE}"
}

log_warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "${LOG_FILE}"
}

log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO:${NC} $1" | tee -a "${LOG_FILE}"
}

# 显示帮助信息
show_help() {
    cat << EOF
AI智能交易大脑环境设置脚本

用法:
  $0 [选项]

选项:
  -h, --help     显示帮助信息
  -d, --dev      设置开发环境
  -t, --test     设置测试环境
  -p, --prod     设置生产环境
  -c, --clean    清理环境
  -u, --update   更新依赖

示例:
  $0 --dev       # 设置开发环境
  $0 --test      # 设置测试环境
  $0 --clean     # 清理环境

EOF
}

# 检查系统要求
check_system_requirements() {
    log_info "检查系统要求..."
    
    # 检查操作系统
    if [[ "$OSTYPE" == "darwin"* ]]; then
        log_info "检测到macOS系统"
        OS_TYPE="macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        log_info "检测到Linux系统"
        OS_TYPE="linux"
    else
        log_error "不支持的操作系统: $OSTYPE"
        exit 1
    fi
    
    # 检查Python版本
    if ! command -v python3 &> /dev/null; then
        log_error "Python3未安装，请先安装Python3"
        exit 1
    fi
    
    local python_version=$(python3 --version | cut -d' ' -f2)
    local python_major=$(echo $python_version | cut -d'.' -f1)
    local python_minor=$(echo $python_version | cut -d'.' -f2)
    
    if [ "$python_major" -lt 3 ] || [ "$python_major" -eq 3 -a "$python_minor" -lt 9 ]; then
        log_error "Python版本过低，需要Python 3.9+，当前版本: $python_version"
        exit 1
    fi
    
    log "Python版本检查通过: $python_version"
}

# 安装系统依赖
install_system_dependencies() {
    log_info "安装系统依赖..."
    
    if [[ "$OS_TYPE" == "macos" ]]; then
        # macOS使用Homebrew
        if ! command -v brew &> /dev/null; then
            log_info "安装Homebrew..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        
        # 安装依赖
        brew install postgresql redis git curl
        
    elif [[ "$OS_TYPE" == "linux" ]]; then
        # Linux使用包管理器
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y postgresql postgresql-client redis-server git curl build-essential
        elif command -v yum &> /dev/null; then
            sudo yum update -y
            sudo yum install -y postgresql postgresql-server redis git curl gcc gcc-c++ make
        else
            log_error "不支持的Linux发行版"
            exit 1
        fi
    fi
    
    log "系统依赖安装完成"
}

# 创建虚拟环境
create_virtual_environment() {
    log_info "创建Python虚拟环境..."
    
    cd "${PROJECT_DIR}"
    
    # 删除旧的虚拟环境
    if [ -d "${VENV_DIR}" ]; then
        log_info "删除旧的虚拟环境..."
        rm -rf "${VENV_DIR}"
    fi
    
    # 创建新的虚拟环境
    python3 -m venv "${VENV_DIR}"
    
    # 激活虚拟环境
    source "${VENV_DIR}/bin/activate"
    
    # 升级pip
    pip install --upgrade pip
    
    log "虚拟环境创建完成"
}

# 安装Python依赖
install_python_dependencies() {
    log_info "安装Python依赖..."
    
    cd "${PROJECT_DIR}"
    
    # 激活虚拟环境
    source "${VENV_DIR}/bin/activate"
    
    # 安装基础依赖
    pip install -r requirements.txt
    
    # 安装开发依赖
    if [ -f "requirements/dev.txt" ]; then
        pip install -r requirements/dev.txt
    fi
    
    # 安装测试依赖
    if [ -f "requirements/test.txt" ]; then
        pip install -r requirements/test.txt
    fi
    
    log "Python依赖安装完成"
}

# 设置数据库
setup_database() {
    log_info "设置数据库..."
    
    # 启动PostgreSQL服务
    if [[ "$OS_TYPE" == "macos" ]]; then
        brew services start postgresql
    elif [[ "$OS_TYPE" == "linux" ]]; then
        sudo systemctl start postgresql
        sudo systemctl enable postgresql
    fi
    
    # 等待PostgreSQL启动
    sleep 5
    
    # 创建数据库用户和数据库
    sudo -u postgres psql -c "CREATE USER trading_user WITH PASSWORD 'trading_password';" || true
    sudo -u postgres psql -c "CREATE DATABASE trading_db OWNER trading_user;" || true
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE trading_db TO trading_user;" || true
    
    log "数据库设置完成"
}

# 设置Redis
setup_redis() {
    log_info "设置Redis..."
    
    # 启动Redis服务
    if [[ "$OS_TYPE" == "macos" ]]; then
        brew services start redis
    elif [[ "$OS_TYPE" == "linux" ]]; then
        sudo systemctl start redis
        sudo systemctl enable redis
    fi
    
    # 等待Redis启动
    sleep 3
    
    # 测试Redis连接
    redis-cli ping
    
    log "Redis设置完成"
}

# 运行数据库迁移
run_database_migrations() {
    log_info "运行数据库迁移..."
    
    cd "${PROJECT_DIR}"
    
    # 激活虚拟环境
    source "${VENV_DIR}/bin/activate"
    
    # 初始化Alembic
    if [ ! -d "alembic" ]; then
        alembic init alembic
    fi
    
    # 运行迁移
    alembic upgrade head
    
    log "数据库迁移完成"
}

# 创建配置文件
create_config_files() {
    log_info "创建配置文件..."
    
    cd "${PROJECT_DIR}"
    
    # 创建环境变量文件
    if [ ! -f ".env" ]; then
        cat > .env << EOF
# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=trading_db
DB_USER=trading_user
DB_PASSWORD=trading_password

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# API配置
API_HOST=0.0.0.0
API_PORT=8000
JWT_SECRET=your-secret-key-here

# AI模型配置
OPENAI_API_KEY=your-openai-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# 交易所配置
BINANCE_API_KEY=your-binance-api-key-here
BINANCE_SECRET_KEY=your-binance-secret-key-here

# 日志配置
LOG_LEVEL=INFO
LOG_FORMAT=json

# 环境配置
ENVIRONMENT=development
EOF
        log "创建了.env文件，请根据需要修改配置"
    fi
    
    # 创建开发环境配置
    if [ ! -f ".env.development" ]; then
        cp .env .env.development
        sed -i.bak 's/ENVIRONMENT=development/ENVIRONMENT=development/' .env.development
        sed -i.bak 's/LOG_LEVEL=INFO/LOG_LEVEL=DEBUG/' .env.development
        rm .env.development.bak
    fi
    
    # 创建测试环境配置
    if [ ! -f ".env.test" ]; then
        cp .env .env.test
        sed -i.bak 's/ENVIRONMENT=development/ENVIRONMENT=test/' .env.test
        sed -i.bak 's/DB_NAME=trading_db/DB_NAME=trading_db_test/' .env.test
        rm .env.test.bak
    fi
    
    log "配置文件创建完成"
}

# 创建必要目录
create_directories() {
    log_info "创建必要目录..."
    
    cd "${PROJECT_DIR}"
    
    # 创建目录
    mkdir -p logs
    mkdir -p data
    mkdir -p backups
    mkdir -p monitoring/dashboards
    mkdir -p monitoring/alerts
    mkdir -p monitoring/metrics
    
    log "目录创建完成"
}

# 设置Git钩子
setup_git_hooks() {
    log_info "设置Git钩子..."
    
    cd "${PROJECT_DIR}"
    
    # 创建pre-commit钩子
    cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Pre-commit hook for code quality checks

# 激活虚拟环境
source venv/bin/activate

# 运行代码格式检查
echo "Running code format check..."
black --check src/
if [ $? -ne 0 ]; then
    echo "Code format check failed. Please run: black src/"
    exit 1
fi

# 运行import排序检查
echo "Running import sort check..."
isort --check-only src/
if [ $? -ne 0 ]; then
    echo "Import sort check failed. Please run: isort src/"
    exit 1
fi

# 运行类型检查
echo "Running type check..."
mypy src/
if [ $? -ne 0 ]; then
    echo "Type check failed. Please fix type issues."
    exit 1
fi

# 运行单元测试
echo "Running unit tests..."
python -m pytest tests/unit/ -v
if [ $? -ne 0 ]; then
    echo "Unit tests failed. Please fix failing tests."
    exit 1
fi

echo "All checks passed!"
EOF
    
    chmod +x .git/hooks/pre-commit
    
    log "Git钩子设置完成"
}

# 运行初始化测试
run_initialization_tests() {
    log_info "运行初始化测试..."
    
    cd "${PROJECT_DIR}"
    
    # 激活虚拟环境
    source "${VENV_DIR}/bin/activate"
    
    # 运行基础测试
    python -m pytest tests/unit/ -v --tb=short
    
    log "初始化测试完成"
}

# 生成开发文档
generate_development_docs() {
    log_info "生成开发文档..."
    
    cd "${PROJECT_DIR}"
    
    # 激活虚拟环境
    source "${VENV_DIR}/bin/activate"
    
    # 生成API文档
    if command -v sphinx-build &> /dev/null; then
        sphinx-build -b html docs/ docs/_build/html
    fi
    
    log "开发文档生成完成"
}

# 清理环境
clean_environment() {
    log_info "清理环境..."
    
    cd "${PROJECT_DIR}"
    
    # 删除虚拟环境
    if [ -d "${VENV_DIR}" ]; then
        rm -rf "${VENV_DIR}"
    fi
    
    # 清理缓存
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete
    find . -type f -name "*.pyo" -delete
    
    # 清理日志
    rm -rf logs/*
    
    # 清理数据
    rm -rf data/*
    
    log "环境清理完成"
}

# 更新依赖
update_dependencies() {
    log_info "更新依赖..."
    
    cd "${PROJECT_DIR}"
    
    # 激活虚拟环境
    source "${VENV_DIR}/bin/activate"
    
    # 更新pip
    pip install --upgrade pip
    
    # 更新Python依赖
    pip install --upgrade -r requirements.txt
    
    # 更新开发依赖
    if [ -f "requirements/dev.txt" ]; then
        pip install --upgrade -r requirements/dev.txt
    fi
    
    log "依赖更新完成"
}

# 设置开发环境
setup_development_environment() {
    log_info "设置开发环境..."
    
    check_system_requirements
    install_system_dependencies
    create_virtual_environment
    install_python_dependencies
    setup_database
    setup_redis
    create_config_files
    create_directories
    run_database_migrations
    setup_git_hooks
    run_initialization_tests
    generate_development_docs
    
    log "开发环境设置完成"
}

# 设置测试环境
setup_test_environment() {
    log_info "设置测试环境..."
    
    check_system_requirements
    create_virtual_environment
    install_python_dependencies
    setup_database
    setup_redis
    create_config_files
    create_directories
    run_database_migrations
    
    log "测试环境设置完成"
}

# 设置生产环境
setup_production_environment() {
    log_info "设置生产环境..."
    
    check_system_requirements
    create_virtual_environment
    install_python_dependencies
    create_config_files
    create_directories
    
    log "生产环境设置完成"
}

# 主函数
main() {
    log "开始执行环境设置脚本..."
    
    # 解析命令行参数
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        -d|--dev)
            setup_development_environment
            ;;
        -t|--test)
            setup_test_environment
            ;;
        -p|--prod)
            setup_production_environment
            ;;
        -c|--clean)
            clean_environment
            ;;
        -u|--update)
            update_dependencies
            ;;
        *)
            log_info "未指定选项，默认设置开发环境"
            setup_development_environment
            ;;
    esac
    
    log "环境设置脚本执行完成"
}

# 脚本入口
main "$@"