#!/bin/bash
set -e

# =============================================
# Expense Bot 一键部署脚本
# =============================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# PID and Log files
PID_FILE="$SCRIPT_DIR/data/expense-bot.pid"
LOG_FILE="$SCRIPT_DIR/data/expense-bot.log"

echo -e "${BLUE}=============================================${NC}"
echo -e "${BLUE}  Expense Bot 部署脚本${NC}"
echo -e "${BLUE}=============================================${NC}"
echo

# Check if .env exists
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo -e "${YELLOW}未找到 .env 文件，正在从 .env.example 创建...${NC}"
        cp .env.example .env
        echo -e "${GREEN}✓ 已创建 .env 文件${NC}"
        echo
        echo -e "${YELLOW}请编辑 .env 文件并配置 TELEGRAM_BOT_TOKEN${NC}"
        echo -e "配置文件位置: ${SCRIPT_DIR}/.env"
        exit 0
    else
        echo -e "${RED}错误: 未找到 .env.example 文件${NC}"
        exit 1
    fi
fi

# Check if TELEGRAM_BOT_TOKEN is set
source .env
if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ "$TELEGRAM_BOT_TOKEN" = "YOUR_BOT_TOKEN_HERE" ]; then
    echo -e "${RED}错误: 请在 .env 文件中配置 TELEGRAM_BOT_TOKEN${NC}"
    echo
    echo "获取 Token 方法:"
    echo "1. 在 Telegram 中搜索 @BotFather"
    echo "2. 发送 /newbot 创建新机器人"
    echo "3. 复制 Bot Token 并填入 .env 文件"
    exit 1
fi

echo -e "${GREEN}✓ 配置检查通过${NC}"
echo

# =============================================
# Helper Functions
# =============================================

# Check if bot is running
is_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

# Get PID
get_pid() {
    if [ -f "$PID_FILE" ]; then
        cat "$PID_FILE"
    fi
}

# Start bot in background
start_bot_background() {
    echo -e "${BLUE}启动 Expense Bot (后台)...${NC}"
    
    # 确保 data 目录存在
    mkdir -p "$SCRIPT_DIR/data"
    
    # 如果已经在运行，显示信息
    if is_running; then
        PID=$(get_pid)
        echo -e "${YELLOW}Bot 已在运行中 (PID: $PID)${NC}"
        return
    fi
    
    # 后台启动
    nohup python3 -m bot.main >> "$LOG_FILE" 2>&1 &
    PID=$!
    
    # 保存 PID
    echo "$PID" > "$PID_FILE"
    
    # 等待一下让进程启动
    sleep 2
    
    if kill -0 "$PID" 2>/dev/null; then
        echo -e "${GREEN}✓ Bot 已启动 (PID: $PID)${NC}"
        echo "  日志文件: $LOG_FILE"
    else
        echo -e "${RED}✗ Bot 启动失败${NC}"
        rm -f "$PID_FILE"
        exit 1
    fi
}

# Start bot in foreground
start_bot_foreground() {
    echo -e "${BLUE}启动 Expense Bot (前台)...${NC}"
    
    if is_running; then
        PID=$(get_pid)
        echo -e "${YELLOW}Bot 已在运行中 (PID: $PID)${NC}"
        echo "使用 '$0 stop' 停止后重新启动"
        exit 1
    fi
    
    python3 -m bot.main
}

# Stop bot
stop_bot() {
    echo -e "${BLUE}停止 Expense Bot...${NC}"
    
    if ! is_running; then
        echo -e "${YELLOW}Bot 未在运行${NC}"
        rm -f "$PID_FILE" 2>/dev/null || true
        return
    fi
    
    PID=$(get_pid)
    
    # 尝试优雅停止
    kill "$PID" 2>/dev/null || true
    
    # 等待进程结束
    for i in {1..10}; do
        if ! kill -0 "$PID" 2>/dev/null; then
            break
        fi
        sleep 0.5
    done
    
    # 如果还在运行，强制杀死
    if kill -0 "$PID" 2>/dev/null; then
        kill -9 "$PID" 2>/dev/null || true
    fi
    
    rm -f "$PID_FILE"
    echo -e "${GREEN}✓ Bot 已停止${NC}"
}

