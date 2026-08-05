"""
Command handlers — /start and /help for the bot skeleton.
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.db.crud import get_or_create_user

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    """Greet the user and register them if they're new."""
    # Register user in DB (seeds default categories on first /start)
    await get_or_create_user(message.from_user.id)
    await message.answer(
        "Hey! 👋 I'm PennyPilot — your personal expense tracker.\n\n"
        "Send me an amount and what it was for, like:\n"
        "• `45 groceries`\n"
        "• `2500 salary`\n"
        "• `200 beer 2025-01-15`\n\n"
        "✨ **AI Assistant Built-in!**\n"
        "You can also just talk to me in simple English:\n"
        "• _\"I spent 300 on swiggy today\"_\n"
        "• _\"How much did I spend on food this month?\"_\n\n"
        "I'll log it instantly or answer your question. You can also send a 🎙 voice note "
        "or a 📸 receipt photo and I'll figure it out.\n\n"
        "Type /help to see everything I can do.",
        parse_mode="Markdown",
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Show available commands."""
    await message.answer(
        "📖 *Here's what I can do:*\n\n"
        "🤖 *Talk to AI (Text, Voice, or Photo)*\n"
        "Just talk to me in simple English or send a voice note/receipt! I understand questions and commands:\n"
        "• _\"I spent ₹400 on swiggy today\"_ — I'll log it under Food.\n"
        "• _\"How much did I spend on transport this month?\"_ — I'll check your records.\n"
        "• _\"Generate a chart of my expenses\"_ — I'll draw a pie chart.\n"
        "• 📸 _*Send a photo of a receipt*_ — I'll scan it and extract the amount automatically!\n\n"
        "📝 *Quick Logging Format*\n"
        "You can also use the fast format: `[amount] [category] [date]`\n"
        "• `45 groceries`\n"
        "• `2500 salary`\n"
        "• `200 beer 2025-01-15`\n\n"
        "*Commands:*\n"
        "/start — Welcome message\n"
        "/help — This help menu\n"
        "/ask — Ask the AI a question explicitly\n"
        "/categories — Manage your custom categories and keywords.\n"
        "/balance — See your income, expenses, and net balance for the month.\n"
        "/stats — View a breakdown of your spending for past months.\n"
        "/export — Download your data as CSV or PDF.\n"
        "/recent — View, edit, or delete recent transactions.\n"
        "/settings — Change your financial month start day (e.g. payday).\n"
        "/reset — ⚠️ Wipe all your data completely.\n",
        parse_mode="Markdown",
    )

from aiogram import F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

@router.message(Command("reset"))
async def cmd_reset(message: Message) -> None:
    """Show the reset confirmation menu."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⚠️ Yes, Wipe Everything", callback_data="confirm_reset")
    builder.button(text="❌ Cancel", callback_data="cancel_reset")
    builder.adjust(1)
    
    await message.answer(
        "⚠️ **DANGER ZONE** ⚠️\n\n"
        "Are you sure you want to completely reset your account? "
        "This will permanently delete all your transactions, categories, and keywords, "
        "and restore the default categories.",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "confirm_reset")
async def cb_confirm_reset(query: CallbackQuery) -> None:
    from bot.db.crud import reset_user_data
    await reset_user_data(query.from_user.id)
    await query.message.edit_text("✅ Your account has been completely reset to factory settings.")

@router.callback_query(F.data == "cancel_reset")
async def cb_cancel_reset(query: CallbackQuery) -> None:
    await query.message.edit_text("Reset cancelled. Your data is safe.")
