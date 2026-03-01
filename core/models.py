"""Data models for the expense core domain."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from typing import Optional, List


class TransactionType(Enum):
    INCOME = "income"
    EXPENSE = "expense"


@dataclass
class Tag:
    """标签"""
    id: int
    name: str


@dataclass
class Category:
    """分类"""
    id: int
    name: str
    type: TransactionType
    emoji: str = "📦"


@dataclass
class Transaction:
    """交易记录"""
    id: int
    amount: float
    category_id: int
    category_name: str  # Denormalized for convenience
    type: TransactionType
    description: Optional[str]
    date: datetime
    created_at: datetime
    user_id: int = 0  # Optional user association
    tags: List[Tag] = None  # Associated tags
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class DailySummary:
    """每日汇总"""
    date: str
    income: float
    expense: float
    balance: float


@dataclass
class CategoryStat:
    """分类统计"""
    category_id: int
    category_name: str
    emoji: str
    total: float
    count: int
    percentage: float


@dataclass
class TrendData:
    """趋势数据"""
    period: str
    income: float
    expense: float
    balance: float
