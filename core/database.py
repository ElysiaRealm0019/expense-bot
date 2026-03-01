"""
数据库模块

处理所有 SQLite 数据库操作，包括：
- 数据库初始化和连接管理
- 分类管理 (CRUD)
- 交易记录管理 (CRUD)
- 标签管理
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, List
from contextlib import contextmanager

from .models import Transaction, TransactionType, Tag, Category


class Database:
    """
    SQLite 数据库处理器

    提供所有数据持久化操作，包括：
    - 分类的增删改查
    - 交易记录的增删改查
    - 标签管理
    """

    def __init__(self, db_path: str):
        """
        初始化数据库连接

        Args:
            db_path: SQLite 数据库文件路径
        """
        self.db_path = db_path
        self._ensure_directory()
        self._init_db()

    def _ensure_directory(self):
        """确保数据库目录存在"""
        directory = os.path.dirname(self.db_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    @contextmanager
    def _get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        """初始化数据库表结构"""
        with self._get_connection() as conn:
            # 分类表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    emoji TEXT DEFAULT '💰',
                    parent_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (parent_id) REFERENCES categories(id)
                )
            """)

            # 标签表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL
                )
            """)

            # 交易记录表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    amount REAL NOT NULL,
                    type TEXT NOT NULL,
                    category_id INTEGER NOT NULL,
                    description TEXT,
                    date TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES categories(id)
                )
            """)

            # 交易-标签关联表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transaction_tags (
                    transaction_id INTEGER NOT NULL,
                    tag_id INTEGER NOT NULL,
                    PRIMARY KEY (transaction_id, tag_id),
                    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
                )
            """)

            # 创建索引
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_transactions_date
                ON transactions(date)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_transactions_type
                ON transactions(type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_transactions_category
                ON transactions(category_id)
            """)

            conn.commit()

            # 初始化默认分类
            cursor = conn.execute("SELECT COUNT(*) as count FROM categories")
            if cursor.fetchone()["count"] == 0:
                self._insert_default_categories(conn)

    def _insert_default_categories(self, conn: sqlite3.Connection):
        """插入默认分类"""
        default_categories = [
            # 支出分类
            ("餐饮", "expense", "🍔"),
            ("交通", "expense", "🚗"),
            ("购物", "expense", "🛍️"),
            ("娱乐", "expense", "🎮"),
            ("居住", "expense", "🏠"),
            ("医疗", "expense", "💊"),
            ("教育", "expense", "📚"),
            ("其他支出", "expense", "📦"),
            # 收入分类
            ("工资", "income", "💵"),
            ("奖金", "income", "🎁"),
            ("投资", "income", "📈"),
            ("其他收入", "income", "💰"),
        ]

        for name, type_, emoji in default_categories:
            conn.execute(
                "INSERT INTO categories (name, type, emoji) VALUES (?, ?, ?)",
                (name, type_, emoji)
            )
        conn.commit()

    # ========== 分类操作 ==========

    def get_categories(self, type_: Optional[TransactionType] = None) -> List[dict]:
        """
        获取分类列表

        Args:
            type_: 可选的分类类型过滤

        Returns:
            分类字典列表
        """
        with self._get_connection() as conn:
            query = "SELECT id, name, type, emoji, parent_id FROM categories"
            params = []
            if type_:
                query += " WHERE type = ?"
                params.append(type_.value)

            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_category_by_name(self, name: str, type_: TransactionType) -> Optional[dict]:
        """
        根据名称获取分类

        Args:
            name: 分类名称
            type_: 分类类型

        Returns:
            分类字典，不存在则返回 None
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM categories WHERE name = ? AND type = ?",
                (name, type_.value)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_category_by_id(self, category_id: int) -> Optional[dict]:
        """根据ID获取分类"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM categories WHERE id = ?",
                (category_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_category_name(self, category_id: int) -> str:
        """根据ID获取分类名称"""
        category = self.get_category_by_id(category_id)
        return category["name"] if category else "未知分类"

    # ========== 标签操作 ==========

    def add_tag(self, name: str) -> int:
        """
        添加标签（如果不存在）

        Args:
            name: 标签名称

        Returns:
            标签 ID
        """
        with self._get_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (name,))
            cursor = conn.execute("SELECT id FROM tags WHERE name = ?", (name,))
            return cursor.fetchone()["id"]

    def get_transaction_tags(self, transaction_id: int) -> List[Tag]:
        """获取交易的标签列表"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """SELECT tg.id, tg.name FROM tags tg
                   JOIN transaction_tags tt ON tg.id = tt.tag_id
                   WHERE tt.transaction_id = ?""",
                (transaction_id,)
            )
            return [Tag(id=row["id"], name=row["name"]) for row in cursor.fetchall()]

    # ========== 交易操作 ==========

    def add_transaction(
        self,
        amount: float,
        type_: TransactionType,
        category_id: int,
        description: str = "",
        date: Optional[datetime] = None,
        tags: Optional[List[str]] = None
    ) -> int:
        """
        添加交易记录

        Args:
            amount: 金额
            type_: 交易类型
            category_id: 分类 ID
            description: 描述（可选）
            date: 交易日期（可选，默认当前时间）
            tags: 标签列表（可选）

        Returns:
            新创建的交易记录 ID
        """
        if date is None:
            date = datetime.now()

        with self._get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO transactions (amount, type, category_id, description, date)
                   VALUES (?, ?, ?, ?, ?)""",
                (amount, type_.value, category_id, description, date)
            )
            transaction_id = cursor.lastrowid

            if tags:
                for tag_name in tags:
                    tag_id = self.add_tag(tag_name)
                    conn.execute(
                        "INSERT OR IGNORE INTO transaction_tags (transaction_id, tag_id) VALUES (?, ?)",
                        (transaction_id, tag_id)
                    )
            conn.commit()
            return transaction_id

    def get_transactions(
        self,
        type_: Optional[TransactionType] = None,
        category_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Transaction]:
        """
        获取交易记录列表

        Args:
            type_: 交易类型过滤
            category_id: 分类 ID 过滤
            start_date: 开始日期
            end_date: 结束日期
            limit: 返回数量限制

        Returns:
            Transaction 对象列表
        """
        with self._get_connection() as conn:
            query = """
                SELECT t.id, t.amount, t.type, t.category_id, c.name as category_name,
                       c.emoji as category_emoji, t.description, t.date, t.created_at
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                WHERE 1=1
            """
            params = []

            if type_:
                query += " AND t.type = ?"
                params.append(type_.value)
            if category_id:
                query += " AND t.category_id = ?"
                params.append(category_id)
            if start_date:
                query += " AND t.date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND t.date <= ?"
                params.append(end_date)

            query += " ORDER BY t.date DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(query, params)

            transactions = []
            for row in cursor.fetchall():
                # 解析日期
                date_val = row["date"]
                if isinstance(date_val, str):
                    try:
                        date_val = datetime.fromisoformat(date_val)
                    except ValueError:
                        date_val = datetime.strptime(date_val.split('.')[0], "%Y-%m-%d %H:%M:%S")

                created_at = row["created_at"]
                if isinstance(created_at, str):
                    try:
                        created_at = datetime.fromisoformat(created_at)
                    except ValueError:
                        created_at = datetime.strptime(created_at.split('.')[0], "%Y-%m-%d %H:%M:%S")

                # 获取标签
                tags = self.get_transaction_tags(row["id"])

                transactions.append(Transaction(
                    id=row["id"],
                    amount=row["amount"],
                    type=TransactionType(row["type"]),
                    category_id=row["category_id"],
                    category_name=f"{row['category_emoji']} {row['category_name']}",
                    description=row["description"] or "",
                    date=date_val,
                    created_at=created_at,
                    tags=tags
                ))

            return transactions

    def delete_transaction(self, transaction_id: int) -> bool:
        """删除交易记录"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM transactions WHERE id = ?",
                (transaction_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
