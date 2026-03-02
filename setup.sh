#!/bin/bash
#
# expense-bot 自动配置脚本
# 功能：创建配置目录、复制配置文件、配置权限、引导设置
#

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$HOME/.config/expense-bot"

echo -e "${GREEN}♪ expense-bot 自动配置脚本${NC}"
echo "================================"

# 1. 创建配置目录
echo -e "\n${YELLOW}[1/6] 创建配置目录...${NC}"
if [ -d "$CONFIG_DIR" ]; then
    echo "配置目录已存在: $CONFIG_DIR"
else
    mkdir -p "$CONFIG_DIR"
    echo -e "${GREEN}✓${NC} 已创建: $CONFIG_DIR"
fi

# 2. 复制配置文件
echo -e "\n${YELLOW}[2/6] 复制配置文件...${NC}"

# 优先复制 .env
if [ -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env" "$CONFIG_DIR/.env"
    echo -e "${GREEN}✓${NC} 已复制 .env 到 $CONFIG_DIR/"
elif [ -f "$PROJECT_DIR/.env.example" ]; then
    cp "$PROJECT_DIR/.env.example" "$CONFIG_DIR/.env"
    echo -e "${GREEN}✓${NC} 已复制 .env.example → $CONFIG_DIR/.env"
fi

# 复制 config.yaml (如果存在)
if [ -f "$PROJECT_DIR/config.yaml" ]; then
    cp "$PROJECT_DIR/config.yaml" "$CONFIG_DIR/config.yaml"
    echo -e "${GREEN}✓${NC} 已复制 config.yaml 到 $CONFIG_DIR/"
else
    # 创建默认配置模板
    cat > "$CONFIG_DIR/config.yaml" << 'EOF'
# expense-bot 配置文件

bot:
  token: "YOUR_BOT_TOKEN_HERE"
  name: "expense_bot"

ai:
  enabled: false
  provider: "openai"
  model: "gpt-4o-mini"
  api_key: "YOUR_API_KEY_HERE"

database:
  path: "data/expenses.db"

currency:
  symbol: "£"
  name: "GBP"

settings:
  max_history: 50
  timezone: "Europe/London"
  language: "zh"
EOF
    echo -e "${GREEN}✓${NC} 已创建默认配置文件: $CONFIG_DIR/config.yaml"
fi

# 3. 配置权限
echo -e "\n${YELLOW}[3/6] 配置权限...${NC}"

# 设置配置目录权限为 700 (仅所有者)
chmod 700 "$CONFIG_DIR"
echo -e "${GREEN}✓${NC} 目录权限: 700"

# 设置配置文件权限为 600 (仅所有者读写)
if [ -f "$CONFIG_DIR/.env" ]; then
    chmod 600 "$CONFIG_DIR/.env"
    echo -e "${GREEN}✓${NC} .env 权限: 600"
fi

if [ -f "$CONFIG_DIR/config.yaml" ]; then
    chmod 600 "$CONFIG_DIR/config.yaml"
    echo -e "${GREEN}✓${NC} config.yaml 权限: 600"
fi

# 确保数据目录存在
mkdir -p "$PROJECT_DIR/data"
mkdir -p "$PROJECT_DIR/logs"
chmod 755 "$PROJECT_DIR/logs"
chmod 755 "$PROJECT_DIR/data"
echo -e "${GREEN}✓${NC} 数据目录权限已设置"

# 4. 安装依赖 (可选)
echo -e "\n${YELLOW}[4/6] 检查依赖...${NC}"
INSTALL_OK=false
if command -v pip3 &> /dev/null; then
    if pip3 install -r "$PROJECT_DIR/requirements.txt" --user 2>/dev/null; then
        INSTALL_OK=true
    elif pip3 install -r "$PROJECT_DIR/requirements.txt" --break-system-packages 2>/dev/null; then
        INSTALL_OK=true
    fi
fi

if [ "$INSTALL_OK" = true ]; then
    echo -e "${GREEN}✓${NC} 依赖安装完成"
else
    echo -e "${YELLOW}! 请手动安装依赖: pip3 install -r requirements.txt${NC}"
fi

# 5. 交互式引导设置
echo -e "\n${YELLOW}[5/6] 引导设置...${NC}"
echo ""

# Telegram Bot Token 设置
echo -e "${CYAN}━━━ Telegram Bot Token ━━━${NC}"
if [ -f "$CONFIG_DIR/config.yaml" ]; then
    CURRENT_TOKEN=$(grep -A1 "^bot:" "$CONFIG_DIR/config.yaml" | grep "token:" | sed 's/.*token: *"\(.*\)"/\1/' | tr -d '"')
    if [ "$CURRENT_TOKEN" = "YOUR_BOT_TOKEN_HERE" ] || [ -z "$CURRENT_TOKEN" ]; then
        echo -e "${YELLOW}尚未配置 Telegram Bot Token${NC}"
        read -p "请输入你的 Telegram Bot Token (或按 Enter 跳过): " NEW_TOKEN
        if [ -n "$NEW_TOKEN" ]; then
            sed -i "s/YOUR_BOT_TOKEN_HERE/$NEW_TOKEN/" "$CONFIG_DIR/config.yaml"
            echo -e "${GREEN}✓${NC} Bot Token 已保存"
        fi
    else
        echo -e "${GREEN}✓${NC} Bot Token 已配置"
    fi
fi
echo ""

# AI 配置设置
echo -e "${CYAN}━━━ AI 配置 (可选) ━━━${NC}"
echo "AI 功能可以帮助你："
echo "  • 智能分类交易记录"
echo "  • 消费洞察和分析"
echo "  • 预算建议"
echo ""
read -p "是否启用 AI 功能? (y/N): " ENABLE_AI

if [ "$ENABLE_AI" = "y" ] || [ "$ENABLE_AI" = "Y" ]; then
    # 更新 config.yaml 启用 AI
    sed -i 's/enabled: false/enabled: true/' "$CONFIG_DIR/config.yaml"
    
    # 选择 AI 提供商
    echo ""
    echo "请选择 AI 提供商:"
    echo "  1) OpenAI (GPT-4o, GPT-4o-mini)"
    echo "  2) Anthropic (Claude)"
    echo "  3) Google (Gemini)"
    echo "  4) Ollama (本地部署)"
    echo "  5) MiniMax"
    read -p "请选择 (1-5): " AI_PROVIDER_CHOICE
    
    case $AI_PROVIDER_CHOICE in
        1) PROVIDER="openai";;
        2) PROVIDER="anthropic";;
        3) PROVIDER="google";;
        4) PROVIDER="ollama";;
        5) PROVIDER="minimax";;
        *) PROVIDER="openai";;
    esac
    
    sed -i "s/provider: \"openai\"/provider: \"$PROVIDER\"/" "$CONFIG_DIR/config.yaml"
    echo -e "${GREEN}✓${NC} AI 提供商: $PROVIDER"
    
    # 输入 API Key
    echo ""
    if [ "$PROVIDER" = "ollama" ]; then
        echo -e "${YELLOW}Ollama 使用本地部署，请确保 Ollama 服务已启动${NC}"
        read -p "Ollama 地址 (默认 http://localhost:11434): " OLLAMA_URL
        if [ -n "$OLLAMA_URL" ]; then
            sed -i "s|base_url: \".*\"|base_url: \"$OLLAMA_URL\"|" "$CONFIG_DIR/config.yaml"
        fi
        read -p "Ollama 模型 (默认 llama3.2): " OLLAMA_MODEL
        if [ -n "$OLLAMA_MODEL" ]; then
            sed -i "s/model: \"llama3.2\"/model: \"$OLLAMA_MODEL\"/" "$CONFIG_DIR/config.yaml"
        fi
    else
        read -p "请输入你的 $PROVIDER API Key: " API_KEY
        if [ -n "$API_KEY" ]; then
            sed -i "s/YOUR_API_KEY_HERE/$API_KEY/" "$CONFIG_DIR/config.yaml"
            echo -e "${GREEN}✓${NC} API Key 已保存"
        fi
    fi
    
    # 选择模型
    echo ""
    echo "推荐模型:"
    case $PROVIDER in
        openai)
            echo "  • gpt-4o - 最新旗舰模型 (推荐)"
            echo "  • gpt-4o-mini - 性价比之选 (推荐)"
            echo "  • gpt-4-turbo - 快速响应"
            DEFAULT_MODEL="gpt-4o-mini"
            ;;
        anthropic)
            echo "  • claude-sonnet-4 - 均衡性能 (推荐)"
            echo "  • claude-3-5-sonnet - 性价比"
            echo "  • claude-3-opus - 最强能力"
            DEFAULT_MODEL="claude-sonnet-4-20250514"
            ;;
        google)
            echo "  • gemini-2.0-flash - 快速响应 (推荐)"
            echo "  • gemini-1.5-pro - 高性能"
            DEFAULT_MODEL="gemini-2.0-flash"
            ;;
        minimax)
            echo "  • MiniMax-M2.1 - 高性能 (推荐)"
            echo "  • MiniMax-M2.5 - 最新模型 (推荐)"
            DEFAULT_MODEL="MiniMax-M2.5"
            ;;
    esac
    read -p "请选择或输入模型名称 (默认 $DEFAULT_MODEL): " AI_MODEL
    if [ -n "$AI_MODEL" ]; then
        sed -i "s/model: \".*\"/model: \"$AI_MODEL\"/" "$CONFIG_DIR/config.yaml"
        echo -e "${GREEN}✓${NC} 模型已设置为: $AI_MODEL"
    fi
    
    echo ""
    echo -e "${GREEN}✓ AI 配置完成!${NC}"
else
    echo -e "${YELLOW}已跳过 AI 配置，如需启用可稍后编辑 config.yaml${NC}"
fi

# 6. 完成
echo -e "\n${YELLOW}[6/6] 完成!${NC}"
echo -e "\n${GREEN}================================"
echo -e "♪ 配置完成！"
echo -e "================================${NC}"
echo ""
echo "配置文件位置: $CONFIG_DIR/"
echo ""
echo "下一步："
echo "  1. 运行: python -m expense_bot.cli start"
echo "  2. 在 Telegram 中发送 /start 给你的机器人"
echo ""
echo "查看配置: python -m expense_bot.cli config list"
echo "修改配置: python -m expense_bot.cli config set ai.enabled true"
echo ""
