"""
Deterministic text parser for transaction messages.

Pure Python/regex — no LLM calls, no database access.
Extracts: amount, sign override, category/keyword words, and date.
"""

import re
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional


@dataclass
class ParsedMessage:
    """Structured result of parsing a user's text message."""

    amount: float                  # The transaction amount (always positive)
    sign_override: Optional[str]   # '+' forces income, '-' forces expense, None = use category default
    words: list[str]               # Remaining words (potential category names or keywords)
    date: str                      # Transaction date in YYYY-MM-DD format


# ────────────────── Regex patterns ──────────────────

# Amount: optional +/- sign, followed by digits with optional decimal part
AMOUNT_RE = re.compile(r'^([+-]?)(\d+(?:\.\d+)?)$')

# ISO date: YYYY-MM-DD
DATE_ISO_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')

# Slash date: D/M/YYYY or DD/MM/YYYY
DATE_SLASH_RE = re.compile(r'^(\d{1,2})/(\d{1,2})/(\d{4})$')

# Relative date words
RELATIVE_DATES = {'today', 'yesterday'}


def parse_message(text: str) -> Optional[ParsedMessage]:
    """
    Parse a user message into structured transaction data.

    Handles these input formats:
        45 groceries              → amount=45, words=["groceries"], date=today
        2500 pay                  → amount=2500, words=["pay"], date=today
        82.55                     → amount=82.55, words=[], date=today
        200 beer 2024-12-26       → amount=200, words=["beer"], date=2024-12-26
        200 beer\\n25/05/2025     → amount=200, words=["beer"], date=2025-05-25
        200 beer\\nyesterday      → amount=200, words=["beer"], date=yesterday
        +45 groceries             → amount=45, sign_override='+', words=["groceries"]
        -2500 salary              → amount=2500, sign_override='-', words=["salary"]

    Returns None if no valid amount is found in the message.
    """
    # Tokenize: split on whitespace (handles multi-line input)
    tokens = text.strip().split()
    if not tokens:
        return None

    amount: Optional[float] = None
    sign_override: Optional[str] = None
    date_str: Optional[str] = None
    words: list[str] = []

    for token in tokens:
        # ── Try matching as amount (take the first number found) ──
        if amount is None:
            m = AMOUNT_RE.match(token)
            if m:
                sign = m.group(1)
                amount = float(m.group(2))
                if sign:
                    sign_override = sign
                continue

        # ── Try matching as ISO date (YYYY-MM-DD) ──
        if date_str is None and DATE_ISO_RE.match(token):
            try:
                datetime.strptime(token, '%Y-%m-%d')
                date_str = token
                continue
            except ValueError:
                pass  # Invalid date like 2025-13-45, treat as word

        # ── Try matching as slash date (DD/MM/YYYY) ──
        if date_str is None:
            m = DATE_SLASH_RE.match(token)
            if m:
                day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
                try:
                    d = datetime(year, month, day)
                    date_str = d.strftime('%Y-%m-%d')
                    continue
                except ValueError:
                    pass  # Invalid date, treat as word

        # ── Try matching as relative date ──
        if date_str is None and token.lower() in RELATIVE_DATES:
            today = datetime.now()
            if token.lower() == 'yesterday':
                date_str = (today - timedelta(days=1)).strftime('%Y-%m-%d')
            else:
                date_str = today.strftime('%Y-%m-%d')
            continue

        # ── Not amount, not date → it's a word ──
        words.append(token)

    # No amount found → this isn't a transaction message
    if amount is None:
        return None

    # Amount of zero is not meaningful
    if amount == 0:
        return None

    # Default date to today if none was specified
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    return ParsedMessage(
        amount=amount,
        sign_override=sign_override,
        words=words,
        date=date_str,
    )
