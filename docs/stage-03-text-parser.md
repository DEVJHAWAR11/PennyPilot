# Stage 03: Deterministic Text Parser

## Features implemented in this stage
- **Deterministic Text Parser (`text_parser.py`)**: A pure Python/regex parser that extracts amount, optional sign override (`+` or `-`), transaction date, and remaining words (as the keyword). It does not use LLMs, ensuring it is 100% predictable, fast, and free to run.
- **Date Handling**: Supports ISO dates (`YYYY-MM-DD`), slash dates (`DD/MM/YYYY`), and relative dates (`today`, `yesterday`). Defaults to today if no date is provided.
- **Message Logging Handler (`logging.py`)**: Listens to raw text messages. If an amount is detected, it processes it as a transaction.
- **Unknown Keyword Flow**: If a user types a word that doesn't match an existing category or keyword, the bot replies with an inline keyboard asking the user to map it to a category. It uses aiogram's `CallbackData` and an in-memory dictionary to store the pending transaction state. Once selected, it saves the keyword to the database so it never asks again for that word.
- **Sign Overrides**: By default, transactions use the underlying category's type. However, if a user explicitly types `+` (e.g., `+45 groceries`), it forces the transaction to be logged as income. `-` forces an expense.

## Commands run
```bash
git add -A
git commit -m "Added deterministic text parser and transaction logging handler with unknown keyword flow"
git push
```

## Code built

### `bot/parser/text_parser.py`
```python
import re
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional

@dataclass
class ParsedMessage:
    amount: float
    sign_override: Optional[str]
    words: list[str]
    date: str

AMOUNT_RE = re.compile(r'^([+-]?)(\d+(?:\.\d+)?)$')
DATE_ISO_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
DATE_SLASH_RE = re.compile(r'^(\d{1,2})/(\d{1,2})/(\d{4})$')
RELATIVE_DATES = {'today', 'yesterday'}

def parse_message(text: str) -> Optional[ParsedMessage]:
    tokens = text.strip().split()
    if not tokens:
        return None

    amount = None
    sign_override = None
    date_str = None
    words = []

    for token in tokens:
        if amount is None:
            m = AMOUNT_RE.match(token)
            if m:
                sign = m.group(1)
                amount = float(m.group(2))
                if sign:
                    sign_override = sign
                continue

        if date_str is None and DATE_ISO_RE.match(token):
            try:
                datetime.strptime(token, '%Y-%m-%d')
                date_str = token
                continue
            except ValueError:
                pass

        if date_str is None:
            m = DATE_SLASH_RE.match(token)
            if m:
                day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
                try:
                    d = datetime(year, month, day)
                    date_str = d.strftime('%Y-%m-%d')
                    continue
                except ValueError:
                    pass

        if date_str is None and token.lower() in RELATIVE_DATES:
            today = datetime.now()
            if token.lower() == 'yesterday':
                date_str = (today - timedelta(days=1)).strftime('%Y-%m-%d')
            else:
                date_str = today.strftime('%Y-%m-%d')
            continue

        words.append(token)

    if amount is None or amount == 0:
        return None

    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    return ParsedMessage(amount, sign_override, words, date_str)
```
**What it does:**
This module tokenizes the incoming message by whitespace and attempts to find an amount, a date, and the leftover words. It iterates over the tokens exactly once. The first token that looks like a number becomes the amount. The first token that looks like a date becomes the date. Everything else is gathered into the `words` list.
This deterministic approach is extremely robust and avoids the latency and hallucination risks of an LLM.

