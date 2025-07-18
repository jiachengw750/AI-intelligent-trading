#!/bin/bash

# AI智能交易大脑 - 监控脚本
# 用于监控系统状态、服务健康和性能指标

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
LOG_FILE="${PROJECT_DIR}/logs/monitor.log"
ALERT_FILE="${PROJECT_DIR}/logs/alerts.log"
METRICS_DIR="${PROJECT_DIR}/monitoring/metrics"

# 监控配置
CHECK_INTERVAL=30  # 检查间隔（秒）
ALERT_THRESHOLD_CPU=80  # CPU使用率告警阈值
ALERT_THRESHOLD_MEMORY=85  # 内存使用率告警阈值
ALERT_THRESHOLD_DISK=90  # 磁盘使用率告警阈值
ALERT_THRESHOLD_RESPONSE_TIME=2000  # 响应时间告警阈值（毫秒）

# 确保目录存在
mkdir -p "${PROJECT_DIR}/logs"
mkdir -p "${METRICS_DIR}"

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

# 告警函数
alert() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo "[$timestamp] [$level] $message" >> "${ALERT_FILE}"
    
    # 发送邮件告警（如果配置了）
    if [ -n "$ALERT_EMAIL" ]; then
        echo "$message" | mail -s "AI智能交易大脑告警 - $level" "$ALERT_EMAIL"
    fi
    
    # 发送Slack告警（如果配置了）
    if [ -n "$SLACK_WEBHOOK" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"AI智能交易大脑告警: $message\"}" \
            "$SLACK_WEBHOOK"
    fi
    
    log_warn "告警: $message"
}

# 显示帮助信息
show_help() {
    cat << EOF
AI智能交易大脑监控脚本

用法:
  $0 [环境] [选项]

环境:
  development  - 开发环境 (默认)
  test         - 测试环境
  production   - 生产环境

选项:
  -h, --help          显示帮助信息
  -s, --status        显示系统状态
  -m, --metrics       显示性能指标
  -a, --alerts        显示告警信息
  -d, --dashboard     启动监控面板
  -w, --watch         持续监控模式
  -c, --check         单次健康检查
  -r, --report        生成监控报告

示例:
  $0 production --watch    # 持续监控生产环境
  $0 --status             # 显示开发环境状态
  $0 --metrics            # 显示性能指标

EOF
}

# 设置环境变量
setup_environment() {
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
        source "${PROJECT_DIR}/.env.${ENVIRONMENT}"
    elif [ -f "${PROJECT_DIR}/.env" ]; then
        source "${PROJECT_DIR}/.env"
    fi
}

# 检查Docker服务状态
check_docker_services() {
    log_info "检查Docker服务状态..."
    
    cd "${PROJECT_DIR}"
    
    # 获取服务状态
    local services=$(docker-compose -f ${COMPOSE_FILE} ps --services)
    local running_services=$(docker-compose -f ${COMPOSE_FILE} ps --services --filter "status=running")
    
    echo "=== Docker服务状态 ==="
    docker-compose -f ${COMPOSE_FILE} ps
    echo ""
    
    # 检查每个服务
    for service in $services; do
        if echo "$running_services" | grep -q "^$service$"; then
            log "✓ $service: 运行中"
        else
            log_error "✗ $service: 未运行"
            alert "ERROR" "服务 $service 未运行"
        fi
    done
}

# 检查系统资源
check_system_resources() {
    log_info "检查系统资源..."
    
    # CPU使用率
    local cpu_usage=$(top -l 1 -s 0 | grep "CPU usage" | awk '{print $3}' | sed 's/%//')
    if [ -z "$cpu_usage" ]; then
        cpu_usage=$(ps -A -o %cpu | awk '{s+=$1} END {print s}')
    fi
    
    # 内存使用率
    local memory_usage=$(ps -A -o %mem | awk '{s+=$1} END {print s}')
    
    # 磁盘使用率
    local disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    echo "=== 系统资源使用情况 ==="
    echo "CPU使用率: ${cpu_usage}%"
    echo "内存使用率: ${memory_usage}%"
    echo "磁盘使用率: ${disk_usage}%"
    echo ""
    
    # 检查告警阈值
    if (( $(echo "$cpu_usage > $ALERT_THRESHOLD_CPU" | bc -l) )); then
        alert "WARNING" "CPU使用率过高: ${cpu_usage}%"
    fi
    
    if (( $(echo "$memory_usage > $ALERT_THRESHOLD_MEMORY" | bc -l) )); then
        alert "WARNING" "内存使用率过高: ${memory_usage}%"
    fi
    
    if (( $(echo "$disk_usage > $ALERT_THRESHOLD_DISK" | bc -l) )); then
        alert "WARNING" "磁盘使用率过高: ${disk_usage}%"
    fi
    
    # 保存指标
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "$timestamp,$cpu_usage,$memory_usage,$disk_usage" >> "${METRICS_DIR}/system_metrics.csv"
}

