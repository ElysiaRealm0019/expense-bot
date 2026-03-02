#!/bin/bash
#
# expense-bot 自动配置脚本
# 功能：创建配置目录、复制配置文件、安装依赖、配置权限
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$HOME/.config/expense-bot"

echo -e "${GREEN}♪ expense-bot 自动配置脚本${NC}"
echo "================================"

# 1. 创建配置目录
echo -e "\n${YELLOW}[1/4] 创建配置目录...${NC}"
if [ -d "$CONFIG_DIR" ]; then
    echo "配置目录已存在: $CONFIG_DIR"
else
    mkdir -p "$CONFIG_DIR"
    echo -e "${GREEN}✓${NC} 已创建: $CONFIG_DIR"
fi

# 2. 复制配置文件
echo -e "\n${YELLOW}[2/4] 复制配置文件...${NC}"
if [ -f "$PROJECT_DIR/config.yaml" ]; then
    cp "$PROJECT_DIR/config.yaml" "$CONFIG_DIR/config.yaml"
    echo -e "${GREEN}✓${NC} 已复制 config.yaml 到 $CONFIG_DIR/"
else
    # 创建默认配置模板
    cat > "$CONFIG_DIR/config.yaml" << 'EOF'
# expense-bot 配置文件
# 请将 YOUR_BOT_TOKEN_HERE 替换为你的 Telegram Bot Token

bot:
  token: "YOUR_BOT_TOKEN_HERE"
  name: "expense_bot"

database:
  path: "data/expenses.db"

currency:
  symbol: "£"
  name: "GBP"

settings:
  max_history: 50
  timezone: "Europe/London"
EOF
    echo -e "${GREEN}✓${NC} 已创建默认配置文件: $CONFIG_DIR/config.yaml"
    echo -e "${YELLOW}! 请编辑配置文件，填入你的 Telegram Bot Token${NC}"
fi

# 3. 安装依赖
echo -e "\n${YELLOW}[3/4] 安装依赖...${NC}"
PIP_FLAGS="--break-system-packages"
if command -v pip3 &> /dev/null; then
    pip3 install -r "$PROJECT_DIR/requirements.txt" $PIP_FLAGS --quiet
    echo -e "${GREEN}✓${NC} 依赖安装完成"
elif command -v pip &> /dev/null; then
    pip install -r "$PROJECT_DIR/requirements.txt" $PIP_FLAGS --quiet
    echo -e "${GREEN}✓${NC} 依赖安装完成"
else
    echo -e "${RED}✗${NC} 未找到 pip，请先安装 Python"
    exit 1
fi

# 4. 配置权限
echo -e "\n${YELLOW}[4/4] 配置权限...${NC}"
# 确保数据目录存在
mkdir -p "$PROJECT_DIR/data"
mkdir -p "$PROJECT_DIR/logs"

# 设置日志目录权限
chmod 755 "$PROJECT_DIR/logs"
chmod 755 "$PROJECT_DIR/data"

# 设置脚本可执行权限
if [ -f "$PROJECT_DIR/deploy.sh" ]; then
    chmod +x "$PROJECT_DIR/deploy.sh"
fi
chmod +x "$PROJECT_DIR/cli.py"

echo -e "${GREEN}✓${NC} 权限配置完成"

# 完成
echo -e "\n${GREEN}================================"
echo -e "♪ 配置完成！"
echo -e "================================${NC}"
echo ""
echo "下一步："
echo "  1. 编辑 $CONFIG_DIR/config.yaml"
echo "  2. 填入你的 Telegram Bot Token"
echo "  3. 运行: python -m expense_bot.cli start"
echo ""
