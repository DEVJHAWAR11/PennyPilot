"""
Database schema and initialization for PostgreSQL via asyncpg.

Creates tables and seeds default categories for new users.
"""

import os
import asyncpg
from typing import Optional

# Global connection pool
pool: Optional[asyncpg.Pool] = None

# Default categories seeded for every new user on first /start
DEFAULT_CATEGORIES = [
    ("Food & Dining", "expense", "🍔"),
    ("Groceries", "expense", "🛒"),
    ("Travel", "expense", "🚕"),
    ("Entertainment", "expense", "🎬"),
    ("Subscriptions", "expense", "🔁"),
    ("EMI", "expense", "🏦"),
    ("Bills & Subs", "expense", "🧾"),
    ("Transport", "expense", "🚌"),
    ("Salary", "income", "💰"),
    ("Other Income", "income", "📥"),
    ("Other Expenses", "expense", "📦"),
]

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    telegram_id     BIGINT UNIQUE NOT NULL,
    month_start_day INTEGER NOT NULL DEFAULT 1,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    name        TEXT    NOT NULL,
    type        TEXT    NOT NULL CHECK (type IN ('income', 'expense')),
    emoji       TEXT    DEFAULT '',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS keywords (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    keyword     TEXT    NOT NULL,
    category_id INTEGER NOT NULL,
    FOREIGN KEY (user_id)     REFERENCES users(id)      ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS transactions (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    amount      REAL    NOT NULL,
    type        TEXT    NOT NULL CHECK (type IN ('income', 'expense')),
    category_id INTEGER NOT NULL,
    note        TEXT    DEFAULT '',
    date        DATE    NOT NULL,
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)     REFERENCES users(id)      ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
);
"""

async def get_pool() -> asyncpg.Pool:
    global pool
    if pool is None:
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            raise ValueError("DATABASE_URL not set in environment")
        pool = await asyncpg.create_pool(db_url, min_size=1, max_size=5)
    return pool

async def init_db() -> None:
    """Create all tables if they don't exist yet."""
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute(CREATE_TABLES_SQL)

async def seed_categories_for_user(user_db_id: int) -> None:
    """Insert the default categories for a newly registered user."""
    p = await get_pool()
    async with p.acquire() as conn:
        # Use executemany for bulk insert
        values = [(user_db_id, name, cat_type, emoji) for name, cat_type, emoji in DEFAULT_CATEGORIES]
        await conn.executemany(
            "INSERT INTO categories (user_id, name, type, emoji) VALUES ($1, $2, $3, $4)",
            values
        )
