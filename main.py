"""
PennyPilot — Telegram Expense Tracker Bot

Entry point. Creates the Bot and Dispatcher, registers handler routers,
and starts polling for updates from Telegram.
"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher

from bot.config import BOT_TOKEN
from bot.db.schema import init_db
from bot.handlers.commands import router as commands_router
from bot.handlers.logging import router as logging_router


def main() -> None:
    """Set up logging, build the bot, register routers, and start polling."""

    # Configure logging so we can see what's happening in the console
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )

    # Validate that the bot token is set
    if not BOT_TOKEN:
        logging.error(
            "BOT_TOKEN is not set. "
            "Copy .env.example to .env and fill in your Telegram bot token."
        )
        sys.exit(1)

    # Create the bot and dispatcher
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Register handler routers
    dp.include_router(commands_router)
    dp.include_router(logging_router)

    # Initialize the database (creates tables if they don't exist)
    asyncio.run(init_db())
    logging.info("Database initialized.")

    # Start polling (blocks until stopped with Ctrl+C)
    logging.info("PennyPilot is starting...")
    asyncio.run(dp.start_polling(bot))


if __name__ == "__main__":
    main()
