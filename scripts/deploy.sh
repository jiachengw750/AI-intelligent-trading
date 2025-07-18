#!/bin/bash

# AI智能交易大脑 - 自动化部署脚本
# 支持开发、测试、生产环境的一键部署

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
ENVIRONMENT=${1:-development}
ACTION=${2:-deploy}
BACKUP_DIR="${PROJECT_DIR}/backups"
LOG_FILE="${PROJECT_DIR}/logs/deploy.log"

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
AI智能交易大脑部署脚本

用法:
  $0 [环境] [操作]

环境:
  development  - 开发环境 (默认)
  test         - 测试环境
  production   - 生产环境

操作:
  deploy       - 部署应用 (默认)
  start        - 启动服务
  stop         - 停止服务
  restart      - 重启服务
  status       - 查看状态
  logs         - 查看日志
  backup       - 备份数据
  restore      - 恢复数据
  test         - 运行测试
  clean        - 清理资源
  update       - 更新应用
  rollback     - 回滚版本

示例:
  $0 development deploy    # 部署到开发环境
  $0 production start      # 启动生产环境
  $0 test logs             # 查看测试环境日志

EOF
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
    
    # 检查Docker是否运行
    if ! docker info &> /dev/null; then
        log_error "Docker服务未运行，请启动Docker服务"
        exit 1
    fi
    
    log "依赖检查通过"
}

# 设置环境变量
setup_environment() {
    log_info "设置环境变量..."
    
    # 根据环境加载不同的配置
    case $ENVIRONMENT in
        development)
            export COMPOSE_FILE="docker-compose.dev.yml"
            export COMPOSE_PROJECT_NAME="ai_trading_dev"
            ;;
        test)
            export COMPOSE_FILE="docker-compose.yml"
            export COMPOSE_PROJECT_NAME="ai_trading_test"
            ;;
        production)
            export COMPOSE_FILE="docker-compose.prod.yml"
            export COMPOSE_PROJECT_NAME="ai_trading_prod"
            ;;
        *)
            log_error "未知环境: $ENVIRONMENT"
            exit 1
            ;;
    esac
    
    # 加载环境变量文件
    if [ -f "${PROJECT_DIR}/.env.${ENVIRONMENT}" ]; then
        log_info "加载环境变量文件: .env.${ENVIRONMENT}"
        source "${PROJECT_DIR}/.env.${ENVIRONMENT}"
    elif [ -f "${PROJECT_DIR}/.env" ]; then
        log_info "加载默认环境变量文件: .env"
        source "${PROJECT_DIR}/.env"
    else
        log_warn "未找到环境变量文件"
    fi
    
    log "环境变量设置完成"
}

# 构建Docker镜像
build_images() {
    log_info "构建Docker镜像..."
    
    cd "${PROJECT_DIR}"
    
    # 构建镜像
    docker-compose -f ${COMPOSE_FILE} build --no-cache
    
    log "Docker镜像构建完成"
}

# 运行测试
run_tests() {
    log_info "运行测试..."
    
    cd "${PROJECT_DIR}"
    
    # 运行单元测试
    docker-compose -f ${COMPOSE_FILE} run --rm test python -m pytest tests/unit/ -v
    
    # 运行集成测试
    docker-compose -f ${COMPOSE_FILE} run --rm test python -m pytest tests/integration/ -v
    
    log "测试运行完成"
}

# 数据库迁移
run_migrations() {
    log_info "运行数据库迁移..."
    
    cd "${PROJECT_DIR}"
    
    # 等待数据库就绪
    docker-compose -f ${COMPOSE_FILE} up -d postgres
    sleep 10
    
    # 运行迁移
    docker-compose -f ${COMPOSE_FILE} run --rm api python -m alembic upgrade head
    
    log "数据库迁移完成"
}

