"""
Telegram 命令处理器模块

提供所有 bot 命令的处理函数，包括：
- /start - 欢迎消息
- /add - 添加收支记录
- /balance - 查看统计
- /history - 历史记录
- /category - 分类管理
- /help - 帮助信息
"""

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from typing import Optional
import logging

from core.database import Database
from core.models import TransactionType
from core.statistics import Statistics
from utils.config import get_config
from utils.formatters import format_amount, format_date

logger = logging.getLogger(__name__)

# Conversation states
(
    SELECT_TYPE,
    ENTER_AMOUNT,
    SELECT_CATEGORY,
    ENTER_DESCRIPTION,
) = range(4)


class CommandHandlers:
    """命令处理器类"""

    def __init__(self, db: Database, stats: Statistics, config: dict):
        self.db = db
        self.stats = stats
        self.config = config
        self.currency = config.get("currency", {}).get("symbol", "£")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /start 命令"""
        # 检查用户权限
        user_id = update.effective_user.id
        allowed_users = context.bot_data.get("config", {}).get("security", {}).get("allowed_users", [])
        if allowed_users and user_id not in allowed_users:
            await update.message.reply_text("⛔ 您没有权限使用此机器人。")
            return
        
        user = update.effective_user
        welcome_text = f"""
🎉 欢迎使用记账机器人！

我是你的私人财务小助手～帮助你记录每一笔收支。

📝 主要功能：
• 记录支出和收入
• 查看月度/周度统计
• 分类管理
• 历史记录查询

💡 开始使用：
输入 /add 添加第一笔记录吧！
        """
        await update.message.reply_text(welcome_text)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /help 命令"""
        help_text = """
📖 命令帮助

/ start - 启动机器人
/ add - 记录支出/收入
/ balance - 查看本月统计
/ history - 查看历史记录
/ category - 管理分类
/ help - 显示帮助信息

💡 使用提示：
• 添加记录时，按照提示输入金额和分类
• 支持中英文分类名称
• 可以添加备注说明
        """
        await update.message.reply_text(help_text)

    async def balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /balance 命令 - 查看统计"""
        monthly = self.stats.get_monthly_summary()

        text = f"""
📊 本月统计

