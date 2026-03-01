"""
格式化工具模块

提供各种数据格式化函数：
- 金额格式化
- 日期格式化
- 交易列表格式化
- 输入验证
"""

from datetime import datetime
from typing import Optional, List
from core.models import Transaction


def format_amount(amount: float, currency: str = "£") -> str:
    """
    格式化金额显示

    Args:
        amount: 金额
        currency: 货币符号

    Returns:
        格式化后的金额字符串，如 "£100.00"
    """
    return f"{currency}{amount:.2f}"


def format_date(date: datetime, format_str: str = "%Y-%m-%d %H:%M") -> str:
    """
    格式化日期显示

    Args:
        date: datetime 对象
        format_str: 格式字符串

    Returns:
        格式化后的日期字符串
    """
    return date.strftime(format_str)


def format_expense_list(transactions: List[Transaction], currency: str = "£") -> str:
    """
    格式化交易列表为可读文本

    Args:
        transactions: Transaction 对象列表
        currency: 货币符号

    Returns:
        格式化的文本
    """
    if not transactions:
        return "暂无记录。"

    lines = []
    for t in transactions:
        # 图标
        icon = "💰" if t.type.value == "income" else "💸"

        # 日期
        date_str = format_date(t.date, "%m/%d %H:%M")

        # 构建行
        line = f"{icon} {date_str} - {format_amount(t.amount, currency)} - {t.category_name}"

        # 添加描述
        if t.description:
            line += f"\n   📝 {t.description}"

        # 添加标签
        if t.tags:
            tag_names = ", ".join(f"#{tag.name}" for tag in t.tags)
            line += f"\n   🏷️ {tag_names}"

        lines.append(line)

    return "\n\n".join(lines)


def validate_amount(amount_str: str) -> Optional[float]:
    """
    验证并解析金额字符串

    Args:
        amount_str: 金额字符串

    Returns:
        解析后的金额（最多2位小数），无效返回 None
    """
    try:
        # 移除常见货币符号和逗号
        cleaned = amount_str.replace(",", "").replace("£", "").replace("$", "").replace("¥", "").strip()
        amount = float(cleaned)
        if amount <= 0:
            return None
        return round(amount, 2)
    except (ValueError, TypeError):
        return None


def validate_category(category: str) -> bool:
    """
    验证分类名称

    Args:
        category: 分类名称

    Returns:
        是否有效
    """
    if not category:
        return False
    # 允许中英文、数字和常见标点
    return len(category) <= 50


def format_category_list(categories: List[dict]) -> str:
    """格式化分类列表"""
    if not categories:
        return "暂无分类。"

    lines = []
    for cat in categories:
        lines.append(f"{cat['emoji']} {cat['name']}")

    return "\n".join(lines)


def format_statistics_summary(
    income: float,
    expense: float,
    currency: str = "£"
) -> str:
    """格式化统计摘要"""
    balance = income - expense

    lines = [
        f"💰 收入：{format_amount(income, currency)}",
        f"💸 支出：{format_amount(expense, currency)}",
        f"📈 结余：{format_amount(balance, currency)}",
    ]

    if balance < 0:
        lines.append("\n⚠️ 注意：支出大于收入！")

    return "\n".join(lines)
