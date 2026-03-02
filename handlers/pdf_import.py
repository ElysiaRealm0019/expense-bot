"""
PDF 导入处理器

处理 PDF 银行账单批量导入功能。

功能：
- 接收用户上传的 PDF 账单
- 解析交易记录（传统正则或 AI 智能解析）
- 预览待导入的交易
- 确认导入到数据库
- 分类自动匹配

作者：SE.AR.PH
"""

import logging
import io
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
    CallbackQueryHandler,
)
from typing import Optional, List, Dict

from core.database import Database
from core.models import TransactionType
from utils.pdf_parser import PDFParser, ParsedTransaction
from utils.pdf_ai_parser import create_parser, AITransaction
from utils.formatters import format_amount, format_date
from utils.config import get_config

logger = logging.getLogger(__name__)

# Conversation states
(
    PDF_CHOOSE_MODE,  # 新增：选择解析模式
    PDF_WAITING,
    PDF_PREVIEW,
    PDF_CONFIRM,
) = range(100, 104)

# 解析模式选择键盘（简化版按钮文字）
MODE_KEYBOARD = ReplyKeyboardMarkup(
    [["🤖 AI智能解析", "📝 传统正则解析"]],
    resize_keyboard=True,
    one_time_keyboard=True
)

CONFIRM_KEYBOARD = ReplyKeyboardMarkup(
    [["✅ 确认导入", "❌ 取消"]],
    resize_keyboard=True,
    one_time_keyboard=True
)


