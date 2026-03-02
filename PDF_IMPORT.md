# PDF 银行账单导入功能

使用 `/pdfimport` 命令可以批量导入银行 PDF 账单。

## 功能特性

- 📄 支持 PDF 格式银行账单解析
- 🗓️ 自动识别多种日期格式 (DD/MM/YYYY, YYYY-MM-DD, DD Mon YYYY 等)
- 💷 自动识别金额格式 (£1,234.56, -50.00, 100CR 等)
- 🏷️ 自动判断交易类型（收入/支出）
- 📂 根据描述自动匹配分类
- ✅ 预览确认机制，确保导入正确

## 支持的银行账单格式

### 日期格式
- `DD/MM/YYYY` (01/01/2024)
- `DD-MM-YYYY` (01-01-2024)
- `DD.MM.YYYY` (01.01.2024)
- `YYYY-MM-DD` (2024-01-01)
- `DD Mon YYYY` (01 Jan 2024)
- `Mon DD, YYYY` (Jan 01, 2024)

### 金额格式
- `£1,234.56` (带货币符号)
- `-50.00` (负数)
- `100.50 CR` (贷记)
- `250 DR` (借记)

### 自动分类关键词

| 分类 | 关键词 |
|------|--------|
| 餐饮 | restaurant, cafe, starbucks, mcdonald, 外卖, 餐厅 |
| 交通 | uber, lyft, taxi, train, petrol, 打车, 汽油 |
| 购物 | amazon, ebay, tesco, sainsbury, 购物, 超市 |
| 娱乐 | netflix, spotify, cinema, game, 电影, 游戏 |
| 居住 | rent, utility, electric, 房租, 水电 |
| 医疗 | pharmacy, doctor, hospital, 医院, 药店 |
| 教育 | school, university, course, 学校, 大学 |
| 工资 | salary, wage, payroll, 工资, 薪资 |
| 奖金 | bonus, commission, 奖金, 佣金 |
| 投资 | dividend, interest, stock, 投资, 股息 |

## 使用方法

1. 发送 `/pdfimport` 命令
2. 上传银行 PDF 账单文件
3. 系统解析并显示预览
4. 确认导入

## 示例

```
用户: /pdfimport
机器人: 📄 PDF 账单导入
请发送您的银行 PDF 账单文件...

用户: [上传 PDF 文件]
机器人: 📥 正在下载 PDF...
机器人: 🔍 正在解析 PDF...
机器人: 📋 解析结果预览
共解析到 15 笔交易：
💰 收入：£2,500.00
💸 支出：£450.00

1. 💸 2024-01-05 | £4.50
   STARBUCKS COFFEE
   📂 分类：餐饮
...

确认导入到数据库？
[✅ 确认导入] [❌ 取消]

用户: ✅ 确认导入
机器人: ✅ 导入完成！
成功导入：15 笔
```

## 文件结构

```
expense-bot/
├── utils/
│   └── pdf_parser.py      # PDF 解析核心模块
├── handlers/
│   ├── commands.py        # 原有命令处理
│   └── pdf_import.py      # PDF 导入处理
└── bot/
    └── main.py            # 主程序入口
```

## 技术栈

- **PyMuPDF** (pymupdf) - PDF 解析
- **正则表达式** - 日期/金额识别
- **关键词匹配** - 分类自动匹配
