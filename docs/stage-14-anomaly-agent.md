# Stage 14: Autonomous Anomaly Detection Agent

## Features implemented in this stage
- Added `apscheduler` to the project to run scheduled background jobs.
- Implemented `bot/agent/anomaly.py`, an autonomous scheduled task that checks for spending spikes across all users.
- Updated `bot/db/crud.py` with `get_all_users()` to fetch the user list for the anomaly agent.
- Integrated `AsyncIOScheduler` into the `main.py` entrypoint, scheduling the anomaly check to run daily at 9:00 AM UTC.
- Created `test_anomaly.py` to seed data and manually verify the unprompted proactive messaging.

## Commands run
```bash
pip install apscheduler
echo apscheduler==3.11.3 >> requirements.txt
python test_anomaly.py
```

## Code built

### `bot/db/crud.py`
```python
async def get_all_users() -> list[dict]:
    """Retrieve all users to process scheduled tasks like anomaly detection."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
```
**Why:** To run a daily scan, the bot needs to know which Telegram user IDs to check. This simple SQL function fetches all registered users from the database.

### `bot/agent/anomaly.py`
```python
import logging
from datetime import datetime, timedelta
from aiogram import Bot
from langchain_core.messages import HumanMessage
from bot.db.crud import get_all_users
from bot.agent.graph import init_agent

ANOMALY_SYSTEM_PROMPT = """You are an autonomous anomaly detection agent for PennyPilot. 
Your job is to check the user's spending data and send a proactive alert ONLY IF you find a statistical anomaly.
...
"""

async def check_user_anomalies(bot: Bot) -> None:
    # Logic to fetch users, initialize agent, format prompt with dates,
    # invoke the agent via astream, and send unprompted alerts if anomalies are found.
```
**Why:** This script contains the core agent logic. We use LangGraph's agent to reason over the user's data. Rather than hardcoding SQL queries for a 7-day vs 30-day average, we simply prompt the agent to use its existing MCP tools (like `get_category_totals`). It computes the averages, determines if there is an anomaly based on our defined threshold (50% higher than the prorated weekly average), and outputs a warning. If a warning is generated, the bot uses `bot.send_message` to push it to the user proactively. 

### `main.py`
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bot.agent.anomaly import check_user_anomalies

# Inside on_startup:
scheduler = AsyncIOScheduler()
scheduler.add_job(check_user_anomalies, 'cron', hour=9, minute=0, args=[bot])
scheduler.start()
```
**Why:** `APScheduler` is the standard library in Python for running scheduled tasks asynchronously. We attach it to `aiogram`'s `on_startup` hook so the schedule runs continuously while the bot is polling.

## Interview Q&A

**Q: Why is this considered agentic and not just a cron job with an if-statement?**
A: While the trigger (APScheduler) is a traditional cron job, the logic itself is agentic. Instead of writing rigid SQL queries to calculate standard deviations and writing `if average > X`, we instruct the LangGraph agent to use its toolset (`get_category_totals`) to retrieve the data and make the judgment call based on our instructions. This allows the agent to reason flexibly over the data and generate a natural, conversational warning message explaining the spike, rather than sending a robotic, hardcoded string. 

**Q: What would happen if a user has zero spending in the last 30 days?**
A: The agent relies on the data provided by the MCP tools. If there is no spending in the prior 30 days, the prorated weekly average is zero. If the user then spends a large amount, the 7-day spend will exceed the threshold (which handles the divide-by-zero gracefully because the agent uses numerical reasoning). We also instructed the agent to ignore tiny amounts (under ₹500) to prevent alerts for trivial purchases triggering an "infinite percentage increase" anomaly.

**Q: How do you prevent the anomaly agent's conversation from interfering with the user's normal chat history?**
A: LangGraph uses `thread_id` to separate conversation contexts. In `anomaly.py`, we generate a unique `thread_id` specifically for the anomaly check (e.g., `anomaly_check_<user_id>_<date>`). This ensures the background reasoning is sandboxed and does not pollute the user's primary chat memory.
