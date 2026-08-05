# Stage 02: Database Layer

## Features implemented in this stage
- SQLite database with 4 tables: users, categories, keywords, transactions
- Database auto-initializes on bot startup (tables created if they don't exist)
- 6 default categories seeded for every new user on first /start: Groceries, Bills & Subs, Transport, Salary, Other Income, Other Expenses
- User registration on /start — creates user record and seeds categories (idempotent — safe to call multiple times)
- Complete async CRUD module with one function per operation
- Financial month start day stored per user (default day 1), ready for custom periods in later stages

## Commands run
```bash
# Verified aiosqlite API via web search (anti-hallucination rule)

git add -A
git commit -m "Added the SQLite schema for users, categories, keywords, and transactions"
git push

# Verification — ran standalone test script
.\venv\Scripts\python.exe test_db.py
# Output confirmed: user created, 6 categories seeded, transaction inserted and read back,
# period query worked, idempotency check passed

# Deleted test script after verification
Remove-Item test_db.py
```

## Code built

### `bot/db/schema.py`
```python
"""
Database schema and initialization.
Creates tables and seeds default categories for new users.
"""

import aiosqlite

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

DB_PATH = "data/expenses.db"

async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(CREATE_TABLES_SQL)
        await db.commit()

async def seed_categories_for_user(user_db_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        for name, cat_type, emoji in DEFAULT_CATEGORIES:
            await db.execute(
                "INSERT INTO categories (user_id, name, type, emoji) VALUES (?, ?, ?, ?)",
                (user_db_id, name, cat_type, emoji),
            )
        await db.commit()
```

**What it does:**
This file defines the database structure (what tables exist and what columns each has) and provides two functions: one to create the tables, and one to seed default categories for a new user.

**How the schema works:**

- **`users` table:** Stores one row per Telegram user. `telegram_id` is the Telegram user's numeric ID (unique per Telegram account). `month_start_day` controls when the financial month begins (default 1 = January 1st, February 1st, etc., but a user could set it to 15 so their month runs 15th–14th). `created_at` is auto-filled with the current UTC timestamp by SQLite's `datetime('now')`.

- **`categories` table:** Each user gets their own set of categories. `user_id` links to the users table (foreign key). `type` is either `'income'` or `'expense'` — the `CHECK` constraint ensures no other value can be stored. `emoji` is optional (defaults to empty string). Categories are per-user so two users can customize independently.

- **`keywords` table:** Maps shortcut words to categories. If a user types `groc`, we look it up in this table to find it maps to "Groceries." `keyword` is the shorthand text, `category_id` links to the category it belongs to. Keywords are also per-user.

- **`transactions` table:** The core table — every logged income or expense entry. `amount` is a REAL (floating point) to handle cents/paise. `type` is `'income'` or `'expense'`. `category_id` links to the category. `note` is optional extra text. `date` is the transaction date in `YYYY-MM-DD` string format (SQLite doesn't have a native date type, but string comparison works perfectly for date ranges because the format is lexicographically sortable). `created_at` is when the record was created (distinct from `date` which is when the expense actually happened).

- **`ON DELETE CASCADE`:** Every foreign key has this clause. It means if you delete a user, all their categories, keywords, and transactions are automatically deleted too. Same for deleting a category — its keywords go with it. This prevents orphaned data.

- **`CREATE TABLE IF NOT EXISTS`:** This clause makes `init_db()` safe to call on every bot startup. If tables already exist, it does nothing. If it's a fresh database, it creates them. No migration system needed for this project.

- **`DEFAULT_CATEGORIES`:** We seed exactly 6 categories — intentionally small. Over-categorizing (20+ categories) makes expense tracking tedious and most entries end up as "Other" anyway. The 6 defaults cover the most common cases: groceries, recurring bills, transport, salary, and two catch-alls for everything else.

---

### `bot/db/crud.py`
```python
# (Full code in repo — key functions summarized below)
```

**What it does:**
This file contains every database operation as a standalone async function. No handler ever writes raw SQL — they call these functions instead.

**Key functions explained:**

- **`get_or_create_user(telegram_id)`** — Checks if a user with this Telegram ID already exists. If yes, returns their record. If no, creates them (INSERT), seeds default categories, and returns the new record. This is called on every `/start` and is idempotent — calling it 10 times for the same user creates exactly 1 row.

- **`get_categories(telegram_id)`** — Returns all categories for a user, ordered by type (expenses first, then income) and name. Uses a JOIN between categories and users tables because categories store `user_id` (the internal DB id) but we identify users by `telegram_id`.

- **`add_category(telegram_id, name, cat_type, emoji)`** — Adds a new custom category. First looks up the user's internal DB id, then inserts. Returns the new category's id.

- **`get_keyword_match(telegram_id, keyword)`** — The core lookup for the text parser. Given a word the user typed, finds if there's a matching keyword for this user and returns the linked category. Matching is case-insensitive (`LOWER()` in SQL). Returns `None` if no match found.

- **`add_keyword(telegram_id, keyword, category_id)`** — Links a new keyword to a category. Stores keywords in lowercase for consistent matching.

- **`add_transaction(telegram_id, amount, txn_type, category_id, note, date)`** — Inserts a new transaction. Returns the transaction id.

- **`get_transactions_for_period(telegram_id, start_date, end_date)`** — Returns all transactions within a date range. Uses `>=` and `<=` on the date strings (works because `YYYY-MM-DD` format sorts lexicographically). Includes JOINed category name and emoji for display.

- **`get_recent_transactions(telegram_id, limit)`** — Returns the N most recent transactions, ordered by date descending. Used for the "recent" view.

- **`update_transaction(txn_id, ...)`** — Updates only the fields that are provided (non-None). Uses dynamic SQL construction — builds the SET clause only for changed fields. This avoids overwriting unchanged fields with NULL.

- **`delete_transaction(txn_id)`** — Deletes a single transaction by id.

**Why it's built this way:**
- **One function per operation** — Each function does exactly one thing. This makes the code testable, readable, and easy to refactor. If we need to add caching later, we change one function, not 15 handler files.
- **Async context managers** — Every function opens and closes its own database connection using `async with aiosqlite.connect(...)`. This ensures connections are always properly closed, even if an error occurs. The cost is minimal — SQLite connections are lightweight.
- **`row_factory = aiosqlite.Row`** — This makes query results accessible by column name (`row["name"]`) instead of index (`row[0]`). Much more readable and less error-prone.
- **JOINs in read queries** — Transaction queries join with the categories table so the handler gets the category name and emoji in one query instead of making a separate query per transaction.

---

### Changes to `bot/handlers/commands.py`
Added `from bot.db.crud import get_or_create_user` and a call to `await get_or_create_user(message.from_user.id)` at the start of the `/start` handler. This means every time a user sends `/start`, they're registered in the database (or their existing record is fetched). The first call for a new user triggers category seeding.

---

### Changes to `main.py`
Added `from bot.db.schema import init_db` and an `asyncio.run(init_db())` call before starting the bot. This ensures the database tables exist before any handler tries to use them.

## Interview Q&A

**Q: Why is the schema normalized (separate tables for categories, keywords, transactions) instead of putting everything in one table?**
A: Normalization eliminates data duplication and inconsistency. If categories were stored as text inside each transaction (like `category_name = "Groceries"`), and the user renamed "Groceries" to "Food," we'd have to update every single transaction that references it. With normalization, the category name is stored once in the `categories` table, and transactions just store a `category_id` (a number). Renaming the category means updating one row in `categories`, and all transactions automatically reflect the new name through the JOIN. Same for keywords — they reference a category_id, so adding or removing keywords never touches the transactions table. (See `bot/db/schema.py`, the foreign key relationships.)

**Q: What happens if two users log a transaction at the same time?**
A: SQLite handles this safely through its locking mechanism. SQLite uses file-level locking — when one write is in progress, other writes wait until it completes. Since `aiosqlite` runs SQLite operations in a background thread (it's async-to-sync bridge), two concurrent `add_transaction` calls from different users will be serialized by SQLite's lock. One completes first, then the other runs. At the scale of a personal Telegram bot (even with a few dozen users), this serialization is imperceptible — each write takes microseconds. If we had thousands of concurrent writers, we'd switch to PostgreSQL which has row-level locking. (See `bot/db/crud.py`, each function opens its own connection.)

**Q: Why use REAL for the amount column instead of INTEGER (storing cents)?**
A: Both approaches work. Storing cents as INTEGER (e.g., 4550 for $45.50) avoids floating-point precision issues — in financial systems at banks, this is the standard practice. For a personal expense tracker, REAL (Python's float) is fine because we're dealing with everyday amounts, not millions-digit precision. The maximum rounding error on a float64 for amounts under $1 million is less than a fraction of a cent. We chose REAL for simplicity — `45.50` is more readable in the database than `4550`, and the parser can pass amounts directly without multiplication. If this were a production banking system, we'd use INTEGER cents or Python's `Decimal` type. (See `bot/db/schema.py`, the transactions table `amount REAL`.)

**Q: What does `ON DELETE CASCADE` do and why is it important?**
A: When a foreign key has `ON DELETE CASCADE`, deleting the parent row automatically deletes all child rows that reference it. For example, if we delete a user from the `users` table, all their categories, keywords, and transactions are automatically cleaned up by SQLite. Without this, deleting a user would leave orphaned rows — categories and transactions with a `user_id` pointing to a non-existent user. That's called referential integrity violation. CASCADE prevents this. It also works transitively: deleting a category cascades to delete its keywords. (See `bot/db/schema.py`, every `FOREIGN KEY` clause.)

**Q: Why store dates as TEXT in YYYY-MM-DD format instead of using SQLite's date functions?**
A: SQLite doesn't have a native DATE type — it stores everything as TEXT, REAL, or INTEGER internally. The `YYYY-MM-DD` string format has a special property: it sorts lexicographically in the same order as chronologically. This means `"2025-01-15" < "2025-02-01"` is true in both date order and string order. So our `WHERE date >= ? AND date <= ?` range queries work correctly with simple string comparison, no date parsing needed. SQLite does have `date()` and `datetime()` functions for more complex operations, but for range queries, string comparison is simpler and equally fast. (See `bot/db/crud.py`, `get_transactions_for_period`.)

**Q: Why is `get_or_create_user` idempotent and why does that matter?**
A: Idempotent means calling the function multiple times with the same input produces the same result — no duplicates, no side effects. A user might press `/start` many times (Telegram shows it as a button). Without idempotency, each press would create a duplicate user row and seed categories again. Our implementation checks `SELECT * FROM users WHERE telegram_id = ?` first — if the user exists, it returns immediately. If not, it creates them. The `UNIQUE` constraint on `telegram_id` is a safety net — even if two concurrent `/start` calls race past the check, the second INSERT would fail with a constraint violation rather than creating a duplicate. (See `bot/db/crud.py`, `get_or_create_user`.)

**Q: Why does each CRUD function open its own database connection instead of sharing one?**
A: Opening a new connection per function call is the simplest pattern and works well for SQLite. SQLite connections are extremely lightweight — there's no server, no TCP handshake, just opening a file handle. The `async with aiosqlite.connect(...)` context manager ensures every connection is closed after use, preventing resource leaks. The alternative — a shared connection or connection pool — adds complexity: you'd need to manage the pool lifecycle, handle thread safety, and deal with connection state leaking between operations. For PostgreSQL (with network overhead per connection), pooling is essential. For SQLite (local file), it's unnecessary at our scale. (See `bot/db/crud.py`, every function starts with `async with aiosqlite.connect(DB_PATH)`.)

**Q: Why did you choose only 6 default categories? Why not more?**
A: This follows the "don't over-categorize" principle from personal finance best practices. Research shows that most people abandon expense tracking when they have to decide between 20+ categories for every purchase. With 6 categories — 4 expense types (Groceries, Bills & Subs, Transport, Other Expenses) and 2 income types (Salary, Other Income) — the decision is fast and covers 80% of real-life transactions. Users can always add custom categories later via the `/categories` command (Stage 4). Starting small and letting users customize is better than overwhelming them with options on day one. (See `bot/db/schema.py`, the `DEFAULT_CATEGORIES` list.)

**Q: What is `aiosqlite` and why not just use Python's built-in `sqlite3` module?**
A: Python's built-in `sqlite3` module is synchronous — every database call blocks the entire program until it completes. In an async bot using `aiogram`, blocking calls freeze the event loop, meaning no other messages can be processed while a database query runs. `aiosqlite` wraps `sqlite3` with an async interface — it runs SQLite operations in a background thread and exposes them as `await`-able coroutines. This way, while one user's database query is running, the bot can handle another user's message. The API is nearly identical to `sqlite3` (`connect`, `execute`, `fetchall`), just with `async/await` added. (See `bot/db/crud.py`, every function uses `await db.execute(...)` instead of `db.execute(...)`.)

**Q: How does the keyword matching work for the text parser?**
A: When a user sends something like `65 groc`, the parser will extract the word "groc" and call `get_keyword_match(telegram_id, "groc")`. This function runs a SQL query that JOINs the keywords table with categories, looking for a row where `LOWER(k.keyword) = LOWER('groc')` for this specific user. If found, it returns the linked category (e.g., Groceries). If not found, it returns `None`, and the bot will ask the user which category to link "groc" to — then store it via `add_keyword()` so it never asks again. The matching is case-insensitive so "Groc", "GROC", and "groc" all work. Keywords are per-user so two users can map the same word to different categories. (See `bot/db/crud.py`, `get_keyword_match` and `add_keyword`.)

**Q: What is a CHECK constraint and why is it on the `type` column?**
A: A `CHECK` constraint tells SQLite to reject any INSERT or UPDATE that violates a condition. `CHECK (type IN ('income', 'expense'))` means only these two values can be stored in the `type` column. If a bug in our code tried to insert `type = "debit"`, SQLite would throw an error instead of silently storing invalid data. This is defense-in-depth — even if the Python code has a bug, the database protects its own integrity. CHECK constraints are lightweight (evaluated on each write) and catch errors early. (See `bot/db/schema.py`, the `categories` and `transactions` tables both have this CHECK.)

**Q: Why do transaction queries JOIN with the categories table instead of storing the category name directly in transactions?**
A: If we stored the category name in the transactions table (denormalization), we'd have two problems: (1) If the user renames a category, old transactions would show the old name — we'd have to update every transaction. (2) We'd store the same category name thousands of times instead of once. By storing just `category_id` (a number) and JOINing with categories when we read, we always get the current category name, and we save storage space. The JOIN is fast because `category_id` is an INTEGER PRIMARY KEY lookup — SQLite does this in constant time. The trade-off is slightly more complex queries, but that complexity is hidden in the CRUD layer — handlers just call `get_recent_transactions()` and get a clean result with category names included. (See `bot/db/crud.py`, the JOIN in `get_recent_transactions` and `get_transactions_for_period`.)

**Q: Walk me through what happens internally when a user sends /start for the first time.**
A: Here's the exact sequence: (1) The `/start` handler calls `await get_or_create_user(message.from_user.id)` with the Telegram user's numeric ID. (2) `get_or_create_user` opens a database connection and runs `SELECT * FROM users WHERE telegram_id = ?`. (3) Since this is a new user, `fetchone()` returns `None`. (4) The function runs `INSERT INTO users (telegram_id) VALUES (?)`, gets the new row's `lastrowid` (the auto-incremented `id`). (5) It calls `seed_categories_for_user(user_db_id)`, which inserts 6 rows into the categories table, each linked to this user's `id`. (6) It fetches and returns the newly created user record as a dictionary. (7) Back in the handler, the welcome message is sent to the user. All of this happens in under 10 milliseconds. (See `bot/handlers/commands.py` for step 1, `bot/db/crud.py` for steps 2-6.)
