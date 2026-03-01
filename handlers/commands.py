"""
Telegram 命令处理器模块

提供所有 bot 命令的处理函数，包括：
- /start - 欢迎消息
- /add - 添加收支记录
- /balance - 查看统计
- /history - 历史记录
- /category - 分类管理
- /help - 帮助信息

优化：
- 完善的错误处理
- 更友好的用户输入验证
- 取消操作支持
- 快捷输入支持
- 键盘按钮
"""

import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from typing import Optional

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

# 键盘布局
TYPE_KEYBOARD = ReplyKeyboardMarkup(
    [["💸 支出", "💰 收入"], ["❌ 取消"]],
    resize_keyboard=True,
    one_time_keyboard=True
)

CANCEL_KEYBOARD = ReplyKeyboardMarkup(
    [["❌ 取消"]],
    resize_keyboard=True,
    one_time_keyboard=True
)

SKIP_KEYBOARD = ReplyKeyboardMarkup(
    [["跳过"]],
    resize_keyboard=True,
    one_time_keyboard=True
)


class CommandHandlers:
    """命令处理器类"""

    def __init__(self, db: Database, stats: Statistics, config: dict):
        self.db = db
        self.stats = stats
        self.config = config
        self.currency = config.get("currency", {}).get("symbol", "£")

    def _check_auth(self, update: Update) -> bool:
        """检查用户权限"""
        user_id = update.effective_user.id
        allowed_users = self.config.get("security", {}).get("allowed_users", [])
        if allowed_users and user_id not in allowed_users:
            return False
        return True

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """取消操作"""
        await update.message.reply_text(
            "已取消操作～",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data.clear()
        return ConversationHandler.END

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """全局错误处理器"""
        logger.error(f"Error: {context.error}", exc_info=context.error)
        if update and update.message:
            await update.message.reply_text(
                "😅 出错了，请重试～",
                reply_markup=ReplyKeyboardRemove()
            )
        context.user_data.clear()
        return ConversationHandler.END

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /start 命令"""
        if not self._check_auth(update):
            await update.message.reply_text("⛔ 您没有权限使用此机器人。")
            return
        
        user = update.effective_user
        welcome_text = f"""
🎉 欢迎使用记账机器人，{user.first_name}！♪

我是你的私人财务小助手～帮助你记录每一笔收支。

📝 主要功能：
• 记录支出和收入
• 查看月度/周度统计
• 分类管理
• 历史记录查询

💡 快速开始：
• 输入 /add 添加记录
• 输入 /balance 查看统计
• 输入 /help 查看帮助
        """
        await update.message.reply_text(welcome_text.strip())

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /help 命令"""
        if not self._check_auth(update):
            await update.message.reply_text("⛔ 您没有权限使用此机器人。")
            return
        
        help_text = """
📖 命令帮助

/ start - 启动机器人
/ add - 记录支出/收入
/ balance - 查看本月统计
/ history - 查看历史记录
/ category - 查看分类
/ help - 显示帮助信息

💡 使用技巧：
• 添加记录时可直接输入金额（如：100）
• 回复"取消"可终止当前操作
        """
        await update.message.reply_text(help_text.strip())

    async def balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /balance 命令 - 查看统计"""
        if not self._check_auth(update):
            await update.message.reply_text("⛔ 您没有权限使用此机器人。")
            return
        
        try:
            monthly = self.stats.get_monthly_summary()

            text = f"""📊 本月统计

💰 收入：{format_amount(monthly.income, self.currency)}
💸 支出：{format_amount(monthly.expense, self.currency)}
📈 结余：{format_amount(monthly.balance, self.currency)}"""

            # 获取分类统计
            expense_stats = self.stats.get_category_stats(
                TransactionType.EXPENSE,
                limit=5
            )

            if expense_stats:
                text += "\n\n📊 支出分类TOP5：\n"
                for stat in expense_stats:
                    text += f"  {stat.emoji} {stat.category_name}: {format_amount(stat.total, self.currency)} ({stat.percentage:.1f}%)\n"

            await update.message.reply_text(text.strip())
        except Exception as e:
            logger.error(f"Balance command error: {e}")
            await update.message.reply_text("获取统计失败，请稍后重试。")

    async def history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /history 命令 - 查看历史记录"""
        if not self._check_auth(update):
            await update.message.reply_text("⛔ 您没有权限使用此机器人。")
            return
        
        try:
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

            await update.message.reply_text(text.strip())
        except Exception as e:
            logger.error(f"History command error: {e}")
            await update.message.reply_text("获取历史记录失败，请稍后重试。")

    async def category_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /category 命令 - 查看分类"""
        if not self._check_auth(update):
            await update.message.reply_text("⛔ 您没有权限使用此机器人。")
            return
        
        try:
            expense_cats = self.db.get_categories(TransactionType.EXPENSE)
            income_cats = self.db.get_categories(TransactionType.INCOME)

            text = "📂 分类列表\n\n💸 支出分类：\n"
            for cat in expense_cats:
                text += f"  {cat['emoji']} {cat['name']}\n"

            text += "\n💰 收入分类：\n"
            for cat in income_cats:
                text += f"  {cat['emoji']} {cat['name']}\n"

            await update.message.reply_text(text.strip())
        except Exception as e:
            logger.error(f"Category command error: {e}")
            await update.message.reply_text("获取分类失败，请稍后重试。")

    async def add_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /add 命令 - 添加记录"""
        if not self._check_auth(update):
            await update.message.reply_text("⛔ 您没有权限使用此机器人。")
            return ConversationHandler.END
        
        await update.message.reply_text(
            "📝 添加新记录\n\n请选择类型：",
            reply_markup=TYPE_KEYBOARD
        )
        return SELECT_TYPE

    async def select_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """选择收支类型"""
        text = update.message.text.strip()

        # 取消操作
        if text in ["取消", "❌ 取消", "cancel"]:
            return await self.cancel(update, context)

        if text in ["1", "💸 支出", "支出", "expense"]:
            context.user_data["type"] = TransactionType.EXPENSE
            await update.message.reply_text(
                "已选择支出💸\n请输入金额：",
                reply_markup=ReplyKeyboardRemove()
            )
        elif text in ["2", "💰 收入", "收入", "income"]:
            context.user_data["type"] = TransactionType.INCOME
            await update.message.reply_text(
                "已选择收入💰\n请输入金额：",
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            # 尝试直接解析为金额（默认为支出）
            try:
                amount = self._parse_amount(text)
                context.user_data["type"] = TransactionType.EXPENSE
                context.user_data["amount"] = amount
                return await self._show_categories(update, context)
            except ValueError:
                await update.message.reply_text(
                    "请选择类型或直接输入金额～\n1️⃣ 支出\n2️⃣ 收入",
                    reply_markup=TYPE_KEYBOARD
                )
                return SELECT_TYPE

        return ENTER_AMOUNT

    def _parse_amount(self, text: str) -> float:
        """解析金额"""
        # 移除常见货币符号和逗号
        cleaned = text.replace(",", "").replace("£", "").replace("$", "").replace("¥", "").strip()
        return float(cleaned)

    async def enter_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """输入金额"""
        text = update.message.text.strip()
        
        # 取消操作
        if text in ["取消", "❌ 取消", "cancel"]:
            return await self.cancel(update, context)

        try:
            amount = self._parse_amount(text)
            if amount <= 0:
                await update.message.reply_text("金额必须大于0，请重新输入：")
                return ENTER_AMOUNT
            if amount > 999999999:
                await update.message.reply_text("金额太大了，请检查后重新输入：")
                return ENTER_AMOUNT

            context.user_data["amount"] = amount
            return await self._show_categories(update, context)
        except ValueError:
            await update.message.reply_text("请输入有效金额（如：100 或 99.50）：")
            return ENTER_AMOUNT

    async def _show_categories(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """显示分类列表"""
        type_ = context.user_data.get("type", TransactionType.EXPENSE)
        categories = self.db.get_categories(type_)

        # 构建分类文本和键盘
        text = "请选择分类：\n\n"
        keyboard = []
        row = []
        
        for i, cat in enumerate(categories):
            text += f"{i+1}. {cat['emoji']} {cat['name']}\n"
            row.append(cat['emoji'] + cat['name'])
            if len(row) == 2:
                keyboard.append(row)
                row = []
        
        if row:
            keyboard.append(row)
        
        keyboard.append(["❌ 取消"])
        
        await update.message.reply_text(
            text,
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return SELECT_CATEGORY

    async def select_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """选择分类（兼容旧接口）"""
        text = update.message.text.strip()
        
        # 取消操作
        if text in ["取消", "❌ 取消", "cancel"]:
            return await self.cancel(update, context)

        # 尝试通过名称匹配
        type_ = context.user_data.get("type", TransactionType.EXPENSE)
        categories = self.db.get_categories(type_)
        
        for i, cat in enumerate(categories):
            if text == cat['emoji'] + cat['name'] or text == cat['name']:
                context.user_data["category_id"] = cat['id']
                return await self._ask_description(update, context)
        
        # 尝试数字索引
        try:
            idx = int(text) - 1
            if 0 <= idx < len(categories):
                context.user_data["category_id"] = categories[idx]["id"]
                return await self._ask_description(update, context)
        except ValueError:
            pass
        
        await update.message.reply_text("请选择有效的分类：")
        return SELECT_CATEGORY

    async def _ask_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """询问备注"""
        await update.message.reply_text(
            "请输入备注（可选，直接发送跳过）：",
            reply_markup=ReplyKeyboardMarkup([["跳过", "❌ 取消"]], resize_keyboard=True)
        )
        return ENTER_DESCRIPTION

    async def enter_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """输入备注"""
        text = update.message.text.strip()
        
        # 取消或跳过
        if text in ["跳过", "skip", "直接发送跳过"]:
            text = ""
        elif text in ["取消", "❌ 取消", "cancel"]:
            return await self.cancel(update, context)

        amount = context.user_data.get("amount")
        type_ = context.user_data.get("type", TransactionType.EXPENSE)
        category_id = context.user_data.get("category_id")

        if not all([amount, category_id]):
            await update.message.reply_text("记录失败，请重试 /add")
            return ConversationHandler.END

        # 获取分类名称
        category_name = self.db.get_category_name(category_id)
        
        result = self.db.add_transaction(
            amount=amount,
            type_=type_,
            category_id=category_id,
            description=text
        )

        if result < 0:
            await update.message.reply_text("保存失败，请重试～")
            return ConversationHandler.END

        icon = "💰" if type_ == TransactionType.INCOME else "💸"
        await update.message.reply_text(
            f"✅ 记录已保存！\n\n"
            f"{icon} {format_amount(amount, self.currency)}\n"
            f"📂 分类：{category_name}"
            + (f"\n📝 备注：{text}" if text else ""),
            reply_markup=ReplyKeyboardRemove()
        )

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
            SELECT_TYPE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.select_type)
            ],
            ENTER_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.enter_amount)
            ],
            SELECT_CATEGORY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.select_category)
            ],
            ENTER_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.enter_description)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", handlers.cancel),
        ],
        name="add_transaction",
        persistent=False,
    )
    application.add_handler(add_conv)
    
    # 错误处理
    application.add_error_handler(handlers.error_handler)