# 部署应用
deploy_application() {
    log_info "部署应用..."
    
    cd "${PROJECT_DIR}"
    
    # 停止现有服务
    docker-compose -f ${COMPOSE_FILE} down
    
    # 拉取最新镜像
    docker-compose -f ${COMPOSE_FILE} pull
    
    # 构建镜像
    if [ "$ENVIRONMENT" = "development" ]; then
        build_images
    fi
    
    # 运行数据库迁移
    if [ "$ENVIRONMENT" != "development" ]; then
        run_migrations
    fi
    
    # 启动服务
    docker-compose -f ${COMPOSE_FILE} up -d
    
    # 等待服务就绪
    sleep 30
    
    # 检查服务状态
    check_service_health
    
    log "应用部署完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    cd "${PROJECT_DIR}"
    docker-compose -f ${COMPOSE_FILE} up -d
    
    log "服务启动完成"
}

# 停止服务
stop_services() {
    log_info "停止服务..."
    
    cd "${PROJECT_DIR}"
    docker-compose -f ${COMPOSE_FILE} down
    
    log "服务停止完成"
}

# 重启服务
restart_services() {
    log_info "重启服务..."
    
    stop_services
    sleep 5
    start_services
    
    log "服务重启完成"
}

# 查看服务状态
check_status() {
    log_info "检查服务状态..."
    
    cd "${PROJECT_DIR}"
    docker-compose -f ${COMPOSE_FILE} ps
    
    log "服务状态检查完成"
}

# 检查服务健康状态
check_service_health() {
    log_info "检查服务健康状态..."
    
    local retries=0
    local max_retries=10
    
    while [ $retries -lt $max_retries ]; do
        if curl -f http://localhost:8000/health &> /dev/null; then
            log "API服务健康检查通过"
            return 0
        fi
        
        log_warn "API服务健康检查失败，重试中... ($((retries + 1))/$max_retries)"
        sleep 10
        retries=$((retries + 1))
    done
    
    log_error "API服务健康检查失败"
    return 1
}

# 查看日志
view_logs() {
    log_info "查看日志..."
    
    cd "${PROJECT_DIR}"
    
    if [ -z "$3" ]; then
        docker-compose -f ${COMPOSE_FILE} logs -f
    else
        docker-compose -f ${COMPOSE_FILE} logs -f "$3"
    fi
}

# 备份数据
backup_data() {
    log_info "备份数据..."
    
    local backup_timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_path="${BACKUP_DIR}/${ENVIRONMENT}_${backup_timestamp}"
    
    mkdir -p "${backup_path}"
    
    cd "${PROJECT_DIR}"
    
    # 备份数据库
    docker-compose -f ${COMPOSE_FILE} exec postgres pg_dump -U trading_user trading_db > "${backup_path}/database.sql"
    
    # 备份Redis数据
    docker-compose -f ${COMPOSE_FILE} exec redis redis-cli BGSAVE
    docker cp $(docker-compose -f ${COMPOSE_FILE} ps -q redis):/data/dump.rdb "${backup_path}/redis_dump.rdb"
    
    # 备份应用数据
    cp -r "${PROJECT_DIR}/data" "${backup_path}/app_data"
    
    # 备份日志
    cp -r "${PROJECT_DIR}/logs" "${backup_path}/logs"
    
    # 压缩备份
    cd "${BACKUP_DIR}"
    tar -czf "${ENVIRONMENT}_${backup_timestamp}.tar.gz" "${ENVIRONMENT}_${backup_timestamp}"
    rm -rf "${ENVIRONMENT}_${backup_timestamp}"
    
    log "数据备份完成: ${ENVIRONMENT}_${backup_timestamp}.tar.gz"
}

