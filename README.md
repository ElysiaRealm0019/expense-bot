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
python -m bot.main
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
