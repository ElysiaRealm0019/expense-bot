# HEARTBEAT.md

# 每日晨间简报 (08:30 Europe/London)

每日上午 08:30 执行以下检查并生成报告：

## 检查项目

### 1. 天气 (Bournemouth)
```bash
curl -s "wttr.in/Bournemouth?format=%C+%t+%h+%w"
```
- 温度、体感温度、湿度、风速
- 预报：最高/最低温

### 2. Google 日历 (多日历汇总)
```bash
# 获取所有日历的事件（--all 获取所有日历，--days 3 获取未来3天）
gog calendar events --all --days 3 --plain
```
- 自动汇总所有 Google 账号的所有日历事件

### 3. 新闻摘要 (Exa)
```bash
mcporter call 'exa.web_search_exa(query: "major news today", numResults: 5)'
```
- 3-4 条今日要闻

### 4. 费用报告 (所有模型)
```bash
# 调用费用估算脚本
python3 ~/.openclaw/skills/gemini-cost-tracker/scripts/extract-cost.py --yesterday
```
- MiniMax: £5/月固定（无限量）
- 其他模型: 实际 API 消耗（USD）
- 展示格式：💰 MiniMax £5 + Gemini $X.XX

### 5. 当日星盘 (Mingli)
```bash
# 基础星盘数据已配置
# 今日关键词：西方占星 + 八字 + 数字命理
```
- 射手座今日运势
- 八字五行建议
- 数字命理提示

## 输出格式

发送 Telegram 消息：

```markdown
## 📋 今日简报 — YYYY年M月D日

### 🌤️ 伯恩茅斯天气
当前: X°C，天气描述
预报: 最高X°C / 最低X°C
→ 建议

### 📰 今日要闻
1. 新闻标题
2. 新闻标题
3. 新闻标题

### 📅 日历
- 事件1
- 事件2

### 💊 今日提醒
- ✅ 维生素 B、D、鱼肝油
- 🧘 运动：瑜伽垫 or VR

### 💰 费用
- MiniMax: £5/月 (固定不限量)
- Gemini + 其他: $X.XX USD (实际消耗)

### 🔮 当日运势
- 星座运势简述
- 五行建议
- 幸运数字/颜色

---
**时间**: 08:30 GMT | **状态**: 正常
```

## 重要提醒

- 维生素 B、D、鱼肝油
- 运动目标：瑜伽垫或 VR
- 记录体重/运动数据到 Notion（如有）

## 定时任务

### 每日简报
- **Cron ID**: daily-briefing
- **时间**: 0 8 * * * (Europe/London)
- **内容**: 天气 + 日历 + 新闻 + 费用 + 星盘

### 重要邮件监控
- **Cron ID**: hourly-email-check
- **时间**: 0 * * * * (每小时)
- **内容**: 检查所有 Gmail 账号的未读重要邮件
- **脚本**: `scripts/check-important-emails-gog.py` (gog CLI)
- **关键词**: 学校、包裹、快递、银行卡、银行账单、成绩、考试、会议、预约
- **仅在发现重要邮件时发送通知**