class PDFImportHandler:
    """PDF 导入处理器"""

    def __init__(self, db: Database, config: dict):
        self.db = db
        self.config = config
        self.currency = config.get("currency", {}).get("symbol", "£")
        
        # 存储待处理的交易
        self.pending_transactions = []
        
        # 存储解析器类型
        self.parser_type = None  # "ai" or "regex"
        
        # AI 配置
        self.ai_config = config.get("ai", {}).get("pdf_parser", {})
        self.ai_enabled = self.ai_config.get("enabled", False)

    def _check_auth(self, update: Update) -> bool:
        """检查用户权限"""
        user_id = update.effective_user.id
        allowed_users = self.config.get("security", {}).get("allowed_users", [])
        if allowed_users and user_id not in allowed_users:
            return False
        return True

    async def pdf_import_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /pdfimport 命令"""
        if not self._check_auth(update):
            await update.message.reply_text("⛔ 您没有权限使用此机器人。")
            return ConversationHandler.END
        
        # 检查 AI 是否启用
        if not self.ai_enabled:
            # AI 未启用，直接使用正则模式
            await update.message.reply_text(
                "📄 PDF 账单导入\n\n"
                "请发送您的银行 PDF 账单文件，我将自动解析交易记录～\n\n"
                "支持的格式：\n"
                "• 日期格式：DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD 等\n"
                "• 金额格式：£1,234.56, -50.00, 100CR 等\n"
                "• 自动识别收入/支出类型\n"
                "• 自动匹配分类",
                reply_markup=ReplyKeyboardRemove()
            )
            self.parser_type = "regex"
            return PDF_WAITING
        
        # AI 已启用，让用户选择解析模式
        await update.message.reply_text(
            "📄 PDF 账单导入\n\n"
            "请选择解析方式：\n\n"
            "🤖 AI 智能解析\n"
            "   • 支持复杂格式、图片型账单\n"
            "   • 智能识别交易类型和分类\n"
            "   • 如失败将返回错误\n\n"
            "📝 传统正则解析\n"
            "   • 速度快，成功率高\n"
            "   • 适用于标准格式账单",
            reply_markup=MODE_KEYBOARD
        )
        
        return PDF_CHOOSE_MODE

    async def handle_pdf(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理接收到的 PDF 文件"""
        if not self._check_auth(update):
            await update.message.reply_text("⛔ 您没有权限使用此机器人。")
            return ConversationHandler.END
        
        # 获取文件
        document = update.message.document
        if not document.file_name.lower().endswith('.pdf'):
            await update.message.reply_text("请发送 PDF 文件～")
            return PDF_WAITING
        
        # 检查文件大小
        if document.file_size > 20 * 1024 * 1024:  # 20MB
            await update.message.reply_text("文件太大了，请发送小于 20MB 的文件。")
            return PDF_WAITING
        
        try:
            # 下载文件
            await update.message.reply_text("📥 正在下载 PDF...")
            file = await context.bot.get_file(document.file_id)
            
            # 读取为字节
            pdf_bytes = await file.download_as_bytearray()
            
            # 根据选择的模式解析
            if self.parser_type == "ai":
                return await self._handle_ai_only(update, pdf_bytes)
            else:
                return await self._handle_regex_parse(update, pdf_bytes)
            
        except Exception as e:
            logger.error(f"Failed to process PDF: {e}")
            await update.message.reply_text(
                f"😅 处理 PDF 时出错：{str(e)}\n"
                "请重试或尝试其他文件。"
            )
            return ConversationHandler.END

    async def handle_mode_choose(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理用户选择解析模式"""
        text = update.message.text.strip()
        
        if "AI" in text:
            # 用户选择 AI 解析
            self.parser_type = "ai"
            await update.message.reply_text(
                "🤖 您选择了 AI 智能解析\n\n"
                "请发送您的银行 PDF 账单文件～\n\n"
                "💡 提示：AI 解析支持复杂格式和图片型账单",
                reply_markup=ReplyKeyboardRemove()
            )
            return PDF_WAITING
        elif "正则" in text or "传统" in text:
            # 用户选择正则解析
            self.parser_type = "regex"
            await update.message.reply_text(
                "📝 您选择了传统正则解析\n\n"
                "请发送您的银行 PDF 账单文件～\n\n"
                "支持的格式：\n"
                "• 日期格式：DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD 等\n"
                "• 金额格式：£1,234.56, -50.00, 100CR 等",
                reply_markup=ReplyKeyboardRemove()
            )
            return PDF_WAITING
        else:
            # 无效选择，提示重新选择
            await update.message.reply_text(
                "😅 请点击按钮选择解析方式：\n\n"
                "🤖 使用 AI 智能解析\n"
                "📝 使用传统正则解析",
                reply_markup=MODE_KEYBOARD
            )
            return PDF_CHOOSE_MODE

    async def _handle_ai_only(self, update: Update, pdf_bytes: bytes):
        """只使用 AI 解析，失败返回错误（不自动回退）"""
        try:
            await update.message.reply_text("🤖 正在调用 AI 解析...")
            
            # 获取 AI 配置
            ai_config = self.config.get("ai", {}).get("pdf_parser", {})
            provider = ai_config.get("provider", "minimax")
            api_key = ai_config.get("api_key", "")
            model = ai_config.get("model", "")
            base_url = ai_config.get("base_url", "")
            
            # 检查 API 配置
            if not api_key:
                await update.message.reply_text(
                    "😅 AI 解析未配置 API Key，无法使用。\n"
                    "请选择使用传统正则解析。"
                )
                return ConversationHandler.END
            
            # 获取分类列表
            categories = self.db.get_categories()
            
            # 创建 AI 解析器
            parser = create_parser(
                provider=provider,
                categories=categories,
                api_key=api_key,
                model=model,
                base_url=base_url
            )
            
            # 解析 PDF
            transactions_data = parser.parse(bytes(pdf_bytes))
            
            if not transactions_data:
                await update.message.reply_text(
                    "😕 AI 未能从 PDF 中解析出交易记录。\n\n"
                    "可能原因：\n"
                    "• PDF 内容无法识别\n"
                    "• 账单格式过于复杂\n\n"
                    "请尝试使用传统正则解析（发送 /pdfimport 重新选择）。"
                )
                return ConversationHandler.END
            
            # 转换为统一格式
            self.pending_transactions = self._convert_ai_transactions(transactions_data)
            
            # 显示预览
            preview_text = self._format_ai_preview(self.pending_transactions)
            await update.message.reply_text(preview_text, reply_markup=CONFIRM_KEYBOARD)
            
            return PDF_PREVIEW
            
        except Exception as e:
            logger.error(f"AI parsing failed: {e}")
            await update.message.reply_text(
                f"😅 AI 解析失败：{str(e)}\n\n"
                "请选择使用传统正则解析（发送 /pdfimport 重新选择）。"
            )
            return ConversationHandler.END

    async def _handle_ai_with_fallback(self, update: Update, pdf_bytes: bytes):
        """优先使用 AI 解析，失败自动回退到正则"""
        try:
            # 先尝试 AI 解析
            return await self._handle_ai_parse(update, pdf_bytes)
        except Exception as e:
            logger.warning(f"AI parsing failed, falling back to regex: {e}")
            await update.message.reply_text(
                "🤖 AI 解析未成功，正在自动尝试传统正则解析..."
            )
            self.parser_type = "regex"
            return await self._handle_regex_parse(update, pdf_bytes)

    async def _handle_ai_parse(self, update: Update, pdf_bytes: bytes):
        """使用 AI 解析 PDF"""
        try:
            await update.message.reply_text("🤖 正在调用 AI 解析...")
            
            # 获取 AI 配置
            ai_config = self.config.get("ai", {}).get("pdf_parser", {})
            provider = ai_config.get("provider", "minimax")
            api_key = ai_config.get("api_key", "")
            model = ai_config.get("model", "")
            base_url = ai_config.get("base_url", "")
            
            # 获取分类列表
            categories = self.db.get_categories()
            
            # 创建 AI 解析器
            parser = create_parser(
                provider=provider,
                categories=categories,
                api_key=api_key,
                model=model,
                base_url=base_url
            )
            
            # 解析 PDF
            transactions_data = parser.parse(bytes(pdf_bytes))
            
            if not transactions_data:
                # AI 未解析出结果，抛出异常触发自动回退
                raise ValueError("AI returned no transactions")
            
            # 转换为统一格式
            self.pending_transactions = self._convert_ai_transactions(transactions_data)
            
            # 显示预览
            preview_text = self._format_ai_preview(self.pending_transactions)
            await update.message.reply_text(preview_text, reply_markup=CONFIRM_KEYBOARD)
            
            return PDF_PREVIEW
            
        except (ValueError, Exception) as e:
            # AI 解析失败或无结果，抛出异常由上层处理回退
            logger.warning(f"AI parsing failed: {e}")
            raise

    async def _handle_regex_parse(self, update: Update, pdf_bytes: bytes):
        """使用传统正则解析 PDF"""
        try:
            # 获取分类列表
            categories = self.db.get_categories()
            
            # 解析 PDF
            await update.message.reply_text("🔍 正在解析 PDF...")
            parser = PDFParser(categories)
            transactions = parser.parse_pdf_bytes(bytes(pdf_bytes))
            
            if not transactions:
                await update.message.reply_text(
                    "😕 未能从 PDF 中解析出交易记录。\n\n"
                    "可能原因：\n"
                    "• PDF 格式不支持\n"
                    "• 账单内容是图片而非文本\n"
                    "• 日期/金额格式无法识别\n\n"
                    "请尝试其他文件或手动添加记录。"
                )
                return ConversationHandler.END
            
            # 存储待处理交易
            self.pending_transactions = transactions
            
            # 显示预览
            preview_text = self._format_regex_preview(transactions)
            await update.message.reply_text(preview_text, reply_markup=CONFIRM_KEYBOARD)
            
            return PDF_PREVIEW
            
        except Exception as e:
            logger.error(f"Regex parsing failed: {e}")
            await update.message.reply_text(
                f"😅 解析失败：{str(e)}\n"
                "请重试或尝试其他文件。"
            )
            return ConversationHandler.END

    def _convert_ai_transactions(self, transactions_data: List[Dict]) -> List:
        """将 AI 解析器的输出转换为统一格式"""
        converted = []
        for item in transactions_data:
            try:
                # 创建一个简单对象来存储交易数据
                class AITransaction:
                    pass
                
                tx = AITransaction()
                tx.date = item.get("date", "")
                tx.amount = float(item.get("amount", 0))
                tx.description = item.get("description", "")
                tx.type = item.get("type", "expense")
                tx.category = item.get("category")
                tx.confidence = item.get("confidence", 0.9)
                converted.append(tx)
            except (ValueError, TypeError) as e:
                logger.warning(f"Skipping invalid AI transaction: {item}, error: {e}")
                continue
        
        return converted

    def _format_regex_preview(self, transactions: List[ParsedTransaction], max_show: int = 15) -> str:
        """格式化传统解析预览"""
        total_income = sum(t.amount for t in transactions if t.type == "income")
        total_expense = sum(t.amount for t in transactions if t.type == "expense")
        
        text = f"📋 解析结果预览（传统正则）\n\n"
        text += f"共解析到 {len(transactions)} 笔交易：\n"
        text += f"💰 收入：{format_amount(total_income, self.currency)}\n"
        text += f"💸 支出：{format_amount(total_expense, self.currency)}\n\n"
        
        text += "📝 最近交易记录：\n"
        text += "─" * 30 + "\n"
        
        # 显示部分交易
        show_count = min(max_show, len(transactions))
        for i, t in enumerate(transactions[:show_count]):
            icon = "💰" if t.type == "income" else "💸"
            date_str = format_date(t.date, '%Y-%m-%d')
            amount_str = format_amount(t.amount, self.currency)
            
            # 截断描述
            desc = t.description[:30] + "..." if len(t.description) > 30 else t.description
            
            text += f"{i+1}. {icon} {date_str} | {amount_str}\n"
            text += f"   {desc}\n"
            
            if t.category:
                text += f"   📂 分类：{t.category}\n"
            
            text += "\n"
        
        if len(transactions) > max_show:
            text += f"... 还有 {len(transactions) - max_show} 笔交易\n"
        
        text += "─" * 30 + "\n"
        text += "\n确认导入到数据库？"
        
        return text

    def _format_ai_preview(self, transactions: List[AITransaction], max_show: int = 15) -> str:
        """格式化 AI 解析预览"""
        total_income = sum(t.amount for t in transactions if t.type == "income")
        total_expense = sum(t.amount for t in transactions if t.type == "expense")
        
        text = f"📋 解析结果预览（AI 智能解析）\n\n"
        text += f"共解析到 {len(transactions)} 笔交易：\n"
        text += f"💰 收入：{format_amount(total_income, self.currency)}\n"
        text += f"💸 支出：{format_amount(total_expense, self.currency)}\n\n"
        
        text += "📝 最近交易记录：\n"
        text += "─" * 30 + "\n"
        
        # 显示部分交易
        show_count = min(max_show, len(transactions))
        for i, t in enumerate(transactions[:show_count]):
            icon = "💰" if t.type == "income" else "💸"
            date_str = t.date
            amount_str = format_amount(t.amount, self.currency)
            
            # 截断描述
            desc = t.description[:30] + "..." if len(t.description) > 30 else t.description
            
            text += f"{i+1}. {icon} {date_str} | {amount_str}\n"
            text += f"   {desc}\n"
            
            if t.category:
                text += f"   📂 分类：{t.category}\n"
            
            if t.confidence < 1.0:
                text += f"   🎯 置信度：{int(t.confidence * 100)}%\n"
            
            text += "\n"
        
        if len(transactions) > max_show:
            text += f"... 还有 {len(transactions) - max_show} 笔交易\n"
        
        text += "─" * 30 + "\n"
        text += "\n确认导入到数据库？"
        
        return text

    async def handle_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理确认导入"""
        text = update.message.text.strip()
        
        if "尝试传统" in text or "传统解析" in text:
            # 用户选择尝试传统解析
            self.parser_type = "regex"
            await update.message.reply_text(
                "📝 切换到传统正则解析\n\n"
                "请重新发送 PDF 文件",
                reply_markup=ReplyKeyboardRemove()
            )
            self.pending_transactions = []
            return PDF_WAITING
        elif text in ["✅ 确认导入", "确认", "confirm", "yes", "y"]:
            return await self._do_import(update, context)
        elif text in ["❌ 取消", "取消", "cancel", "no", "n"]:
            await update.message.reply_text(
                "已取消导入～",
                reply_markup=ReplyKeyboardRemove()
            )
            self.pending_transactions = []
            return ConversationHandler.END
        else:
            await update.message.reply_text(
                "请点击按钮确认：\n"
                "✅ 确认导入\n"
                "❌ 取消",
                reply_markup=CONFIRM_KEYBOARD
            )
            return PDF_PREVIEW

    async def _do_import(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """执行导入"""
        if not self.pending_transactions:
            await update.message.reply_text(
                "没有待导入的交易～",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END
        
        try:
            imported = 0
            failed = 0
            category_cache = {}  # 分类名称 -> ID 缓存
            
            # 获取所有分类
            all_categories = self.db.get_categories()
            for cat in all_categories:
                category_cache[cat['name'].lower()] = cat['id']
            
            # 获取默认分类（用于未匹配的情况）
            default_expense_cat = category_cache.get('其他支出')
            default_income_cat = category_cache.get('其他收入')
            
            for t in self.pending_transactions:
                try:
                    # 统一接口：无论 AI 还是 Regex 都使用相同字段
                    # AI: date 是字符串, Regex: date 是 datetime
                    tx_date = t.date
                    if isinstance(tx_date, str):
                        # 解析 AI 返回的日期字符串
                        from datetime import datetime
                        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y']:
                            try:
                                tx_date = datetime.strptime(tx_date, fmt)
                                break
                            except ValueError:
                                continue
                        if isinstance(tx_date, str):
                            tx_date = datetime.now()  # 无法解析则使用当前日期
                    
                    # 确定分类 ID
                    category_id = None
                    
                    if t.category:
                        # 尝试精确匹配
                        cat_lower = t.category.lower()
                        if cat_lower in category_cache:
                            category_id = category_cache[cat_lower]
                        else:
                            # 尝试模糊匹配
                            for cat_name, cat_id in category_cache.items():
                                if cat_name in cat_lower or cat_lower in cat_name:
                                    category_id = cat_id
                                    break
                    
                    # 使用默认分类
                    if category_id is None:
                        if t.type == "expense":
                            category_id = default_expense_cat or 1
                        else:
                            category_id = default_income_cat or 1
                    
                    # 添加交易
                    tx_type = TransactionType.INCOME if t.type == "income" else TransactionType.EXPENSE
                    
                    self.db.add_transaction(
                        amount=abs(t.amount),
                        type_=tx_type,
                        category_id=category_id,
                        description=t.description[:200],  # 限制描述长度
                        date=tx_date
                    )
                    
                    imported += 1
                    
                except Exception as e:
                    logger.error(f"Failed to import transaction: {e}")
                    failed += 1
            
            # 清理
            self.pending_transactions = []
            parser_type = self.parser_type
            
            # 显示结果
            result_text = f"✅ 导入完成！\n\n"
            result_text += f"成功导入：{imported} 笔\n"
            result_text += f"解析方式：{'🤖 AI 智能解析' if parser_type == 'ai' else '📝 传统正则解析'}\n"
            
            if failed > 0:
                result_text += f"导入失败：{failed} 笔\n"
            
            await update.message.reply_text(
                result_text,
                reply_markup=ReplyKeyboardRemove()
            )
            
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Import failed: {e}")
            await update.message.reply_text(
                f"😅 导入失败：{str(e)}",
                reply_markup=ReplyKeyboardRemove()
            )
            self.pending_transactions = []
            return ConversationHandler.END

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """取消操作"""
        self.pending_transactions = []
        self.parser_type = None
        await update.message.reply_text(
            "已取消操作～",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END


def setup_pdf_handlers(application: Application):
    """设置 PDF 导入处理器"""
    config = get_config()
    db_path = config.get("database.path", "data/expenses.db")
    db = Database(db_path)

    handler = PDFImportHandler(db, config._config)

    # PDF 导入 ConversationHandler
    pdf_conv = ConversationHandler(
        entry_points=[CommandHandler("pdfimport", handler.pdf_import_command)],
        states={
            PDF_CHOOSE_MODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler.handle_mode_choose)
            ],
            PDF_WAITING: [
                MessageHandler(filters.Document.PDF, handler.handle_pdf)
            ],
            PDF_PREVIEW: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler.handle_confirm)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", handler.cancel),
        ],
        name="pdf_import",
        persistent=False,
    )
    application.add_handler(pdf_conv)
    
    logger.info("PDF import handlers registered")
