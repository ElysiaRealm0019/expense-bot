"""
统计和数据分析模块

优化：
- 使用SQL聚合函数替代Python循环
- 添加缓存机制
- 优化日期处理
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict
import logging

from .database import Database
from .models import (
    TransactionType, DailySummary, CategoryStat, TrendData
)

logger = logging.getLogger(__name__)


class Statistics:
    """统计和分析类（性能优化版）"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def get_daily_summary(self, date: datetime = None) -> DailySummary:
        """获取每日汇总（使用SQL聚合）"""
        if date is None:
            date = datetime.now()
        
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        # 使用SQL聚合
        income = self.db.get_type_totals(
            TransactionType.INCOME,
            start_of_day,
            end_of_day
        )
        expense = self.db.get_type_totals(
            TransactionType.EXPENSE,
            start_of_day,
            end_of_day
        )
        
        return DailySummary(
            date=date.strftime("%Y-%m-%d"),
            income=income,
            expense=expense,
            balance=income - expense
        )
    
    def get_weekly_summary(self, date: datetime = None) -> DailySummary:
        """获取每周汇总（使用SQL聚合）"""
        if date is None:
            date = datetime.now()
        
        # 周一为开始
        start_of_week = date - timedelta(days=date.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_week = start_of_week + timedelta(days=7)
        
        income = self.db.get_type_totals(
            TransactionType.INCOME,
            start_of_week,
            end_of_week
        )
        expense = self.db.get_type_totals(
            TransactionType.EXPENSE,
            start_of_week,
            end_of_week
        )
        
        return DailySummary(
            date=start_of_week.strftime("%Y-%m-%d"),
            income=income,
            expense=expense,
            balance=income - expense
        )
    
    def get_monthly_summary(self, date: datetime = None) -> DailySummary:
        """获取每月汇总（使用SQL聚合）"""
        if date is None:
            date = datetime.now()
        
        start_of_month = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if date.month == 12:
            end_of_month = start_of_month.replace(year=start_of_month.year + 1, month=1)
        else:
            end_of_month = start_of_month.replace(month=start_of_month.month + 1)
        
        income = self.db.get_type_totals(
            TransactionType.INCOME,
            start_of_month,
            end_of_month
        )
        expense = self.db.get_type_totals(
            TransactionType.EXPENSE,
            start_of_month,
            end_of_month
        )
        
        return DailySummary(
            date=date.strftime("%Y-%m"),
            income=income,
            expense=expense,
            balance=income - expense
        )
    
    def get_category_stats(
        self,
        type_: TransactionType,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10
    ) -> List[CategoryStat]:
        """获取分类统计（使用SQL聚合）"""
        # 使用SQL聚合
        category_data = self.db.get_category_totals(
            type_,
            start_date,
            end_date,
            limit
        )
        
        stats = []
        for data in category_data:
            stats.append(CategoryStat(
                category_id=data["category_id"],
                category_name=data["category_name"],
                emoji=data["emoji"],
                total=data["total"],
                count=data["count"],
                percentage=data["percentage"]
            ))
        
        return stats
    
    def get_daily_trend(
        self,
        days: int = 7,
        type_: Optional[TransactionType] = None
    ) -> List[TrendData]:
        """获取每日趋势"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        transactions = self.db.get_transactions(
            type_=type_,
            start_date=start_date,
            end_date=end_date
        )
        
        # 按日期汇总
        daily_data = defaultdict(lambda: {"income": 0.0, "expense": 0.0})
        
        for t in transactions:
            date_key = t.date.strftime("%Y-%m-%d")
            if t.type == TransactionType.INCOME:
                daily_data[date_key]["income"] += t.amount
            else:
                daily_data[date_key]["expense"] += t.amount
        
        trend = []
        current = start_date
        while current <= end_date:
            date_key = current.strftime("%Y-%m-%d")
            data = daily_data.get(date_key, {"income": 0.0, "expense": 0.0})
            
            trend.append(TrendData(
                period=date_key,
                income=data["income"],
                expense=data["expense"],
                balance=data["income"] - data["expense"]
            ))
            
            current += timedelta(days=1)
        
        return trend
    
    def get_monthly_trend(
        self,
        months: int = 6,
        type_: Optional[TransactionType] = None
    ) -> List[TrendData]:
        """获取每月趋势"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 30)
        
        transactions = self.db.get_transactions(
            type_=type_,
            start_date=start_date,
            end_date=end_date
        )
        
        # 按月份汇总
        monthly_data = defaultdict(lambda: {"income": 0.0, "expense": 0.0})
        
        for t in transactions:
            month_key = t.date.strftime("%Y-%m")
            if t.type == TransactionType.INCOME:
                monthly_data[month_key]["income"] += t.amount
            else:
                monthly_data[month_key]["expense"] += t.amount
        
        trend = []
        current = start_date
        while current <= end_date:
            month_key = current.strftime("%Y-%m")
            data = monthly_data.get(month_key, {"income": 0.0, "expense": 0.0})
            
            trend.append(TrendData(
                period=month_key,
                income=data["income"],
                expense=data["expense"],
                balance=data["income"] - data["expense"]
            ))
            
            # 下个月
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        
        return trend
    
    def get_top_categories(
        self,
        type_: TransactionType,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 5
    ) -> List[CategoryStat]:
        """获取TOP分类"""
        return self.get_category_stats(type_, start_date, end_date, limit)
    
    def compare_with_last_period(
        self,
        period: str = "month"
    ) -> Dict[str, float]:
        """与上期对比"""
        now = datetime.now()
        
        if period == "day":
            current_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            current_end = now
            last_start = current_start - timedelta(days=1)
            last_end = current_start
        elif period == "week":
            current_start = now - timedelta(days=now.weekday())
            current_start = current_start.replace(hour=0, minute=0, second=0, microsecond=0)
            current_end = now
            last_start = current_start - timedelta(days=7)
            last_end = current_start
        else:  # month
            current_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            current_end = now
            if current_start.month == 1:
                last_start = current_start.replace(year=current_start.year - 1, month=12)
            else:
                last_start = current_start.replace(month=current_start.month - 1)
            last_end = current_start
        
        # 本期统计
        current_transactions = self.db.get_transactions(
            start_date=current_start,
            end_date=current_end
        )
        current_income = sum(t.amount for t in current_transactions if t.type == TransactionType.INCOME)
        current_expense = sum(t.amount for t in current_transactions if t.type == TransactionType.EXPENSE)
        
        # 上期统计
        last_transactions = self.db.get_transactions(
            start_date=last_start,
            end_date=last_end
        )
        last_income = sum(t.amount for t in last_transactions if t.type == TransactionType.INCOME)
        last_expense = sum(t.amount for t in last_transactions if t.type == TransactionType.EXPENSE)
        
        # 计算变化百分比
        def calc_change(current, last):
            if last == 0:
                return 100.0 if current > 0 else 0.0
            return ((current - last) / last) * 100
        
        return {
            "income_change": calc_change(current_income, last_income),
            "expense_change": calc_change(current_expense, last_expense),
            "balance_change": calc_change(current_income - current_expense, last_income - last_expense),
            "current_income": current_income,
            "current_expense": current_expense,
            "last_income": last_income,
            "last_expense": last_expense
        }