# Show status
show_status() {
    if is_running; then
        PID=$(get_pid)
        echo -e "${GREEN}● Bot 运行中 (PID: $PID)${NC}"
        
        # 显示运行时间 (如果 /proc 存在)
        if [ -d "/proc/$PID" ]; then
            START_TIME=$(ps -o lstart= -p "$PID" 2>/dev/null || echo "未知")
            echo "  启动时间: $START_TIME"
        fi
    else
        echo -e "${YELLOW}○ Bot 未运行${NC}"
    fi
}

# Show logs
show_logs() {
    LINES=${1:-50}
    
    if [ -f "$LOG_FILE" ]; then
        echo -e "${CYAN}--- 最近 $LINES 行日志 ---${NC}"
        tail -n "$LINES" "$LOG_FILE"
    else
        echo "日志文件不存在: $LOG_FILE"
    fi
}

# =============================================
# Parse command line arguments
# =============================================

case "${1:-start}" in
    start)
        # 默认后台启动
        if [ "${2:-}" = "-f" ] || [ "${2:-}" = "--foreground" ]; then
            start_bot_foreground
        else
            start_bot_background
        fi
        ;;
    restart)
        echo -e "${BLUE}重启 Expense Bot...${NC}"
        stop_bot
        sleep 1
        start_bot_background
        ;;
    stop)
        stop_bot
        ;;
    rebuild)
        echo -e "${BLUE}重新构建并启动 Expense Bot...${NC}"
        docker-compose up -d --build
        echo
        echo -e "${GREEN}✓ Bot 已重新构建并启动!${NC}"
        echo
        echo "查看日志: $0 logs"
        echo "停止 Bot:  $0 stop"
        ;;
    status)
        show_status
        ;;
    logs)
        LINES=$(echo "${2:-50}" | sed 's/-n//' | sed 's/--lines//' | tr -d ' ')
        if [ -n "$LINES" ] && [ "$LINES" != "$2" ]; then
            show_logs "$LINES"
        elif [ "$2" = "-f" ] || [ "$2" = "--follow" ]; then
            # 实时跟踪日志
            tail -f "$LOG_FILE"
        else
            show_logs "${2:-50}"
        fi
        ;;
    clean)
        echo -e "${YELLOW}清理所有数据卷? 这将删除所有记账数据! (y/N)${NC}"
        read -r confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            stop_bot
            docker-compose down -v 2>/dev/null || true
            rm -rf "$SCRIPT_DIR/data"/*
            echo -e "${GREEN}✓ 已清理所有数据${NC}"
        else
            echo "已取消"
        fi
        ;;
    # Docker Compose 命令透传
    docker)
        shift
        docker-compose "$@"
        ;;
    # 使用 Python CLI
    cli)
        shift
        python3 "$SCRIPT_DIR/cli.py" "$@"
        ;;
    help|--help|-h)
        echo "用法: $0 <命令> [选项]"
        echo
        echo "基本命令:"
        echo "  start [选项]     启动 Bot"
        echo "    -f, --foreground   前台运行"
        echo "  stop              停止 Bot"
        echo "  restart           重启 Bot"
        echo "  status            查看运行状态"
        echo "  logs [行数]       查看日志 (默认50行)"
        echo "    -f, --follow       实时跟踪日志"
        echo "  clean             清理所有数据"
        echo
        echo "Docker 命令:"
        echo "  rebuild           重新构建 Docker 镜像"
        echo "  docker <args>     执行 docker-compose 命令"
        echo
        echo "CLI 命令:"
        echo "  cli <args>        使用 Python CLI 工具"
        echo "    示例: $0 cli list"
        echo "           $0 cli set bot.token YOUR_TOKEN"
        echo "           $0 cli get currency.symbol"
        echo
        echo "其他:"
        echo "  help              显示帮助信息"
        ;;
    *)
        echo "未知命令: $1"
        echo "使用 '$0 help' 查看帮助"
        exit 1
        ;;
esac
