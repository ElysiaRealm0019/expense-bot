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
class Category:
    id: int
    name: str
    type: TransactionType
    emoji: str = "📦"


@dataclass
class Transaction:
    id: int
    user_id: int
    amount: float
    category_id: int
    category_name: str  # Denormalized for convenience
    type: TransactionType
    description: Optional[str]
    date: datetime
    created_at: datetime
    tags: List["Tag"] = None  # Associated tags
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class DailySummary:
    date: str
    income: float
    expense: float
    balance: float


@dataclass
class CategoryStat:
    category_id: int
    category_name: str
    emoji: str
    total: float
    count: int
    percentage: float


@dataclass
class TrendData:
    period: str
    income: float
    expense: float
    balance: float

# Placeholder classes to satisfy imports if needed elsewhere
@dataclass
class Tag:
    id: int
    name: str

