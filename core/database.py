"""
Database module for expense tracking.

Handles all SQLite operations for storing and retrieving expenses.
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict
from .models import Transaction, TransactionType, Tag


class Database:
    """
    SQLite database handler for expense tracking.
    
    Provides methods to add, retrieve, and summarize expenses.
    """
    
    def __init__(self, db_path: str):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_directory()
        self._init_db()
    
    def _ensure_directory(self):
        """Create database directory if it doesn't exist."""
        directory = os.path.dirname(self.db_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """Create tables if they don't exist."""
        with self._get_connection() as conn:
            # Categories table
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
            
            # Tags table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL
                )
            """)
            
            # Transactions table
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
            
            # Transaction-Tags linking table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transaction_tags (
                    transaction_id INTEGER NOT NULL,
                    tag_id INTEGER NOT NULL,
                    PRIMARY KEY (transaction_id, tag_id),
                    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes
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
            
            # Initialize default categories if empty
            cursor = conn.execute("SELECT COUNT(*) as count FROM categories")
            if cursor.fetchone()["count"] == 0:
                self._insert_default_categories(conn)
    
    def _insert_default_categories(self, conn):
        """Insert default categories."""
        default_categories = [
            # Expense categories
            ("餐饮", "expense", "🍔"),
            ("交通", "expense", "🚗"),
            ("购物", "expense", "🛍️"),
            ("娱乐", "expense", "🎮"),
            ("居住", "expense", "🏠"),
            ("医疗", "expense", "💊"),
            ("教育", "expense", "📚"),
            ("其他支出", "expense", "📦"),
            # Income categories
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

    # ========== Category Operations ==========
    
    def get_categories(self, type_: Optional[TransactionType] = None) -> List[dict]:
        """Get list of categories."""
        with self._get_connection() as conn:
            query = "SELECT id, name, type, emoji, parent_id FROM categories"
            params = []
            if type_:
                query += " WHERE type = ?"
                params.append(type_.value)
            
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_category_by_name(self, name: str, type_: TransactionType) -> Optional[dict]:
        """Get category by name."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM categories WHERE name = ? AND type = ?",
                (name, type_.value)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    # ========== Tag Operations ==========
    
    def add_tag(self, name: str) -> int:
        """Add a tag if not exists."""
        with self._get_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (name,))
            cursor = conn.execute("SELECT id FROM tags WHERE name = ?", (name,))
            return cursor.fetchone()["id"]

    # ========== Transaction Operations ==========
    
    def add_transaction(
        self,
        amount: float,
        type_: TransactionType,
        category_id: int,
        description: str = "",
        date: Optional[datetime] = None,
        tags: Optional[List[str]] = None
    ) -> int:
        """Add a transaction record."""
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
        """Retrieve transactions with filters."""
        with self._get_connection() as conn:
            query = """
                SELECT t.id, t.amount, t.type, t.category_id, c.name as category_name,
                       c.emoji as category_emoji, t.description, t.date
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
                # Get tags for this transaction
                tag_cursor = conn.execute(
                    """SELECT tg.id, tg.name FROM tags tg
                       JOIN transaction_tags tt ON tg.id = tt.tag_id
                       WHERE tt.transaction_id = ?""",
                    (row["id"],)
                )
                tags = [Tag(id=t["id"], name=t["name"]) for t in tag_cursor.fetchall()]
                
                # Parse date handling potential string from SQLite
                date_val = row["date"]
                if isinstance(date_val, str):
                    try:
                        date_val = datetime.fromisoformat(date_val)
                    except ValueError:
                        # Fallback for simple date strings
                        date_val = datetime.strptime(date_val.split('.')[0], "%Y-%m-%d %H:%M:%S")

                transactions.append(Transaction(
                    id=row["id"],
                    amount=row["amount"],
                    type=TransactionType(row["type"]),
                    category_id=row["category_id"],
                    category_name=f"{row['category_emoji']} {row['category_name']}",
                    description=row["description"] or "",
                    date=date_val,
                    tags=tags
                ))
            
            return transactions
