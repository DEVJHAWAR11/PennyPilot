"""
PennyPilot — Telegram Expense Tracker Bot

Entry point. Creates the Bot and Dispatcher, registers handler routers,
and starts polling for updates from Telegram.
"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from bot.config import BOT_TOKEN
from bot.db.schema import init_db
from bot.handlers.commands import router as commands_router
from bot.handlers.categories import router as categories_router
from bot.handlers.logging import router as logging_router
from bot.handlers.voice import router as voice_router
from bot.handlers.photo import router as photo_router
from bot.handlers.stats import router as stats_router
from bot.handlers.export import router as export_router
from bot.handlers.recent import router as recent_router
from bot.handlers.ask import router as ask_router


async def setup_bot_commands(bot: Bot):
    """Set up the Telegram bot menu commands."""
    commands = [
        BotCommand(command="start", description="Start or restart the bot"),
        BotCommand(command="balance", description="View current month balance"),
        BotCommand(command="stats", description="View past months breakdown"),
        BotCommand(command="categories", description="Manage categories"),
        BotCommand(command="export", description="Export to CSV or PDF"),
        BotCommand(command="recent", description="View recent transactions"),
        BotCommand(command="ask", description="Ask the AI a financial question"),
        BotCommand(command="settings", description="Change bot settings"),
        BotCommand(command="reset", description="Wipe all data"),
        BotCommand(command="help", description="Show help menu")
    ]
    await bot.set_my_commands(commands)


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
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # Register handler routers
    dp.include_router(commands_router)
    dp.include_router(categories_router)
    dp.include_router(voice_router)
    dp.include_router(photo_router)
    dp.include_router(stats_router)
    dp.include_router(export_router)
    dp.include_router(recent_router)
    dp.include_router(ask_router)
    dp.include_router(logging_router)

    async def on_startup() -> None:
        logging.info("PennyPilot is starting...")
        await init_db()
        await setup_bot_commands(bot)
        logging.info("Database initialized and commands set.")
        
        # Start the background anomaly detection scheduler
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from bot.agent.anomaly import check_user_anomalies
        scheduler = AsyncIOScheduler()
        # Schedule it to run daily at 9:00 AM UTC
        scheduler.add_job(check_user_anomalies, 'cron', hour=9, minute=0, args=[bot])
        scheduler.start()
        logging.info("APScheduler started (anomaly checks run at 09:00 UTC).")

    dp.startup.register(on_startup)

    # Start polling (blocks until stopped with Ctrl+C)
    logging.info("PennyPilot is starting polling...")
    asyncio.run(dp.start_polling(bot))


if __name__ == "__main__":
    main()
