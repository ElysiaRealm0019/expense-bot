"""
数据模型模块

定义所有核心数据结构：
- TransactionType - 交易类型枚举
- Category - 分类模型
- Transaction - 交易记录模型
- DailySummary - 每日汇总
- CategoryStat - 分类统计
- TrendData - 趋势数据
- Tag - 标签模型
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Optional, List


class TransactionType(Enum):
    """交易类型枚举"""
    INCOME = "income"
    EXPENSE = "expense"


@dataclass
class Category:
    """分类模型"""
    id: int
    name: str
    type: TransactionType
    emoji: str = "📦"
    parent_id: Optional[int] = None


@dataclass
class Transaction:
    """交易记录模型"""
    id: int
    amount: float
    type: TransactionType
    category_id: int
    category_name: str  # 反范式化存储，方便显示
    description: str = ""
    date: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)
    tags: List[Tag] = field(default_factory=list)


@dataclass
class DailySummary:
    """每日/周/月汇总模型"""
    date: str  # 格式: YYYY-MM-DD 或 YYYY-MM
    income: float
    expense: float
    balance: float


@dataclass
class CategoryStat:
    """分类统计数据模型"""
    category_id: int
    category_name: str
    emoji: str
    total: float
    count: int
    percentage: float


@dataclass
class TrendData:
    """趋势数据模型"""
    period: str  # 日期或月份
    income: float
    expense: float
    balance: float


@dataclass
class Tag:
    """标签模型"""
    id: int
    name: str