### `bot/handlers/logging.py`
```python
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData
# ... imports ...

router = Router()
pending_txns = {}

class CategorySelectCallback(CallbackData, prefix="cat_sel"):
    category_id: int

@router.message(F.text)
async def handle_text_message(message: Message) -> None:
    # 1. Parse the message
    # 2. If no words given, fallback to "Other Expenses"
    # 3. If words given, check database (get_keyword_match)
    # 4. If exact match found -> log transaction
    # 5. If unknown word -> save state to `pending_txns` and send InlineKeyboard
    pass

@router.callback_query(CategorySelectCallback.filter())
async def handle_category_selection(query: CallbackQuery, callback_data: CategorySelectCallback) -> None:
    # 1. Retrieve pending transaction from `pending_txns`
    # 2. Save the new keyword mapping to the database
    # 3. Log the transaction
    # 4. Edit message to remove buttons and show success
    pass
```
**What it does:**
This is the core flow for manual text entry. We register a handler for all text messages. We parse it, check if we know the keyword, and if not, we use an inline keyboard to ask the user. We use a simple in-memory dict (`pending_txns`) to hold the transaction details while we wait for the user to tap a button.

---

### Update to `bot/db/crud.py`
Updated `get_keyword_match` to also check exact category names. Previously, it only checked the `keywords` table, meaning if a user typed "groceries" (the exact name of the category), it didn't recognize it unless they explicitly mapped it. Now it first checks for an exact (case-insensitive) match against the `categories` table, then falls back to checking the `keywords` table.

## Interview Q&A

**Q: Why use a custom regex parser instead of an LLM for text parsing?**
A: LLMs are powerful but they introduce latency (1-3 seconds), cost (API calls), and unpredictability (hallucinations). A personal expense tracker is a high-frequency utility. Users want instant feedback when they log a coffee. A deterministic regex parser executes in less than a millisecond, costs nothing, and behaves 100% predictably. We reserve the LLM for voice notes (Stage 5) where deterministic parsing is impossible.

**Q: How does the parser handle multi-line messages?**
A: By using `.split()` on the string, the parser tokenizes by any whitespace, including newlines (`\n`). This means `200 beer\nyesterday` is tokenized into `["200", "beer", "yesterday"]`, which is identical to `200 beer yesterday`. This makes the parser incredibly robust to how the user types.

**Q: What is `CallbackData` and why is it used for the inline keyboard?**
A: In Telegram, inline keyboard buttons can send a small payload (up to 64 bytes) back to the bot when clicked. Aiogram provides a `CallbackData` factory class that lets us define a strongly-typed structure for this payload (like `CategorySelectCallback(category_id=1)`). Aiogram automatically packs this into a short string (e.g., `cat_sel:1`) and unpacks it when the callback is received. It ensures type safety and makes filtering callbacks clean.

**Q: Why store pending transactions in an in-memory dictionary? What happens if the bot restarts?**
A: `pending_txns` is a module-level dictionary mapping `telegram_id` to the parsed transaction data. We use this to temporarily hold the data while waiting for the user to tap a category button. If the bot restarts while a transaction is pending, that transaction is lost from memory. If the user then taps the button, `pending_txns.pop()` returns `None`, and we reply with a polite "This transaction has expired" message. For a simple bot, an in-memory dict is perfectly fine. For a highly reliable production bot, we would use aiogram's FSM (Finite State Machine) backed by Redis.

**Q: How do you handle the sign override logic?**
A: The parser captures an optional leading `+` or `-` from the amount regex. When logging the transaction, we first check if the user provided an override. If they typed `+`, we force `txn_type = "income"`. If `-`, we force `txn_type = "expense"`. If neither, we default to whatever `txn_type` the matched category uses (e.g., "Salary" defaults to income, "Groceries" defaults to expense).

**Q: Why does the bot only ask to link a keyword once per user?**
A: User friction must be minimized. When the user taps a category button for an unknown word, the callback handler immediately calls `add_keyword()` to save that mapping in the database. The next time the user types that exact same word, `get_keyword_match()` will find it, and the transaction is logged instantly without asking. The bot effectively "learns" the user's vocabulary.

**Q: Why did you update `get_keyword_match` to check category names?**
A: Without this, a user typing `45 groceries` would be asked to map the word "groceries" to the "Groceries" category, because the word didn't exist in the `keywords` table yet. By updating `get_keyword_match` to do a case-insensitive check against the `categories` table first, we make the bot instantly recognize exact category names, providing a much smoother initial experience.
