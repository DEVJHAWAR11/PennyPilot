import asyncio
from bot.agent.mcp_server import query_transactions, get_category_totals, get_balance, generate_chart
from bot.db.schema import init_db
from bot.db.crud import get_or_create_user, add_transaction

async def main():
    await init_db()
    
    # 1. Get or create a test user
    # For testing, we use a dummy telegram ID
    test_id = 999999999
    user = await get_or_create_user(test_id)
    print(f"Test user: {user['id']}")
    
    from bot.db.crud import get_categories
    cats = await get_categories(test_id)
    cat_id = cats[0]['id']
    
    # Add a test transaction
    await add_transaction(test_id, 50.0, "expense", cat_id, "Test groceries", "2026-08-05")
    
    print("\n--- Testing query_transactions ---")
    txns = await query_transactions(test_id, "2026-08-01", "2026-08-31")
    print(f"Found {len(txns)} transactions")
    
    print("\n--- Testing get_category_totals ---")
    totals = await get_category_totals(test_id, "2026-08-01", "2026-08-31")
    print(f"Totals: {totals}")
    
    print("\n--- Testing get_balance ---")
    balance = await get_balance(test_id, "2026-08-01", "2026-08-31")
    print(f"Balance: {balance}")
    
    print("\n--- Testing generate_chart ---")
    chart_path = await generate_chart(test_id, "2026-08-01", "2026-08-31")
    print(f"Chart saved to: {chart_path}")

if __name__ == "__main__":
    asyncio.run(main())