# 检查应用健康状态
check_application_health() {
    log_info "检查应用健康状态..."
    
    # 检查API健康状态
    local api_health=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
    local response_time=$(curl -s -o /dev/null -w "%{time_total}" http://localhost:8000/health)
    local response_time_ms=$(echo "$response_time * 1000" | bc)
    
    echo "=== 应用健康状态 ==="
    if [ "$api_health" = "200" ]; then
        log "✓ API服务: 健康"
        echo "API响应时间: ${response_time_ms}ms"
    else
        log_error "✗ API服务: 不健康 (HTTP $api_health)"
        alert "ERROR" "API服务不健康，HTTP状态码: $api_health"
    fi
    
    # 检查响应时间
    if (( $(echo "$response_time_ms > $ALERT_THRESHOLD_RESPONSE_TIME" | bc -l) )); then
        alert "WARNING" "API响应时间过长: ${response_time_ms}ms"
    fi
    
    # 检查数据库连接
    local db_status=$(docker-compose -f ${COMPOSE_FILE} exec -T postgres pg_isready -U trading_user 2>/dev/null)
    if echo "$db_status" | grep -q "accepting connections"; then
        log "✓ 数据库: 连接正常"
    else
        log_error "✗ 数据库: 连接异常"
        alert "ERROR" "数据库连接异常"
    fi
    
    # 检查Redis连接
    local redis_status=$(docker-compose -f ${COMPOSE_FILE} exec -T redis redis-cli ping 2>/dev/null)
    if [ "$redis_status" = "PONG" ]; then
        log "✓ Redis: 连接正常"
    else
        log_error "✗ Redis: 连接异常"
        alert "ERROR" "Redis连接异常"
    fi
    
    echo ""
    
    # 保存健康状态指标
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local db_ok=$([ "$db_status" ] && echo "1" || echo "0")
    local redis_ok=$([ "$redis_status" = "PONG" ] && echo "1" || echo "0")
    local api_ok=$([ "$api_health" = "200" ] && echo "1" || echo "0")
    
    echo "$timestamp,$api_ok,$db_ok,$redis_ok,$response_time_ms" >> "${METRICS_DIR}/health_metrics.csv"
}

# 检查容器资源使用
check_container_resources() {
    log_info "检查容器资源使用..."
    
    cd "${PROJECT_DIR}"
    
    echo "=== 容器资源使用情况 ==="
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}"
    echo ""
    
    # 检查容器资源使用情况
    local containers=$(docker-compose -f ${COMPOSE_FILE} ps -q)
    for container in $containers; do
        local stats=$(docker stats --no-stream --format "{{.CPUPerc}},{{.MemPerc}}" $container)
        local cpu_perc=$(echo $stats | cut -d',' -f1 | sed 's/%//')
        local mem_perc=$(echo $stats | cut -d',' -f2 | sed 's/%//')
        local container_name=$(docker inspect --format '{{.Name}}' $container | sed 's/^.//')
        
        if (( $(echo "$cpu_perc > 80" | bc -l) )); then
            alert "WARNING" "容器 $container_name CPU使用率过高: ${cpu_perc}%"
        fi
        
        if (( $(echo "$mem_perc > 85" | bc -l) )); then
            alert "WARNING" "容器 $container_name 内存使用率过高: ${mem_perc}%"
        fi
    done
}

# 检查日志错误
check_log_errors() {
    log_info "检查日志错误..."
    
    local error_count=0
    local log_files="${PROJECT_DIR}/logs/*.log"
    
    echo "=== 最近的错误日志 ==="
    
    # 检查最近5分钟的错误
    for log_file in $log_files; do
        if [ -f "$log_file" ]; then
            local recent_errors=$(grep -i "error\|exception\|failed" "$log_file" | tail -10)
            if [ -n "$recent_errors" ]; then
                echo "来自 $(basename $log_file):"
                echo "$recent_errors"
                echo ""
                error_count=$((error_count + 1))
            fi
        fi
    done
    
    if [ $error_count -gt 10 ]; then
        alert "WARNING" "检测到大量错误日志: $error_count 个错误"
    fi
}

# 检查网络连接
check_network_connectivity() {
    log_info "检查网络连接..."
    
    echo "=== 网络连接状态 ==="
    
    # 检查外部API连接
    local endpoints=("https://api.binance.com/api/v3/ping" "https://api.openai.com/v1/models")
    
    for endpoint in "${endpoints[@]}"; do
        local response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$endpoint")
        if [ "$response" = "200" ] || [ "$response" = "401" ]; then
            log "✓ $(echo $endpoint | cut -d'/' -f3): 连接正常"
        else
            log_error "✗ $(echo $endpoint | cut -d'/' -f3): 连接异常 (HTTP $response)"
            alert "WARNING" "外部API连接异常: $endpoint"
        fi
    done
    
    echo ""
}

