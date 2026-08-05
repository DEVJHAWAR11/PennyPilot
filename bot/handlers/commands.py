"""
Command handlers — /start and /help for the bot skeleton.
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    """Greet the user and explain what the bot does."""
    await message.answer(
        "Hey! 👋 I'm PennyPilot — your personal expense tracker.\n\n"
        "Send me an amount and what it was for, like:\n"
        "• `45 groceries`\n"
        "• `2500 salary`\n"
        "• `200 beer 2025-01-15`\n\n"
        "I'll log it instantly. You can also send a 🎙 voice note "
        "or a 📸 receipt photo and I'll figure it out.\n\n"
        "Type /help to see everything I can do.",
        parse_mode="Markdown",
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Show available commands."""
    await message.answer(
        "📖 *Here's what I can do:*\n\n"
        "*Log a transaction* — just send a message like `45 groceries` "
        "or `2500 salary`.\n\n"
        "*Commands:*\n"
        "/start — Welcome message\n"
        "/help — This help menu\n\n"
        "🚧 More commands coming soon — categories, balance, stats, "
        "charts, exports, and more!",
        parse_mode="Markdown",
    )
