"""
Async CRUD functions for the database.

One function per operation — no raw SQL in handlers.
"""

import datetime
from typing import Optional
from bot.db.schema import get_pool, seed_categories_for_user

# ──────────────────────────── Users ────────────────────────────

async def get_or_create_user(telegram_id: int) -> dict:
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE telegram_id = $1", telegram_id)
        if row:
            return dict(row)
        
        user_db_id = await conn.fetchval(
            "INSERT INTO users (telegram_id) VALUES ($1) RETURNING id", telegram_id
        )
    await seed_categories_for_user(user_db_id)
    async with p.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_db_id)
        return dict(row)

async def get_all_users() -> list[dict]:
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM users")
        return [dict(r) for r in rows]

async def update_month_start_day(telegram_id: int, day: int) -> None:
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("UPDATE users SET month_start_day = $1 WHERE telegram_id = $2", day, telegram_id)

# ──────────────────────────── Categories ────────────────────────────

async def get_categories(telegram_id: int) -> list[dict]:
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT c.* FROM categories c
            JOIN users u ON c.user_id = u.id
            WHERE u.telegram_id = $1
            ORDER BY c.type, c.name
            """, telegram_id
        )
        return [dict(r) for r in rows]

async def add_category(telegram_id: int, name: str, cat_type: str, emoji: str = "") -> int:
    p = await get_pool()
    async with p.acquire() as conn:
        user_id = await conn.fetchval("SELECT id FROM users WHERE telegram_id = $1", telegram_id)
        cat_id = await conn.fetchval(
            "INSERT INTO categories (user_id, name, type, emoji) VALUES ($1, $2, $3, $4) RETURNING id",
            user_id, name, cat_type, emoji
        )
        return cat_id

async def rename_category(category_id: int, new_name: str) -> None:
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("UPDATE categories SET name = $1 WHERE id = $2", new_name, category_id)

async def delete_category(category_id: int) -> None:
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("DELETE FROM keywords WHERE category_id = $1", category_id)
        await conn.execute("DELETE FROM categories WHERE id = $1", category_id)

async def get_category_by_id(category_id: int) -> Optional[dict]:
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM categories WHERE id = $1", category_id)
        return dict(row) if row else None

# ──────────────────────────── Keywords ────────────────────────────

async def get_keyword_match(telegram_id: int, keyword: str) -> Optional[dict]:
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT c.* FROM categories c
            JOIN users u ON c.user_id = u.id
            WHERE u.telegram_id = $1 AND LOWER(c.name) = LOWER($2)
            """, telegram_id, keyword
        )
        if row:
            return dict(row)
            
        row = await conn.fetchrow(
            """
            SELECT c.* FROM keywords k
            JOIN categories c ON k.category_id = c.id
            JOIN users u ON k.user_id = u.id
            WHERE u.telegram_id = $1 AND LOWER(k.keyword) = LOWER($2)
            """, telegram_id, keyword
        )
        return dict(row) if row else None

async def add_keyword(telegram_id: int, keyword: str, category_id: int) -> None:
    p = await get_pool()
    async with p.acquire() as conn:
        user_id = await conn.fetchval("SELECT id FROM users WHERE telegram_id = $1", telegram_id)
        await conn.execute(
            "INSERT INTO keywords (user_id, keyword, category_id) VALUES ($1, $2, $3)",
            user_id, keyword.lower(), category_id
        )

async def delete_keyword(keyword_id: int) -> None:
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("DELETE FROM keywords WHERE id = $1", keyword_id)

async def get_keywords_for_category(category_id: int) -> list[dict]:
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM keywords WHERE category_id = $1", category_id)
        return [dict(r) for r in rows]

# ──────────────────────────── Transactions ────────────────────────────

async def add_transaction(telegram_id: int, amount: float, txn_type: str, category_id: int, note: str, date: str) -> int:
    p = await get_pool()
    async with p.acquire() as conn:
        user_id = await conn.fetchval("SELECT id FROM users WHERE telegram_id = $1", telegram_id)
        
        parsed_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        
        txn_id = await conn.fetchval(
            """
            INSERT INTO transactions (user_id, amount, type, category_id, note, date)
            VALUES ($1, $2, $3, $4, $5, $6) RETURNING id
            """,
            user_id, amount, txn_type, category_id, note, parsed_date
        )
        return txn_id

async def get_transactions_for_period(telegram_id: int, start_date: str, end_date: str) -> list[dict]:
    p = await get_pool()
    async with p.acquire() as conn:
        start_d = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
        end_d = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
        rows = await conn.fetch(
            """
            SELECT t.*, c.name AS category_name, c.emoji AS category_emoji,
                   c.type AS category_type
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            JOIN users u ON t.user_id = u.id
            WHERE u.telegram_id = $1 AND t.date >= $2 AND t.date <= $3
            ORDER BY t.date DESC, t.created_at DESC
            """, telegram_id, start_d, end_d
        )
        
        def format_row(r):
            d = dict(r)
            d['date'] = str(d['date'])
            d['created_at'] = str(d['created_at'])
            return d
            
        return [format_row(r) for r in rows]

async def get_recent_transactions(telegram_id: int, limit: int = 10) -> list[dict]:
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT t.*, c.name AS category_name, c.emoji AS category_emoji,
                   c.type AS category_type
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            JOIN users u ON t.user_id = u.id
            WHERE u.telegram_id = $1
            ORDER BY t.date DESC, t.created_at DESC
            LIMIT $2
            """, telegram_id, limit
        )
        def format_row(r):
            d = dict(r)
            d['date'] = str(d['date'])
            d['created_at'] = str(d['created_at'])
            return d
        return [format_row(r) for r in rows]

async def delete_transaction(txn_id: int) -> None:
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("DELETE FROM transactions WHERE id = $1", txn_id)

async def update_transaction(txn_id: int, amount: Optional[float] = None, category_id: Optional[int] = None, note: Optional[str] = None, date: Optional[str] = None) -> None:
    updates = []
    params = []
    i = 1
    if amount is not None:
        updates.append(f"amount = ${i}")
        params.append(amount)
        i += 1
    if category_id is not None:
        updates.append(f"category_id = ${i}")
        params.append(category_id)
        i += 1
    if note is not None:
        updates.append(f"note = ${i}")
        params.append(note)
        i += 1
    if date is not None:
        updates.append(f"date = ${i}")
        params.append(datetime.datetime.strptime(date, "%Y-%m-%d").date())
        i += 1

    if not updates:
        return

    params.append(txn_id)
    sql = f"UPDATE transactions SET {', '.join(updates)} WHERE id = ${i}"

    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute(sql, *params)

async def get_transaction_by_id(txn_id: int) -> Optional[dict]:
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT t.*, c.name AS category_name, c.emoji AS category_emoji,
                   c.type AS category_type
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE t.id = $1
            """, txn_id
        )
        if not row:
            return None
        d = dict(row)
        d['date'] = str(d['date'])
        d['created_at'] = str(d['created_at'])
        return d

async def reset_user_data(telegram_id: int) -> None:
    p = await get_pool()
    async with p.acquire() as conn:
        user_id = await conn.fetchval("SELECT id FROM users WHERE telegram_id = $1", telegram_id)
        if not user_id:
            return
        
        await conn.execute("DELETE FROM transactions WHERE user_id = $1", user_id)
        await conn.execute("DELETE FROM keywords WHERE user_id = $1", user_id)
        await conn.execute("DELETE FROM categories WHERE user_id = $1", user_id)
        
    await seed_categories_for_user(user_id)
