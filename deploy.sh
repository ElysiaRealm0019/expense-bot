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
NC='\033[0m' # No Color

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

# Function to start the bot
start_bot() {
    echo -e "${BLUE}启动 Expense Bot...${NC}"
    docker-compose up -d
    echo
    echo -e "${GREEN}✓ Bot 已启动!${NC}"
    echo
    echo "查看日志: docker-compose logs -f"
    echo "停止 Bot:  docker-compose down"
}

# Function to rebuild and start
rebuild_bot() {
    echo -e "${BLUE}重新构建并启动 Expense Bot...${NC}"
    docker-compose up -d --build
    echo
    echo -e "${GREEN}✓ Bot 已重新构建并启动!${NC}"
    echo
    echo "查看日志: docker-compose logs -f"
    echo "停止 Bot:  docker-compose down"
}

# Parse command line arguments
case "${1:-start}" in
    start)
        start_bot
        ;;
    restart)
        echo -e "${BLUE}重启 Expense Bot...${NC}"
        docker-compose restart
        echo -e "${GREEN}✓ Bot 已重启!${NC}"
        ;;
    stop)
        echo -e "${BLUE}停止 Expense Bot...${NC}"
        docker-compose down
        echo -e "${GREEN}✓ Bot 已停止!${NC}"
        ;;
    rebuild)
        rebuild_bot
        ;;
    logs)
        docker-compose logs -f
        ;;
    status)
        docker-compose ps
        ;;
    clean)
        echo -e "${YELLOW}清理所有数据卷? 这将删除所有记账数据! (y/N)${NC}"
        read -r confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            docker-compose down -v
            echo -e "${GREEN}✓ 已清理所有数据卷${NC}"
        else
            echo "已取消"
        fi
        ;;
    *)
        echo "用法: $0 {start|restart|stop|rebuild|logs|status|clean}"
        echo
        echo "命令说明:"
        echo "  start    - 启动 Bot (首次或更新后)"
        echo "  restart  - 重启 Bot"
        echo "  stop     - 停止 Bot"
        echo "  rebuild  - 重新构建镜像并启动"
        echo "  logs     - 查看实时日志"
        echo "  status   - 查看运行状态"
        echo "  clean    - 清理所有数据 (包括数据库)"
        exit 1
        ;;
esac
