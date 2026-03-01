"""
数据库模块

处理所有 SQLite 数据库操作，包括：
- 数据库初始化和连接管理
- 分类管理 (CRUD)
- 交易记录管理 (CRUD)
- 标签管理

优化：
- 连接复用，减少开销
- 添加缓存层
- 完善错误处理
"""

import sqlite3
import os
import logging
import threading
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from .models import Transaction, TransactionType, Tag, Category

logger = logging.getLogger(__name__)


class Database:
    """
    SQLite 数据库处理器

    提供所有数据持久化操作，包括：
    - 分类的增删改查
    - 交易记录的增删改查
    - 标签管理

    优化：
    - 连接池和线程本地存储
    - 分类缓存
    - 异常处理
    """

    def __init__(self, db_path: str):
        """
        初始化数据库连接

        Args:
            db_path: SQLite 数据库文件路径
        """
        self.db_path = db_path
        self._local = threading.local()
        self._category_cache: Dict[str, Any] = {}
        self._cache_lock = threading.Lock()
        self._ensure_directory()
        self._init_db()

    def _ensure_directory(self):
        """确保数据库目录存在"""
        directory = os.path.dirname(self.db_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    @property
    def _connection(self) -> sqlite3.Connection:
        """获取线程本地的数据库连接"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
            # 启用外键约束
            self._local.conn.execute("PRAGMA foreign_keys = ON")
            logger.debug(f"Created new database connection for thread")
        return self._local.conn

    @contextmanager
    def _get_connection(self):
        """获取数据库连接的上下文管理器（兼容旧接口）"""
        conn = self._connection
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise

    def close(self):
        """关闭数据库连接"""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
            logger.debug("Database connection closed")

    def _invalidate_category_cache(self):
        """清除分类缓存"""
        with self._cache_lock:
            self._category_cache.clear()
            logger.debug("Category cache invalidated")

    def _get_categories_cached(self, type_: Optional[TransactionType] = None) -> List[dict]:
        """获取分类（带缓存）"""
        cache_key = f"categories_{type_.value if type_ else 'all'}"
        
        with self._cache_lock:
            if cache_key in self._category_cache:
                return self._category_cache[cache_key]
        
        # 从数据库获取
        categories = self._get_categories_from_db(type_)
        
        with self._cache_lock:
            self._category_cache[cache_key] = categories
        
        return categories

    def _get_categories_from_db(self, type_: Optional[TransactionType] = None) -> List[dict]:
        """从数据库获取分类"""
        with self._get_connection() as conn:
            try:
                query = "SELECT id, name, type, emoji, parent_id FROM categories"
                params = []
                if type_:
                    query += " WHERE type = ?"
                    params.append(type_.value)

                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
            except sqlite3.Error as e:
                logger.error(f"Failed to get categories: {e}")
                return []

    def _init_db(self):
        """初始化数据库表结构"""
        try:
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
                    
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

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

    def get_categories(self, type_: Optional[TransactionType] = None, use_cache: bool = True) -> List[dict]:
        """
        获取分类列表

        Args:
            type_: 可选的分类类型过滤
            use_cache: 是否使用缓存

        Returns:
            分类字典列表
        """
        if use_cache:
            return self._get_categories_cached(type_)
        return self._get_categories_from_db(type_)

    def get_category_by_name(self, name: str, type_: TransactionType) -> Optional[dict]:
        """根据名称获取分类"""
        with self._get_connection() as conn:
            try:
                cursor = conn.execute(
                    "SELECT * FROM categories WHERE name = ? AND type = ?",
                    (name, type_.value)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
            except sqlite3.Error as e:
                logger.error(f"Failed to get category by name: {e}")
                return None

    def get_category_by_id(self, category_id: int) -> Optional[dict]:
        """根据ID获取分类"""
        with self._get_connection() as conn:
            try:
                cursor = conn.execute(
                    "SELECT * FROM categories WHERE id = ?",
                    (category_id,)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
            except sqlite3.Error as e:
                logger.error(f"Failed to get category by id: {e}")
                return None

    def get_category_name(self, category_id: int) -> str:
        """根据ID获取分类名称"""
        category = self.get_category_by_id(category_id)
        return category["name"] if category else "未知分类"

    # ========== 标签操作 ==========

    def add_tag(self, name: str) -> int:
        """添加标签（如果不存在）"""
        with self._get_connection() as conn:
            try:
                conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (name,))
                cursor = conn.execute("SELECT id FROM tags WHERE name = ?", (name,))
                result = cursor.fetchone()
                return result["id"] if result else -1
            except sqlite3.Error as e:
                logger.error(f"Failed to add tag: {e}")
                return -1

    def get_transaction_tags(self, transaction_id: int) -> List[Tag]:
        """获取交易的标签列表"""
        with self._get_connection() as conn:
            try:
                cursor = conn.execute(
                    """SELECT tg.id, tg.name FROM tags tg
                       JOIN transaction_tags tt ON tg.id = tt.tag_id
                       WHERE tt.transaction_id = ?""",
                    (transaction_id,)
                )
                return [Tag(id=row["id"], name=row["name"]) for row in cursor.fetchall()]
            except sqlite3.Error as e:
                logger.error(f"Failed to get transaction tags: {e}")
                return []

    def get_transaction_tags_batch(self, transaction_ids: List[int]) -> Dict[int, List[Tag]]:
        """批量获取交易的标签（避免N+1查询）"""
        if not transaction_ids:
            return {}
        
        with self._get_connection() as conn:
            try:
                placeholders = ','.join('?' * len(transaction_ids))
                query = f"""
                    SELECT tt.transaction_id, tg.id, tg.name 
                    FROM transaction_tags tt
                    JOIN tags tg ON tt.tag_id = tg.id
                    WHERE tt.transaction_id IN ({placeholders})
                """
                cursor = conn.execute(query, transaction_ids)
                
                result: Dict[int, List[Tag]] = {}
                for row in cursor.fetchall():
                    tid = row["transaction_id"]
                    if tid not in result:
                        result[tid] = []
                    result[tid].append(Tag(id=row["id"], name=row["name"]))
                return result
            except sqlite3.Error as e:
                logger.error(f"Failed to get transaction tags batch: {e}")
                return {}

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
        """添加交易记录"""
        if date is None:
            date = datetime.now()

        try:
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
                        if tag_id > 0:
                            conn.execute(
                                "INSERT OR IGNORE INTO transaction_tags (transaction_id, tag_id) VALUES (?, ?)",
                                (transaction_id, tag_id)
                            )
                conn.commit()
                
                # 清除分类缓存
                self._invalidate_category_cache()
                
                logger.info(f"Transaction added: {transaction_id}")
                return transaction_id
        except Exception as e:
            logger.error(f"Failed to add transaction: {e}")
            return -1

    def get_transactions(
        self,
        type_: Optional[TransactionType] = None,
        category_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        include_tags: bool = True
    ) -> List[Transaction]:
        """获取交易记录列表"""
        try:
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
                rows = cursor.fetchall()

                # 批量获取标签（优化N+1问题）
                transaction_ids = [row["id"] for row in rows]
                tags_map = self.get_transaction_tags_batch(transaction_ids) if include_tags and transaction_ids else {}

                transactions = []
                for row in rows:
                    # 解析日期
                    date_val = self._parse_date(row["date"])
                    created_at = self._parse_date(row["created_at"])

                    # 使用批量获取的标签
                    tags = tags_map.get(row["id"], [])

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
        except Exception as e:
            logger.error(f"Failed to get transactions: {e}")
            return []

    def _parse_date(self, date_val: Any) -> datetime:
        """安全解析日期"""
        if isinstance(date_val, datetime):
            return date_val
        if isinstance(date_val, str):
            try:
                return datetime.fromisoformat(date_val)
            except ValueError:
                try:
                    return datetime.strptime(date_val.split('.')[0], "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    return datetime.now()
        return datetime.now()

    def delete_transaction(self, transaction_id: int) -> bool:
        """删除交易记录"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM transactions WHERE id = ?",
                    (transaction_id,)
                )
                conn.commit()
                self._invalidate_category_cache()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to delete transaction: {e}")
            return False

    # ========== 统计优化方法 ==========

    def get_type_totals(
        self,
        type_: TransactionType,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> float:
        """获取指定类型的总金额（SQL聚合，性能优化）"""
        try:
            with self._get_connection() as conn:
                query = "SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE type = ?"
                params = [type_.value]

                if start_date:
                    query += " AND date >= ?"
                    params.append(start_date)
                if end_date:
                    query += " AND date < ?"
                    params.append(end_date)

                cursor = conn.execute(query, params)
                result = cursor.fetchone()
                return float(result["total"]) if result else 0.0
        except Exception as e:
            logger.error(f"Failed to get type totals: {e}")
            return 0.0

    def get_category_totals(
        self,
        type_: TransactionType,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10
    ) -> List[Dict]:
        """获取分类统计数据（SQL聚合，性能优化）"""
        try:
            with self._get_connection() as conn:
                query = """
                    SELECT 
                        t.category_id,
                        c.name as category_name,
                        c.emoji,
                        SUM(t.amount) as total,
                        COUNT(t.id) as count
                    FROM transactions t
                    JOIN categories c ON t.category_id = c.id
                    WHERE t.type = ?
                """
                params = [type_.value]

                if start_date:
                    query += " AND t.date >= ?"
                    params.append(start_date)
                if end_date:
                    query += " AND t.date < ?"
                    params.append(end_date)

                query += " GROUP BY t.category_id ORDER BY total DESC LIMIT ?"
                params.append(limit)

                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

                # 计算百分比
                total_amount = sum(float(row["total"]) for row in rows)
                result = []
                for row in rows:
                    percentage = (float(row["total"]) / total_amount * 100) if total_amount > 0 else 0
                    result.append({
                        "category_id": row["category_id"],
                        "category_name": row["category_name"],
                        "emoji": row["emoji"],
                        "total": float(row["total"]),
                        "count": row["count"],
                        "percentage": percentage
                    })

                return result
        except Exception as e:
            logger.error(f"Failed to get category totals: {e}")
            return []

    # ========== 聚合查询（性能优化）==========
    
    def get_type_totals(
        self,
        type_: TransactionType,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> float:
        """获取指定类型的总金额（使用SQL SUM）"""
        try:
            with self._get_connection() as conn:
                query = "SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE type = ?"
                params = [type_.value]
                
                if start_date:
                    query += " AND date >= ?"
                    params.append(start_date)
                if end_date:
                    query += " AND date <= ?"
                    params.append(end_date)
                
                cursor = conn.execute(query, params)
                return cursor.fetchone()["total"]
        except Exception as e:
            logger.error(f"Failed to get type totals: {e}")
            return 0.0

    def get_category_totals(
        self,
        type_: TransactionType,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """获取分类统计（使用SQL聚合）"""
        try:
            with self._get_connection() as conn:
                query = """
                    SELECT 
                        t.category_id,
                        c.name as category_name,
                        c.emoji,
                        SUM(t.amount) as total,
                        COUNT(t.id) as count
                    FROM transactions t
                    JOIN categories c ON t.category_id = c.id
                    WHERE t.type = ?
                """
                params = [type_.value]
                
                if start_date:
                    query += " AND t.date >= ?"
                    params.append(start_date)
                if end_date:
                    query += " AND t.date <= ?"
                    params.append(end_date)
                
                query += " GROUP BY t.category_id ORDER BY total DESC LIMIT ?"
                params.append(limit)
                
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                # 计算总额用于百分比
                total_sum = sum(row["total"] for row in rows)
                
                result = []
                for row in rows:
                    percentage = (row["total"] / total_sum * 100) if total_sum > 0 else 0
                    result.append({
                        "category_id": row["category_id"],
                        "category_name": row["category_name"],
                        "emoji": row["emoji"],
                        "total": row["total"],
                        "count": row["count"],
                        "percentage": percentage
                    })
                
                return result
        except Exception as e:
            logger.error(f"Failed to get category totals: {e}")
            return []
