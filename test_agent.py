import asyncio
from bot.agent.graph import ask_agent, close_agent

async def main():
    # User 999999999 is our test user from earlier (id=3 in the db)
    # Wait, the tool expects `user_id`, which is the database id, NOT the telegram_id!
    # Let me check crud.py: `get_transactions_for_period(telegram_id: int, start_date: str, end_date: str)`
    # Ah! In crud.py, almost all functions expect `telegram_id: int`, NOT the internal `user_id`.
    # Let's verify this.
    
    print("Asking agent about balance...")
    reply = await ask_agent(999999999, "What is my balance between 2026-08-01 and 2026-08-31?")
    print("Agent reply:\n", reply)
    
    print("\nAsking agent for a chart...")
    reply2 = await ask_agent(999999999, "Generate a pie chart of my expenses between 2026-08-01 and 2026-08-31.")
    print("Agent reply:\n", reply2)
    
    await close_agent()

if __name__ == "__main__":
    asyncio.run(main())
