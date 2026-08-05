import asyncio
import os
from datetime import datetime, timedelta
import random

from aiogram import Bot
from bot.config import BOT_TOKEN
from bot.db.schema import init_db
from bot.db.crud import get_or_create_user, get_categories, add_transaction, update_month_start_day, get_all_users
from bot.agent.summary import send_monthly_summaries
from bot.utils.dates import get_past_financial_months

async def main():
    if not BOT_TOKEN:
        print("BOT_TOKEN is missing. Cannot test summary agent.")
        return

    # 1. Initialize the database
    await init_db()
    
    users = await get_all_users()
    if not users:
        print("No users found in database to test with.")
        return
        
    test_user = users[0]
    telegram_id = test_user["telegram_id"]
    print(f"Testing monthly summary for user {telegram_id}...")

    # Force the month start day to be TODAY so that the summary triggers
    today = datetime.now().date()
    await update_month_start_day(telegram_id, today.day)
    print(f"Set month_start_day to {today.day}")

    categories = await get_categories(telegram_id)
    expense_cats = [c for c in categories if c["type"] == "expense"]
    if len(expense_cats) < 2:
        print("Not enough expense categories to test with.")
        return

    cat1 = expense_cats[0]
    cat2 = expense_cats[1]

    # 2. Seed data for the just-closed month (index 1) and prior month (index 2)
    past_months = get_past_financial_months(today, today.day, count=3)
    closed_start, closed_end = past_months[1]
    prior_start, prior_end = past_months[2]
    
    print(f"Seeding prior month data: {prior_start} to {prior_end}")
    await add_transaction(telegram_id, 2000, "expense", cat1["id"], "Prior Exp 1", (prior_start + timedelta(days=2)).strftime("%Y-%m-%d"))
    await add_transaction(telegram_id, 1000, "expense", cat2["id"], "Prior Exp 2", (prior_start + timedelta(days=10)).strftime("%Y-%m-%d"))

    print(f"Seeding closed month data: {closed_start} to {closed_end}")
    await add_transaction(telegram_id, 4500, "expense", cat1["id"], "Closed Exp 1", (closed_start + timedelta(days=5)).strftime("%Y-%m-%d"))
    await add_transaction(telegram_id, 3000, "expense", cat2["id"], "Closed Exp 2", (closed_start + timedelta(days=15)).strftime("%Y-%m-%d"))
    
    print("Data seeded. Triggering summary agent...")
    
    # 3. Trigger summary check
    bot = Bot(token=BOT_TOKEN)
    # We pass the user ID as force_run_for_user_id just in case, though we set month_start_day to today anyway
    await send_monthly_summaries(bot, force_run_for_user_id=telegram_id)
    
    print("Summary agent finished. Check Telegram for a proactive message!")
    await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
