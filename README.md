# 📱 Telegram Expense Bot

[English](#english) | [中文](#中文)

---

## 中文

一个简洁的 Telegram 记账机器人，帮助你追踪日常开支。

### ✨ 功能特性

- 📝 记录支出/收入
- 📊 月度/周度支出统计
- 📈 分类管理
- 🔍 查询历史记录
- 🏷️ 标签支持
- 💾 数据本地存储 (SQLite)
- 🤖 **AI 智能分析** (可选)

### 🤖 AI 功能

expense-bot 支持 AI 智能功能，让记账更智能：

#### 功能列表

| 功能 | 说明 |
|------|------|
| 智能分类 | AI 自动识别交易类型并分类 |
| 消费洞察 | 分析消费习惯，提供洞察 |
| 预算建议 | 根据历史数据给出预算建议 |

#### 支持的 AI 提供商

| 提供商 | 模型示例 | 说明 |
|--------|----------|------|
| OpenAI | gpt-4o, gpt-4o-mini | 官方 API |
| Anthropic | claude-sonnet-4, claude-3-5-sonnet | Claude 系列 |
| Google | gemini-2.0-flash, gemini-1.5-pro | Gemini 系列 |
| Ollama | llama3.2, qwen2.5 | 本地部署 |
| MiniMax | MiniMax-M2.5, MiniMax-M2.1 | 国内模型 |

### 🔗 OpenClaw 协作

expense-bot 可以与 **OpenClaw** 个人 AI 助手无缝协作！

#### 协作功能

| 功能 | 说明 |
|------|------|
| 📊 财务分析 | OpenClaw 可直接查询数据库，提供详细财务报告 |
| 📄 PDF 导入 | 将银行账单发送给 OpenClaw，AI 自动解析导入 |
| 💡 智能建议 | 根据消费数据提供个性化理财建议 |
| 📈 趋势分析 | 分析趋势 |

#### 月度/年度支出联动示例

```
用户: 帮我分析这个月的支出
OpenClaw: 📊 2月支出 £1,015 | 收入 £1,111
         - 餐饮超预算 30%
         - 建议减少外卖次数

用户: (发送 PDF 账单)
OpenClaw: 📄 检测到银行账单，正在解析...
         ✅ 解析到 50 笔交易，已导入数据库
```

#### 数据共享

OpenClaw 可直接读取本地 SQLite 数据库 (`data/expenses.db`)：
- 读取交易记录
- 生成统计报告
- 分析消费习惯
- 提供预算建议



### 📁 项目结构

```
expense-bot/
├── bot/                  # Bot 入口和初始化
│   └── main.py          # 主程序入口
├── core/                 # 核心业务逻辑
│   ├── models.py        # 数据模型
│   ├── database.py     # 数据库操作
│   └── statistics.py   # 统计分析
├── handlers/            # Telegram 命令处理器
│   ├── __init__.py
│   └── commands.py    # 命令处理函数
├── utils/               # 工具函数
│   ├── config.py       # 配置管理
│   └── formatters.py  # 格式化工具
├── config.yaml          # 配置文件
├── requirements.txt     # Python 依赖
└── README.md           # 项目文档
```

### 🚀 快速开始

#### 1. 安装依赖

```bash
pip install -r requirements.txt
```

#### 2. 配置 Bot

运行交互式配置脚本：

```bash
./setup.sh
```

脚本会引导你设置：
- Telegram Bot Token
- AI 配置 (可选)

或手动编辑 `config.yaml`：

```yaml
bot:
  token: "YOUR_BOT_TOKEN_HERE"
```

> 💡 如何获取 Token：搜索 @BotFather 并发送 /newbot

#### 3. 运行 Bot

```bash
# 直接运行
python -m bot.main

# 或使用 CLI (推荐)
python -m expense_bot.cli start
```

### 🤖 AI 配置指南

#### 方式一：交互式配置

```bash
./setup.sh
```

按提示选择 AI 提供商并输入 API Key。

#### 方式二：手动配置

编辑 `config.yaml`：

```yaml
ai:
  enabled: true                    # 启用 AI
  provider: "openai"               # 提供商
  model: "gpt-4o-mini"             # 模型
  api_key: "YOUR_API_KEY_HERE"    # API Key
  
  features:
    smart_categorization: true     # 智能分类
    spending_insights: true       # 消费洞察
    budget_advice: true           # 预算建议
```

#### 各提供商配置示例

**OpenAI:**
```yaml
ai:
  enabled: true
  provider: "openai"
  model: "gpt-4o-mini"
  api_key: "sk-xxx"
```

**Anthropic:**
```yaml
ai:
  enabled: true
  provider: "anthropic"
  model: "claude-sonnet-4-20250514"
  api_key: "sk-ant-xxx"
```

**Google:**
```yaml
ai:
  enabled: true
  provider: "google"
  model: "gemini-2.0-flash"
  api_key: "AIzaSyxxx"
```

**Ollama (本地):**
```yaml
ai:
  enabled: true
  provider: "ollama"
  model: "llama3.2"
  ollama:
    base_url: "http://localhost:11434"
```

**MiniMax:**
```yaml
ai:
  enabled: true
  provider: "minimax"
  model: "MiniMax-M2.5"
  api_key: "your-minimax-api-key"
```

#### 环境变量方式

也可以通过环境变量配置：

```bash
export TELEGRAM_BOT_TOKEN="xxx"
export AI_API_KEY="your-api-key"
export AI_PROVIDER="openai"
export AI_MODEL="gpt-4o-mini"
```

### 📖 CLI 命令列表

| 命令 | 说明 |
|------|------|
| `python -m expense_bot.cli start` | 启动机器人 (前台) |
| `python -m expense_bot.cli start --daemon` | 后台运行 |
| `python -m expense_bot.cli stop` | 停止机器人 |
| `python -m expense_bot.cli status` | 查看运行状态 |
| `python -m expense_bot.cli restart` | 重启机器人 |
| `python -m expense_bot.cli config set token "xxx"` | 设置配置 |
| `python -m expense_bot.cli config get currency.symbol` | 获取配置 |
| `python -m expense_bot.cli config list` | 列出所有配置 |
| `python -m expense_bot.cli config set ai.enabled true` | 启用 AI |
| `python -m expense_bot.cli systemd install` | 安装 systemd 服务 |

### 后台运行 (nohup)

```bash
# 后台启动
python -m expense_bot.cli start --daemon

# 查看日志
tail -f logs/bot.log

# 停止
python -m expense_bot.cli stop
```

### Systemd 服务 (推荐)

```bash
# 安装 systemd 服务 (需要 sudo)
sudo python -m expense_bot.cli systemd install

# 管理服务
sudo systemctl start expense-bot    # 启动
sudo systemctl stop expense-bot    # 停止
sudo systemctl restart expense-bot # 重启
sudo systemctl status expense-bot  # 状态
sudo journalctl -u expense-bot -f   # 查看日志
```

### 📖 命令列表

| 命令 | 说明 |
|------|------|
| `/start` | 启动机器人，显示欢迎信息 |
| `/add` | 记录新的支出/收入 |
| `/balance` | 查看本月统计 |
| `/history` | 查看最近的历史记录 |
| `/category` | 查看可用分类 |
| `/pdfimport` | 导入 PDF 银行账单 |
| `/ai` | AI 功能菜单 |
| `/insights` | 获取 AI 消费洞察 |
| `/help` | 显示帮助信息 |

### 📄 PDF 银行账单导入

支持从 PDF 格式的银行账单自动批量导入交易记录！

#### 功能特点

- 📄 自动解析 PDF 文本
- 💰 识别金额和交易类型（收入/支出）
- 🏷️ 自动根据描述匹配分类
- ✅ 预览确认后再导入

#### 支持的格式

**日期格式：**
- `DD/MM/YYYY` (如 15/01/2024)
- `YYYY-MM-DD` (如 2024-01-15)
- `DD Mon YYYY` (如 15 Jan 2024)
- `DD.MM.YYYY` (如 15.01.2024)

**金额格式：**
- `£1,234.56`
- `-50.00` (支出)
- `100 CR` (收入)

#### 使用方法

```
1. 发送 /pdfimport 命令
2. 上传 PDF 银行账单文件
3. 机器人会解析并显示预览：
   - 识别到的交易数量
   - 总收入/总支出金额
4. 确认后批量导入数据库
```

#### 分类匹配

系统会自动根据交易描述匹配分类：
- 餐饮：餐厅、咖啡、麦当劳、星巴克
- 购物：淘宝、京东、亚马逊
- 交通：地铁、滴滴、加油
- 工资：工资、薪资、转账
- ...

未匹配的交易会标记为"未分类"，可后续手动修改。

### ⚙️ 配置说明

```yaml
# Bot 配置
bot:
  token: "YOUR_TELEGRAM_BOT_TOKEN"  # 必填
  name: "expense_bot"               # 可选

# AI 配置
ai:
  enabled: false                    # 是否启用 AI 功能
  provider: "openai"               # 提供商: openai/anthropic/google/ollama/minimax
  model: "gpt-4o-mini"            # 模型名称
  api_key: "YOUR_API_KEY"         # API Key
  base_url: ""                     # 自定义 API 端点 (可选)
  max_tokens: 1000                 # 最大生成 token 数
  temperature: 0.7                 # 生成温度 (0-2)
  
  features:
    smart_categorization: true     # 智能分类
    spending_insights: true        # 消费洞察
    budget_advice: true            # 预算建议
    receipt_ocr: false             # 收据 OCR 识别
  
  ollama:
    base_url: "http://localhost:11434"
    model: "llama3.2"

database:
  path: "data/expenses.db"          # 数据库路径

currency:
  symbol: "£"                       # 货币符号
  name: "GBP"                       # 货币名称

settings:
  max_history: 50                   # 历史记录上限
  timezone: "Europe/London"         # 时区
  language: "zh"                    # 语言: zh / en
```

### 🐳 Docker 部署

推荐使用 Docker 部署，可以快速启动并确保环境一致性。

#### 前置要求

- [Docker](https://www.docker.com/get-started)
- [Docker Compose](https://docs.docker.com/compose/install/)

#### 快速部署

```bash
# 1. 克隆项目
git clone https://github.com/ElysiaRealm0019/expense-bot.git
cd expense-bot

# 2. 复制环境配置
cp .env.example .env

# 3. 编辑 .env 文件，填入你的 Telegram Bot Token
nano .env

# 4. 一键启动
./deploy.sh start
```

#### 部署命令

```bash
./deploy.sh start    # 启动 Bot
./deploy.sh restart  # 重启 Bot
./deploy.sh stop     # 停止 Bot
./deploy.sh rebuild  # 重新构建镜像
./deploy.sh logs     # 查看日志
./deploy.sh status   # 查看状态
./deploy.sh clean    # 清理所有数据
```

#### 使用 docker-compose 直接运行

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 TELEGRAM_BOT_TOKEN

# 2. 启动
docker-compose up -d

# 3. 查看日志
docker-compose logs -f
```

#### 数据持久化

数据库文件存储在 Docker 命名卷 `expense-data` 中，即使容器删除也不会丢失数据。

查看数据卷:
```bash
docker volume ls | grep expense
```

#### 环境变量

| 变量 | 说明 | 必填 |
|------|------|------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | 是 |
| `AI_ENABLED` | 启用 AI 功能 | 否 |
| `AI_PROVIDER` | AI 提供商 | 否 |
| `AI_API_KEY` | AI API Key | 否 |
| `AI_MODEL` | AI 模型 | 否 |

### 🛠️ 开发

```bash
# 安装开发依赖
pip install -r requirements.txt

# 格式化代码
black .

# 类型检查
mypy .

# 运行测试
pytest
```

### 📝 数据模型

- **Transaction** - 交易记录
- **Category** - 分类
- **Tag** - 标签
- **DailySummary** - 日/周/月汇总
- **CategoryStat** - 分类统计
- **TrendData** - 趋势数据



---

### 🔗 OpenClaw Collaboration

expense-bot can seamlessly collaborate with **OpenClaw** your personal AI assistant!

#### Collaboration Features

| Feature | Description |
|---------|-------------|
| 📊 Financial Analysis | OpenClaw can query the database directly for detailed reports |
| 📄 PDF Import | Send bank statements to OpenClaw, AI auto-parses and imports |
| 💡 Smart Suggestions | Personalized financial advice based on spending data |
| 📈 Trend Analysis | Analyze spending trends |

#### Collaboration Example

```
User: Analyze this month's expenses
OpenClaw: 📊 Feb expenses £1,015 | Income £1,111
         - Dining over budget by 30%
         - Suggest reducing takeout

User: (sends PDF statement)
OpenClaw: 📄 Bank statement detected, parsing...
         ✅ Parsed 50 transactions, imported to database
```

#### Data Sharing

OpenClaw can directly read the local SQLite database (`data/expenses.db`):
- Read transaction records
- Generate statistical reports
- Analyze spending habits
- Provide budget advice


### 📄 许可证

MIT License

---

## English

A simple Telegram expense tracking bot to help you manage your daily finances.

### Features

- 📝 Record expenses and income
- 📊 Monthly/weekly statistics
- 📈 Category management
- 🔍 Query history
- 🏷️ Tag support
- 💾 Local SQLite storage
- 🤖 **AI-powered analytics** (optional)

### 🤖 AI Features

expense-bot supports AI-powered features to make expense tracking smarter:

| Feature | Description |
|---------|-------------|
| Smart Categorization | AI automatically identifies transaction types |
| Spending Insights | Analyze spending habits |
| Budget Advice | Get budget suggestions based on history |

### Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run setup script (recommended)
./setup.sh

# Or manually configure token in config.yaml
# Run the bot
python -m bot.main
```

### Commands

| Command | Description |
|---------|-------------|
| `/start` | Start the bot |
| `/add` | Add new transaction |
| `/balance` | View monthly stats |
| `/history` | View history |
| `/category` | List categories |
| `/ai` | AI features menu |
| `/insights` | Get AI spending insights |
| `/help` | Show help |

### AI Configuration

```yaml
ai:
  enabled: true
  provider: "openai"  # openai/anthropic/google/ollama/minimax
  model: "gpt-4o-mini"
  api_key: "YOUR_API_KEY"
```

### License

MIT License
