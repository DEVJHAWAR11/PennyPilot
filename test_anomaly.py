import asyncio
import os
from datetime import datetime, timedelta

from aiogram import Bot
from bot.config import BOT_TOKEN
from bot.db.schema import init_db
from bot.db.crud import get_or_create_user, get_categories, add_transaction
from bot.agent.anomaly import check_user_anomalies

async def main():
    if not BOT_TOKEN:
        print("BOT_TOKEN is missing. Cannot test anomaly agent.")
        return

    # 1. Initialize the database
    await init_db()
    
    # We need a user to test against. Let's ask the user for their ID,
    # or just use the first user in the DB.
    from bot.db.crud import get_all_users
    users = await get_all_users()
    if not users:
        print("No users found in database to test with.")
        return
        
    test_user = users[0]
    telegram_id = test_user["telegram_id"]
    print(f"Testing anomaly detection for user {telegram_id}...")

    # Ensure the user exists and has categories
    await get_or_create_user(telegram_id)
    categories = await get_categories(telegram_id)
    
    ent_cat = next((c for c in categories if c["name"] == "Entertainment"), None)
    if not ent_cat:
        print("Could not find 'Entertainment' category to test with.")
        return

    cat_id = ent_cat["id"]

    today = datetime.now()
    # 2. Seed normal data (e.g. ₹500 every 5 days for the last 30 days)
    print("Seeding normal historical data...")
    for i in range(10, 35, 5):
        txn_date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        await add_transaction(telegram_id, 500, "expense", cat_id, f"Normal {i}", txn_date)
        
    # Historical total = 5 * 500 = 2500 over ~30 days. Weekly average = ~580.
    
    # 3. Seed an anomalous spike (e.g. 15,000 yesterday)
    print("Seeding anomalous spike (15,000 yesterday)...")
    spike_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    await add_transaction(telegram_id, 15000, "expense", cat_id, "Big Party", spike_date)
    
    print("Data seeded. Triggering anomaly agent...")
    
    # 4. Trigger anomaly check
    bot = Bot(token=BOT_TOKEN)
    await check_user_anomalies(bot)
    
    print("Anomaly agent finished. Check Telegram for a proactive message!")
    await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
