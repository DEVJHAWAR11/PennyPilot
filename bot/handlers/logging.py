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
    needs_confirmation: bool = False

class ConfirmTxnCallback(CallbackData, prefix="txn_conf"):
    """Callback data for confirming an AI-transcribed transaction."""
    confirm: bool


@router.message(F.text)
async def handle_text_message(message: Message) -> None:
    """Handle any raw text message as a potential transaction log."""
    await process_transaction_text(message, message.text, needs_confirmation=False)


async def process_transaction_text(message: Message, text: str, needs_confirmation: bool = False) -> None:
    """Core logic to parse and route a transaction text."""
    telegram_id = message.from_user.id
    
    # Guarantee user exists in DB
    from bot.db.crud import get_or_create_user
    await get_or_create_user(telegram_id)

    # 1. Parse the message
    parsed = parse_message(text)
    if not parsed:
        # Ignore commands
        if not text.startswith("/"):
            await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
            from bot.agent.graph import ask_agent
            try:
                reply = await ask_agent(telegram_id, text)
                import re
                if "[CHART_PATH:" in reply:
                    match = re.search(r"\[CHART_PATH:(.*?)\]", reply)
                    if match:
                        chart_path = match.group(1)
                        clean_reply = re.sub(r"\[CHART_PATH:.*?\]", "", reply).strip()
                        from aiogram.types import FSInputFile
                        photo = FSInputFile(chart_path)
                        await message.answer_photo(photo=photo, caption=clean_reply)
                    else:
                        await message.answer(reply)
                else:
                    await message.answer(reply)
            except Exception as e:
                await message.answer(
                    "I couldn't find an amount in that message to log a transaction, "
                    "and my query agent encountered an error. 🧐\n"
                    "Try starting with a number, like `45 groceries` or `2500 salary`."
                )
        return

    # 2. If no words given (e.g. "82.55"), fallback to "Other Expenses"
    if not parsed.words:
        categories = await get_categories(telegram_id)
        fallback_cat = next((c for c in categories if c["name"] == "Other Expenses"), categories[0])
        await _log_and_reply(message, telegram_id, parsed, fallback_cat["id"], fallback_cat["type"], fallback_cat["name"], fallback_cat["emoji"], needs_confirmation=needs_confirmation)
        return

    # 3. We have words, try to match a keyword
    keyword = " ".join(parsed.words)
    match = await get_keyword_match(telegram_id, keyword)

    if match:
        # Known keyword -> log it immediately (or confirm)
        await _log_and_reply(message, telegram_id, parsed, match["id"], match["type"], match["name"], match["emoji"], keyword=keyword, needs_confirmation=needs_confirmation)
    else:
        # If the user typed a long sentence (e.g. "i spend 300 on food today")
        # the keyword will be long. Route this to the AI agent instead of the basic parser.
        if len(parsed.words) > 2:
            await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
            from bot.agent.graph import ask_agent
            try:
                reply = await ask_agent(telegram_id, text)
                await message.answer(reply)
            except Exception as e:
                await message.answer(f"Agent error: {e}")
            return
            
        # Unknown short keyword -> ask user
        pending_txns[telegram_id] = parsed
        categories = await get_categories(telegram_id)
        
        builder = InlineKeyboardBuilder()
        for cat in categories:
            # e.g., "🛒 Groceries"
            btn_text = f"{cat['emoji']} {cat['name']}".strip()
            builder.button(
                text=btn_text, 
                callback_data=CategorySelectCallback(category_id=cat["id"], needs_confirmation=needs_confirmation).pack()
            )
        
        # Adjust layout (2 buttons per row)
        builder.adjust(2)
        
        # Mention the transcribed text if this came from voice/vision
        transcribed_note = f"\n*(I heard/saw: \"{text}\")*" if needs_confirmation else ""
        
        await message.answer(
            f"I don't recognize the word **\"{keyword}\"**. 🤔\n"
            f"Which category should I link this to?{transcribed_note}",
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

    # Log the transaction (or confirm)
    await _log_and_reply(query.message, telegram_id, parsed, category_id, cat["type"], cat["name"], cat["emoji"], keyword=keyword, is_callback=True, needs_confirmation=callback_data.needs_confirmation)


@router.callback_query(ConfirmTxnCallback.filter())
async def handle_txn_confirmation(query: CallbackQuery, callback_data: ConfirmTxnCallback) -> None:
    """Handle the user confirming or cancelling an AI-transcribed transaction."""
    telegram_id = query.from_user.id
    
    if not callback_data.confirm:
        pending_txns.pop(telegram_id, None)
        await query.answer("Transaction cancelled.")
        await query.message.edit_text("❌ Transaction cancelled.", parse_mode="Markdown")
        return

    # User confirmed
    pending_data = pending_txns.pop(telegram_id, None)
    if not pending_data:
        await query.answer("Transaction expired.", show_alert=True)
        await query.message.edit_reply_markup(reply_markup=None)
        return
        
    # Unpack the pending data we stored for confirmation
    parsed, category_id, cat_type, cat_name, cat_emoji, keyword = pending_data
    
    # Actually log it now
    await _log_and_reply(query.message, telegram_id, parsed, category_id, cat_type, cat_name, cat_emoji, keyword=keyword, is_callback=True, needs_confirmation=False)
    await query.answer("Transaction logged!")


async def _log_and_reply(
    message: Message, 
    telegram_id: int, 
    parsed: ParsedMessage, 
    category_id: int, 
    category_type: str, 
    category_name: str, 
    category_emoji: str, 
    keyword: str = "",
    is_callback: bool = False,
    needs_confirmation: bool = False
) -> None:
    """Helper to finalize the transaction logic and send a confirmation reply."""
    
    # Determine final sign/type
    if parsed.sign_override == "+":
        txn_type = "income"
    elif parsed.sign_override == "-":
        txn_type = "expense"
    else:
        txn_type = category_type

    action = "Earned" if txn_type == "income" else "Spent"
    reply = f"✅ **{action}** `₹{parsed.amount:.2f}`\n"
    reply += f"📂 {category_emoji} {category_name}\n"
    reply += f"📅 {parsed.date}"

    # If it needs confirmation (Voice/Vision), don't log yet. Ask first.
    if needs_confirmation:
        # Save to pending txns as a tuple
        pending_txns[telegram_id] = (parsed, category_id, category_type, category_name, category_emoji, keyword)
        
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Confirm", callback_data=ConfirmTxnCallback(confirm=True).pack())
        builder.button(text="❌ Cancel", callback_data=ConfirmTxnCallback(confirm=False).pack())
        builder.adjust(2)
        
        ask_text = f"🎙️ **I heard:**\n{reply}\n\nIs this correct?"
        if is_callback:
            await message.answer(ask_text, reply_markup=builder.as_markup(), parse_mode="Markdown")
        else:
            await message.reply(ask_text, reply_markup=builder.as_markup(), parse_mode="Markdown")
        return

    # Otherwise, log it immediately
    await add_transaction(
        telegram_id=telegram_id,
        amount=parsed.amount,
        txn_type=txn_type,
        category_id=category_id,
        note=keyword,
        date=parsed.date
    )

    # If it was a callback, we reply as a new message so it acts like a normal log confirmation
    if is_callback:
        await message.answer(reply, parse_mode="Markdown")
    else:
        await message.reply(reply, parse_mode="Markdown")
