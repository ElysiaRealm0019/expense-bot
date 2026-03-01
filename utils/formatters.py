"""Utility functions for formatting."""

from datetime import datetime
from typing import Optional


def format_amount(amount: float, currency: str = "£") -> str:
    """Format amount with currency symbol"""
    return f"{currency}{amount:.2f}"


def format_date(date: datetime, format_str: str = "%Y-%m-%d %H:%M") -> str:
    """Format date for display"""
    return date.strftime(format_str)


def format_expense_list(expenses: list, currency: str = "£") -> str:
    """Format a list of expenses for display"""
    if not expenses:
        return "No expenses to display."
    
    lines = []
    for exp in expenses:
        date_str = format_date(exp.created_at, "%m/%d")
        line = f"{date_str} - {format_amount(exp.amount, currency)} - {exp.category}"
        if exp.description:
            line += f" ({exp.description})"
        lines.append(line)
    
    return "\n".join(lines)


def validate_amount(amount_str: str) -> Optional[float]:
    """Validate and parse amount string"""
    try:
        amount = float(amount_str)
        if amount <= 0:
            return None
        return round(amount, 2)
    except (ValueError, TypeError):
        return None


def validate_category(category: str) -> bool:
    """Validate category name"""
    if not category:
        return False
    # Allow alphanumeric, spaces, and common punctuation
    return len(category) <= 50 and category.replace(" ", "").isalnum()