# 生成性能指标
generate_metrics() {
    log_info "生成性能指标..."
    
    check_system_resources
    check_application_health
    check_container_resources
    check_log_errors
    check_network_connectivity
}

# 显示监控仪表板
show_dashboard() {
    clear
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    AI智能交易大脑监控面板                      ║"
    echo "║                    环境: $ENVIRONMENT                        ║"
    echo "║                    时间: $(date '+%Y-%m-%d %H:%M:%S')        ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    
    check_docker_services
    check_system_resources
    check_application_health
    check_container_resources
    
    echo "按 Ctrl+C 退出监控..."
}

# 持续监控模式
watch_mode() {
    log_info "启动持续监控模式..."
    
    while true; do
        show_dashboard
        sleep $CHECK_INTERVAL
    done
}

# 单次健康检查
single_health_check() {
    log_info "执行单次健康检查..."
    
    check_docker_services
    check_application_health
    check_system_resources
    
    # 生成简单报告
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local report_file="${PROJECT_DIR}/logs/health_check_${timestamp//[: -]/}.txt"
    
    {
        echo "健康检查报告"
        echo "时间: $timestamp"
        echo "环境: $ENVIRONMENT"
        echo ""
        echo "服务状态: $(docker-compose -f ${COMPOSE_FILE} ps --services | wc -l) 个服务"
        echo "运行服务: $(docker-compose -f ${COMPOSE_FILE} ps --services --filter 'status=running' | wc -l) 个运行中"
        echo ""
        echo "详细信息请查看监控日志: $LOG_FILE"
    } > "$report_file"
    
    log "健康检查报告已生成: $report_file"
}

# 显示告警信息
show_alerts() {
    log_info "显示告警信息..."
    
    if [ -f "$ALERT_FILE" ]; then
        echo "=== 最近的告警 ==="
        tail -20 "$ALERT_FILE"
        echo ""
        echo "告警总数: $(wc -l < "$ALERT_FILE")"
    else
        echo "暂无告警信息"
    fi
}

# 生成监控报告
generate_report() {
    log_info "生成监控报告..."
    
    local timestamp=$(date '+%Y-%m-%d_%H-%M-%S')
    local report_file="${PROJECT_DIR}/logs/monitoring_report_${timestamp}.html"
    
    cat > "$report_file" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>AI智能交易大脑监控报告</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f0f0f0; padding: 20px; border-radius: 5px; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .error { color: red; }
        .warning { color: orange; }
        .success { color: green; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <div class="header">
        <h1>AI智能交易大脑监控报告</h1>
        <p>生成时间: $(date)</p>
        <p>环境: $ENVIRONMENT</p>
    </div>
    
    <div class="section">
        <h2>系统概览</h2>
        <p>Docker版本: $(docker --version)</p>
        <p>Docker Compose版本: $(docker-compose --version)</p>
        <p>系统信息: $(uname -a)</p>
    </div>
    
    <div class="section">
        <h2>服务状态</h2>
        <pre>$(docker-compose -f ${COMPOSE_FILE} ps)</pre>
    </div>
    
    <div class="section">
        <h2>资源使用情况</h2>
        <pre>$(docker stats --no-stream)</pre>
    </div>
    
    <div class="section">
        <h2>最近告警</h2>
        <pre>$(tail -20 "$ALERT_FILE" 2>/dev/null || echo "无告警记录")</pre>
    </div>
    
    <div class="section">
        <h2>日志摘要</h2>
        <pre>$(tail -50 "$LOG_FILE")</pre>
    </div>
</body>
</html>
EOF
    
    log "监控报告已生成: $report_file"
}

# 主函数
main() {
    log "开始执行监控脚本..."
    
    # 设置环境
    setup_environment
    
    # 解析命令行参数
    case "$2" in
        -h|--help)
            show_help
            exit 0
            ;;
        -s|--status)
            check_docker_services
            ;;
        -m|--metrics)
            generate_metrics
            ;;
        -a|--alerts)
            show_alerts
            ;;
        -d|--dashboard)
            show_dashboard
            ;;
        -w|--watch)
            watch_mode
            ;;
        -c|--check)
            single_health_check
            ;;
        -r|--report)
            generate_report
            ;;
        *)
            log_info "未指定选项，执行单次健康检查"
            single_health_check
            ;;
    esac
    
    log "监控脚本执行完成"
}

# 捕获退出信号
trap 'log_info "监控脚本被中断"; exit 0' SIGINT SIGTERM

# 脚本入口
main "$@"