# 恢复数据
restore_data() {
    log_info "恢复数据..."
    
    local backup_file="$3"
    
    if [ -z "$backup_file" ]; then
        log_error "请指定备份文件"
        exit 1
    fi
    
    if [ ! -f "${BACKUP_DIR}/${backup_file}" ]; then
        log_error "备份文件不存在: ${backup_file}"
        exit 1
    fi
    
    cd "${BACKUP_DIR}"
    
    # 解压备份
    tar -xzf "${backup_file}"
    local backup_dir=$(basename "${backup_file}" .tar.gz)
    
    # 停止服务
    stop_services
    
    # 恢复数据库
    cd "${PROJECT_DIR}"
    docker-compose -f ${COMPOSE_FILE} up -d postgres
    sleep 10
    
    docker-compose -f ${COMPOSE_FILE} exec -T postgres psql -U trading_user trading_db < "${BACKUP_DIR}/${backup_dir}/database.sql"
    
    # 恢复Redis数据
    docker-compose -f ${COMPOSE_FILE} up -d redis
    sleep 5
    
    docker cp "${BACKUP_DIR}/${backup_dir}/redis_dump.rdb" $(docker-compose -f ${COMPOSE_FILE} ps -q redis):/data/dump.rdb
    docker-compose -f ${COMPOSE_FILE} restart redis
    
    # 恢复应用数据
    rm -rf "${PROJECT_DIR}/data"
    cp -r "${BACKUP_DIR}/${backup_dir}/app_data" "${PROJECT_DIR}/data"
    
    # 启动服务
    start_services
    
    # 清理临时文件
    rm -rf "${BACKUP_DIR}/${backup_dir}"
    
    log "数据恢复完成"
}

# 清理资源
clean_resources() {
    log_info "清理资源..."
    
    cd "${PROJECT_DIR}"
    
    # 停止所有服务
    docker-compose -f ${COMPOSE_FILE} down -v
    
    # 删除未使用的镜像
    docker image prune -f
    
    # 删除未使用的容器
    docker container prune -f
    
    # 删除未使用的网络
    docker network prune -f
    
    # 删除未使用的数据卷
    docker volume prune -f
    
    log "资源清理完成"
}

# 更新应用
update_application() {
    log_info "更新应用..."
    
    # 备份数据
    backup_data
    
    # 拉取最新代码
    git pull origin main
    
    # 重新部署
    deploy_application
    
    log "应用更新完成"
}

# 回滚版本
rollback_version() {
    log_info "回滚版本..."
    
    local version="$3"
    
    if [ -z "$version" ]; then
        log_error "请指定要回滚的版本"
        exit 1
    fi
    
    # 切换到指定版本
    git checkout "$version"
    
    # 重新部署
    deploy_application
    
    log "版本回滚完成"
}

# 生成部署报告
generate_report() {
    log_info "生成部署报告..."
    
    local report_file="${PROJECT_DIR}/logs/deployment_report_$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "$report_file" << EOF
AI智能交易大脑部署报告
生成时间: $(date)
环境: $ENVIRONMENT
操作: $ACTION

=== 系统信息 ===
Docker版本: $(docker --version)
Docker Compose版本: $(docker-compose --version)
操作系统: $(uname -a)

=== 服务状态 ===
$(docker-compose -f ${COMPOSE_FILE} ps)

=== 资源使用情况 ===
$(docker stats --no-stream)

=== 日志摘要 ===
$(tail -n 20 "${LOG_FILE}")

=== 部署配置 ===
Compose文件: ${COMPOSE_FILE}
项目名称: ${COMPOSE_PROJECT_NAME}
EOF
    
    log "部署报告生成完成: $report_file"
}

# 主函数
main() {
    log "开始执行部署脚本..."
    log "环境: $ENVIRONMENT"
    log "操作: $ACTION"
    
    # 显示帮助
    if [ "$1" = "help" ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
        show_help
        exit 0
    fi
    
    # 检查依赖
    check_dependencies
    
    # 设置环境
    setup_environment
    
    # 根据操作执行相应功能
    case $ACTION in
        deploy)
            deploy_application
            ;;
        start)
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        status)
            check_status
            ;;
        logs)
            view_logs "$@"
            ;;
        backup)
            backup_data
            ;;
        restore)
            restore_data "$@"
            ;;
        test)
            run_tests
            ;;
        clean)
            clean_resources
            ;;
        update)
            update_application
            ;;
        rollback)
            rollback_version "$@"
            ;;
        *)
            log_error "未知操作: $ACTION"
            show_help
            exit 1
            ;;
    esac
    
    # 生成部署报告
    generate_report
    
    log "部署脚本执行完成"
}

# 脚本入口
main "$@"