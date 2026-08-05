"""
Database schema and initialization.

Creates tables and seeds default categories for new users.
"""

import aiosqlite

# Default categories seeded for every new user on first /start
DEFAULT_CATEGORIES = [
    ("Groceries", "expense", "🛒"),
    ("Bills & Subs", "expense", "🧾"),
    ("Transport", "expense", "🚌"),
    ("Salary", "income", "💰"),
    ("Other Income", "income", "📥"),
    ("Other Expenses", "expense", "📦"),
]

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id     INTEGER UNIQUE NOT NULL,
    month_start_day INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    name        TEXT    NOT NULL,
    type        TEXT    NOT NULL CHECK (type IN ('income', 'expense')),
    emoji       TEXT    DEFAULT '',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS keywords (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    keyword     TEXT    NOT NULL,
    category_id INTEGER NOT NULL,
    FOREIGN KEY (user_id)     REFERENCES users(id)      ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    amount      REAL    NOT NULL,
    type        TEXT    NOT NULL CHECK (type IN ('income', 'expense')),
    category_id INTEGER NOT NULL,
    note        TEXT    DEFAULT '',
    date        TEXT    NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id)     REFERENCES users(id)      ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
);
"""

# Path to the SQLite database file
DB_PATH = "data/expenses.db"


async def init_db() -> None:
    """Create all tables if they don't exist yet."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(CREATE_TABLES_SQL)
        await db.commit()


async def seed_categories_for_user(user_db_id: int) -> None:
    """Insert the default categories for a newly registered user."""
    async with aiosqlite.connect(DB_PATH) as db:
        for name, cat_type, emoji in DEFAULT_CATEGORIES:
            await db.execute(
                "INSERT INTO categories (user_id, name, type, emoji) VALUES (?, ?, ?, ?)",
                (user_db_id, name, cat_type, emoji),
            )
        await db.commit()
