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

编辑 `config.yaml`，填入你的 Telegram Bot Token：

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
python -m expense_bot.cli --help
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
| `/help` | 显示帮助信息 |

### ⚙️ 配置说明

```yaml
bot:
  token: "YOUR_TELEGRAM_BOT_TOKEN"  # 必填
  name: "expense_bot"               # 可选

database:
  path: "data/expenses.db"          # 数据库路径

currency:
  symbol: "£"                       # 货币符号
  name: "GBP"                       # 货币名称

settings:
  max_history: 50                   # 历史记录上限
  timezone: "Europe/London"         # 时区
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

### Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure bot token in config.yaml

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
| `/help` | Show help |

### License

MIT License
