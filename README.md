# Telegram Expense Bot

一个简洁的 Telegram 记账机器人，帮助你追踪日常开支。

## 功能特性

- 📝 记录支出/收入
- 📊 月度支出统计
- 📈 分类管理
- 🔍 查询历史记录
- 💾 数据本地存储 (SQLite)

## 项目结构

```
expense-bot/
├── bot/              # Bot 入口和初始化
├── core/             # 核心业务逻辑
├── handlers/         # Telegram 命令处理器
├── utils/            # 工具函数
├── config.yaml       # 配置文件
└── requirements.txt  # Python 依赖
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 Bot

编辑 `config.yaml`，填入你的 Telegram Bot Token：

```yaml
bot:
  token: "YOUR_BOT_TOKEN_HERE"
```

### 3. 运行 Bot

```bash
python -m bot.main
```

## 命令列表

| 命令 | 说明 |
|------|------|
| `/start` | 启动机器人 |
| `/add` | 记录支出/收入 |
| `/balance` | 查看本月统计 |
| `/history` | 查看历史记录 |
| `/category` | 管理分类 |
| `/help` | 帮助信息 |

## 配置说明

```yaml
bot:
  token: "YOUR_TELEGRAM_BOT_TOKEN"
  admin_id: 123456789  # 可选：管理员 ID

database:
  path: "data/expenses.db"

categories:
  expense:
    - 餐饮
    - 交通
    - 购物
    - 娱乐
    - 其他
  income:
    - 工资
    - 兼职
    - 投资
    - 其他
```

## 开发

```bash
# 格式化代码
black .

# 类型检查
mypy .

# 运行测试
pytest
```

## 许可证

MIT License