💰 收入：{format_amount(monthly.income, self.currency)}
💸 支出：{format_amount(monthly.expense, self.currency)}
📈 结余：{format_amount(monthly.balance, self.currency)}
        """

        # 获取分类统计
        expense_stats = self.stats.get_category_stats(
            TransactionType.EXPENSE,
            limit=5
        )

        if expense_stats:
            text += "\n\n📊 支出分类TOP5：\n"
            for stat in expense_stats:
                text += f"  {stat.emoji} {stat.category_name}: {format_amount(stat.total, self.currency)} ({stat.percentage:.1f}%)\n"

        await update.message.reply_text(text)

    async def history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /history 命令 - 查看历史记录"""
        transactions = self.db.get_transactions(limit=10)

        if not transactions:
            await update.message.reply_text("暂无记录，快去添加一笔吧！")
            return

        text = "📋 最近记录：\n\n"
        for t in transactions:
            icon = "💰" if t.type == TransactionType.INCOME else "💸"
            text += f"{icon} {format_amount(t.amount, self.currency)} - {t.category_name}\n"
            if t.description:
                text += f"   📝 {t.description}\n"
            text += f"   📅 {format_date(t.date, '%Y-%m-%d %H:%M')}\n\n"

        await update.message.reply_text(text)

    async def category_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /category 命令 - 查看分类"""
        expense_cats = self.db.get_categories(TransactionType.EXPENSE)
        income_cats = self.db.get_categories(TransactionType.INCOME)

        text = "📂 分类列表\n\n"

        text += "💸 支出分类：\n"
        for cat in expense_cats:
            text += f"  {cat['emoji']} {cat['name']}\n"

        text += "\n💰 收入分类：\n"
        for cat in income_cats:
            text += f"  {cat['emoji']} {cat['name']}\n"

        await update.message.reply_text(text)

    async def add_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /add 命令 - 添加记录"""
        await update.message.reply_text(
            "📝 添加新记录\n\n"
            "请选择类型：\n"
            "1️⃣ 支出\n"
            "2️⃣ 收入\n\n"
            "回复数字或直接输入金额（默认支出）"
        )
        return SELECT_TYPE

    async def select_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """选择收支类型"""
        text = update.message.text.strip()

        if text in ["1", "支出", "expense"]:
            context.user_data["type"] = TransactionType.EXPENSE
            await update.message.reply_text("已选择支出💸\n请输入金额：")
        elif text in ["2", "收入", "income"]:
            context.user_data["type"] = TransactionType.INCOME
            await update.message.reply_text("已选择收入💰\n请输入金额：")
        else:
            # 尝试直接解析为金额（默认为支出）
            try:
                amount = float(text.replace(",", ""))
                context.user_data["type"] = TransactionType.EXPENSE
                context.user_data["amount"] = amount
                return await self.select_category(update, context)
            except ValueError:
                await update.message.reply_text("请输入有效选项：\n1️⃣ 支出\n2️⃣ 收入")
                return SELECT_TYPE

        return ENTER_AMOUNT

    async def enter_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """输入金额"""
        try:
            amount = float(update.message.text.replace(",", "").replace("£", "").replace("$", ""))
            if amount <= 0:
                await update.message.reply_text("金额必须大于0，请重新输入：")
                return ENTER_AMOUNT

            context.user_data["amount"] = amount
            return await self.select_category(update, context)
        except ValueError:
            await update.message.reply_text("请输入有效金额：")
            return ENTER_AMOUNT

    async def select_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """选择分类"""
        type_ = context.user_data.get("type", TransactionType.EXPENSE)
        categories = self.db.get_categories(type_)

        text = "请选择分类：\n\n"
        for i, cat in enumerate(categories, 1):
            text += f"{i}. {cat['emoji']} {cat['name']}\n"

        await update.message.reply_text(text)
        return SELECT_CATEGORY

    async def enter_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """输入备注"""
        try:
            idx = int(update.message.text.strip()) - 1
            type_ = context.user_data.get("type", TransactionType.EXPENSE)
            categories = self.db.get_categories(type_)

            if idx < 0 or idx >= len(categories):
                await update.message.reply_text("请输入有效的分类编号：")
                return SELECT_CATEGORY

            context.user_data["category_id"] = categories[idx]["id"]

            await update.message.reply_text("请输入备注（可选，直接发送跳过）：")
            return ENTER_DESCRIPTION
        except ValueError:
            await update.message.reply_text("请输入有效的分类编号：")
            return SELECT_CATEGORY

    async def save_transaction(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """保存交易记录"""
        description = update.message.text.strip() if update.message.text.strip() else ""

        amount = context.user_data.get("amount")
        type_ = context.user_data.get("type", TransactionType.EXPENSE)
        category_id = context.user_data.get("category_id")

        if not all([amount, category_id]):
            await update.message.reply_text("记录失败，请重试 /add")
            return ConversationHandler.END

        # 获取分类名称
        category_name = self.db.get_category_name(category_id)
        
        self.db.add_transaction(
            amount=amount,
            type_=type_,
            category_id=category_id,
            description=description
        )

        icon = "💰" if type_ == TransactionType.INCOME else "💸"
        await update.message.reply_text(
            f"✅ 记录已保存！\n\n"
            f"{icon} {format_amount(amount, self.currency)}\n"
            f"📂 分类：{category_name}"
            + (f"\n📝 备注：{description}" if description else "")
        )

        # 清理用户数据
        context.user_data.clear()
        return ConversationHandler.END


def setup_handlers(application: Application):
    """设置所有命令处理器"""
    config = get_config()
    db_path = config.get("database.path", "data/expenses.db")
    db = Database(db_path)
    stats = Statistics(db)

    handlers = CommandHandlers(db, stats, config._config)

    # 普通命令
    application.add_handler(CommandHandler("start", handlers.start_command))
    application.add_handler(CommandHandler("help", handlers.help_command))
    application.add_handler(CommandHandler("balance", handlers.balance_command))
    application.add_handler(CommandHandler("history", handlers.history_command))
    application.add_handler(CommandHandler("category", handlers.category_command))

    # 添加记录 - ConversationHandler
    add_conv = ConversationHandler(
        entry_points=[CommandHandler("add", handlers.add_command)],
        states={
            SELECT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.select_type)],
            ENTER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.enter_amount)],
            SELECT_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.select_category)],
            ENTER_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.save_transaction)],
        },
        fallbacks=[],
        name="add_transaction",
        persistent=False,
    )
    application.add_handler(add_conv)
