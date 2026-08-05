"""
Transaction logging handler.
Parses raw text messages, matches keywords, and handles unknown categories.
"""

from typing import Dict

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

from bot.db.crud import (
    get_categories,
    get_keyword_match,
    add_keyword,
    add_transaction,
    get_category_by_id,
)
from bot.parser.text_parser import parse_message, ParsedMessage

router = Router()

# In-memory store for transactions waiting on category selection.
# Maps telegram_id (int) -> ParsedMessage
pending_txns: Dict[int, ParsedMessage] = {}


class CategorySelectCallback(CallbackData, prefix="cat_sel"):
    """Callback data for the unknown keyword category selection."""
    category_id: int


@router.message(F.text)
async def handle_text_message(message: Message) -> None:
    """Handle any raw text message as a potential transaction log."""
    telegram_id = message.from_user.id
    text = message.text

    # 1. Parse the message
    parsed = parse_message(text)
    if not parsed:
        # Ignore normal chat / commands that don't look like transactions.
        # But if it's not a command (doesn't start with /), maybe give a helpful error.
        if not text.startswith("/"):
            await message.answer(
                "I couldn't find an amount in that message. 🧐\n"
                "Try starting with a number, like `45 groceries` or `2500 salary`.",
                parse_mode="Markdown"
            )
        return

    # 2. If no words given (e.g. "82.55"), fallback to "Other Expenses"
    if not parsed.words:
        categories = await get_categories(telegram_id)
        fallback_cat = next((c for c in categories if c["name"] == "Other Expenses"), categories[0])
        await _log_and_reply(message, telegram_id, parsed, fallback_cat["id"], fallback_cat["type"], fallback_cat["name"], fallback_cat["emoji"])
        return

    # 3. We have words, try to match a keyword
    keyword = " ".join(parsed.words)
    match = await get_keyword_match(telegram_id, keyword)

    if match:
        # Known keyword -> log it immediately
        await _log_and_reply(message, telegram_id, parsed, match["id"], match["type"], match["name"], match["emoji"], keyword=keyword)
    else:
        # Unknown keyword -> ask user
        pending_txns[telegram_id] = parsed
        categories = await get_categories(telegram_id)
        
        builder = InlineKeyboardBuilder()
        for cat in categories:
            # e.g., "🛒 Groceries"
            btn_text = f"{cat['emoji']} {cat['name']}".strip()
            builder.button(
                text=btn_text, 
                callback_data=CategorySelectCallback(category_id=cat["id"]).pack()
            )
        
        # Adjust layout (2 buttons per row)
        builder.adjust(2)
        
        await message.answer(
            f"I don't recognize the word **\"{keyword}\"**. 🤔\n"
            "Which category should I link this to? (I'll remember it for next time).",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )


@router.callback_query(CategorySelectCallback.filter())
async def handle_category_selection(query: CallbackQuery, callback_data: CategorySelectCallback) -> None:
    """Handle the user tapping a category button for an unknown keyword."""
    telegram_id = query.from_user.id
    parsed = pending_txns.pop(telegram_id, None)

    if not parsed:
        await query.answer("This transaction has expired or was already logged.", show_alert=True)
        # Edit the message to remove buttons
        await query.message.edit_reply_markup(reply_markup=None)
        return

    category_id = callback_data.category_id
    cat = await get_category_by_id(category_id)
    if not cat:
        await query.answer("Category not found.", show_alert=True)
        return

    # Save the new keyword
    keyword = " ".join(parsed.words)
    await add_keyword(telegram_id, keyword, category_id)

    # Acknowledge the callback
    await query.answer("Category saved!")

    # Remove the buttons from the original message and update text
    await query.message.edit_text(f"✅ Linked **\"{keyword}\"** to {cat['emoji']} {cat['name']}.", parse_mode="Markdown")

    # Log the transaction
    await _log_and_reply(query.message, telegram_id, parsed, category_id, cat["type"], cat["name"], cat["emoji"], keyword=keyword, is_callback=True)


async def _log_and_reply(
    message: Message, 
    telegram_id: int, 
    parsed: ParsedMessage, 
    category_id: int, 
    category_type: str, 
    category_name: str, 
    category_emoji: str, 
    keyword: str = "",
    is_callback: bool = False
) -> None:
    """Helper to finalize the transaction logic and send a confirmation reply."""
    
    # Determine final sign/type
    if parsed.sign_override == "+":
        txn_type = "income"
    elif parsed.sign_override == "-":
        txn_type = "expense"
    else:
        txn_type = category_type

    # Log it
    await add_transaction(
        telegram_id=telegram_id,
        amount=parsed.amount,
        txn_type=txn_type,
        category_id=category_id,
        note=keyword,
        date=parsed.date
    )

    # Format reply
    action = "Earned" if txn_type == "income" else "Spent"
    reply = f"✅ **{action}** `₹{parsed.amount:.2f}`\n"
    reply += f"📂 {category_emoji} {category_name}\n"
    reply += f"📅 {parsed.date}"

    # If it was a callback, we reply as a new message so it acts like a normal log confirmation
    await message.answer(reply, parse_mode="Markdown")
