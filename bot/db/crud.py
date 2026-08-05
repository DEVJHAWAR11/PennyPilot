"""
Async CRUD functions for the database.

One function per operation — no raw SQL in handlers.
"""

from typing import Optional

import aiosqlite

from bot.db.schema import DB_PATH, seed_categories_for_user


# ──────────────────────────── Users ────────────────────────────

async def get_or_create_user(telegram_id: int) -> dict:
    """
    Return the user row for this telegram_id.
    If the user doesn't exist yet, create them and seed default categories.
    Returns a dict with keys: id, telegram_id, month_start_day, created_at.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Check if user already exists
        async with db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            row = await cursor.fetchone()

        if row:
            return dict(row)

        # Create new user
        cursor = await db.execute(
            "INSERT INTO users (telegram_id) VALUES (?)", (telegram_id,)
        )
        user_db_id = cursor.lastrowid
        await db.commit()

    # Seed default categories (uses its own connection)
    await seed_categories_for_user(user_db_id)

    # Fetch and return the newly created user
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE id = ?", (user_db_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row)


async def update_month_start_day(telegram_id: int, day: int) -> None:
    """Update the financial month start day for a user."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET month_start_day = ? WHERE telegram_id = ?",
            (day, telegram_id),
        )
        await db.commit()


# ──────────────────────────── Categories ────────────────────────────

async def get_categories(telegram_id: int) -> list[dict]:
    """Return all categories for a user, ordered by type then name."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT c.* FROM categories c
            JOIN users u ON c.user_id = u.id
            WHERE u.telegram_id = ?
            ORDER BY c.type, c.name
            """,
            (telegram_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def add_category(telegram_id: int, name: str, cat_type: str, emoji: str = "") -> int:
    """Add a new category for a user. Returns the new category id."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Get user db id
        async with db.execute(
            "SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            user_row = await cursor.fetchone()

        cursor = await db.execute(
            "INSERT INTO categories (user_id, name, type, emoji) VALUES (?, ?, ?, ?)",
            (user_row["id"], name, cat_type, emoji),
        )
        cat_id = cursor.lastrowid
        await db.commit()
        return cat_id


async def rename_category(category_id: int, new_name: str) -> None:
    """Rename an existing category."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE categories SET name = ? WHERE id = ?",
            (new_name, category_id),
        )
        await db.commit()


async def delete_category(category_id: int) -> None:
    """Delete a category and its linked keywords."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM keywords WHERE category_id = ?", (category_id,))
        await db.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        await db.commit()


async def get_category_by_id(category_id: int) -> Optional[dict]:
    """Return a single category by its id, or None."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM categories WHERE id = ?", (category_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


# ──────────────────────────── Keywords ────────────────────────────

async def get_keyword_match(telegram_id: int, keyword: str) -> Optional[dict]:
    """
    Look up a keyword for this user. Returns the category dict if found, None otherwise.
    Matching is case-insensitive.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT c.* FROM keywords k
            JOIN categories c ON k.category_id = c.id
            JOIN users u ON k.user_id = u.id
            WHERE u.telegram_id = ? AND LOWER(k.keyword) = LOWER(?)
            """,
            (telegram_id, keyword),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def add_keyword(telegram_id: int, keyword: str, category_id: int) -> None:
    """Link a keyword to a category for this user."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            user_row = await cursor.fetchone()

        await db.execute(
            "INSERT INTO keywords (user_id, keyword, category_id) VALUES (?, ?, ?)",
            (user_row["id"], keyword.lower(), category_id),
        )
        await db.commit()


async def delete_keyword(keyword_id: int) -> None:
    """Delete a keyword by its id."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM keywords WHERE id = ?", (keyword_id,))
        await db.commit()


async def get_keywords_for_category(category_id: int) -> list[dict]:
    """Return all keywords linked to a category."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM keywords WHERE category_id = ?", (category_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


# ──────────────────────────── Transactions ────────────────────────────

async def add_transaction(
    telegram_id: int,
    amount: float,
    txn_type: str,
    category_id: int,
    note: str,
    date: str,
) -> int:
    """
    Insert a new transaction. Returns the new transaction id.
    txn_type must be 'income' or 'expense'.
    date should be in 'YYYY-MM-DD' format.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            user_row = await cursor.fetchone()

        cursor = await db.execute(
            """
            INSERT INTO transactions (user_id, amount, type, category_id, note, date)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_row["id"], amount, txn_type, category_id, note, date),
        )
        txn_id = cursor.lastrowid
        await db.commit()
        return txn_id


async def get_transactions_for_period(
    telegram_id: int, start_date: str, end_date: str
) -> list[dict]:
    """
    Return all transactions for a user within a date range (inclusive).
    Dates should be in 'YYYY-MM-DD' format.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT t.*, c.name AS category_name, c.emoji AS category_emoji,
                   c.type AS category_type
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            JOIN users u ON t.user_id = u.id
            WHERE u.telegram_id = ? AND t.date >= ? AND t.date <= ?
            ORDER BY t.date DESC, t.created_at DESC
            """,
            (telegram_id, start_date, end_date),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_recent_transactions(telegram_id: int, limit: int = 10) -> list[dict]:
    """Return the most recent transactions for a user."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT t.*, c.name AS category_name, c.emoji AS category_emoji,
                   c.type AS category_type
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            JOIN users u ON t.user_id = u.id
            WHERE u.telegram_id = ?
            ORDER BY t.date DESC, t.created_at DESC
            LIMIT ?
            """,
            (telegram_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def delete_transaction(txn_id: int) -> None:
    """Delete a transaction by its id."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM transactions WHERE id = ?", (txn_id,))
        await db.commit()


async def update_transaction(
    txn_id: int,
    amount: Optional[float] = None,
    category_id: Optional[int] = None,
    note: Optional[str] = None,
    date: Optional[str] = None,
) -> None:
    """Update fields of an existing transaction. Only non-None fields are updated."""
    updates = []
    params = []
    if amount is not None:
        updates.append("amount = ?")
        params.append(amount)
    if category_id is not None:
        updates.append("category_id = ?")
        params.append(category_id)
    if note is not None:
        updates.append("note = ?")
        params.append(note)
    if date is not None:
        updates.append("date = ?")
        params.append(date)

    if not updates:
        return

    params.append(txn_id)
    sql = f"UPDATE transactions SET {', '.join(updates)} WHERE id = ?"

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(sql, tuple(params))
        await db.commit()


async def get_transaction_by_id(txn_id: int) -> Optional[dict]:
    """Return a single transaction by its id, or None."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT t.*, c.name AS category_name, c.emoji AS category_emoji,
                   c.type AS category_type
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE t.id = ?
            """,
            (txn_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None
