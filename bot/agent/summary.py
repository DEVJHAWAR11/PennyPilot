import asyncio
import logging
from datetime import datetime

from aiogram import Bot
from langchain_core.messages import HumanMessage

from bot.db.crud import get_all_users
from bot.agent.graph import init_agent
from bot.utils.dates import get_past_financial_months

SUMMARY_SYSTEM_PROMPT = """You are PennyPilot's monthly summary agent.
Your job is to provide the user with a concise, insightful summary of their spending for the just-closed financial month.

Rules:
1. You will be provided with the dates for the JUST CLOSED month and the PRIOR month.
2. Use `get_cat_totals` and `get_bal` to fetch data for the closed month.
3. Use the same tools to fetch data for the prior month to make a comparison.
4. Output a natural-language recap including:
   - Total expenses for the month.
   - Top 1 or 2 spending categories.
   - A brief comparison to the prior month (e.g. "You spent ₹2000 more this month").
   - One concrete, data-backed observation (e.g. "Your dining out expenses doubled").
5. DO NOT use generic filler text like "Here is your summary". Start directly with a friendly greeting and the facts.
6. Format your output with Markdown (bolding key numbers).
7. NEVER hallucinate numbers. If the tools return no data, say "You had no recorded transactions for this month."
"""

async def send_monthly_summaries(bot: Bot, force_run_for_user_id: int = None) -> None:
    """
    Scheduled job: Iterates through users, checks if today is their month_start_day,
    and sends them a monthly AI summary if so.
    force_run_for_user_id can be used in testing to bypass the date check.
    """
    logging.info("Starting scheduled monthly summary checks...")
    users = await get_all_users()
    
    agent = await init_agent()
    if not agent:
        logging.error("Cannot run monthly summary: LangGraph agent not initialized.")
        return

    today = datetime.now().date()

    for user in users:
        telegram_id = user["telegram_id"]
        start_day = user.get("month_start_day", 1)
        
        # Check if today is the start of a new financial month for this user, OR if we're forcing a run
        if force_run_for_user_id != telegram_id and today.day != start_day:
            continue
            
        logging.info(f"Generating monthly summary for user {telegram_id}...")
        
        # We need the dates for the just-closed month (index 1) and the prior month (index 2)
        # get_past_financial_months returns: [0: current, 1: closed, 2: prior_to_closed, ...]
        past_months = get_past_financial_months(today, start_day, count=3)
        
        closed_start, closed_end = past_months[1]
        prior_start, prior_end = past_months[2]
        
        context = (
            f"Context:\nUser ID: {telegram_id}\n"
            f"Just Closed Month: {closed_start.strftime('%Y-%m-%d')} to {closed_end.strftime('%Y-%m-%d')}\n"
            f"Prior Month: {prior_start.strftime('%Y-%m-%d')} to {prior_end.strftime('%Y-%m-%d')}"
        )
        
        user_prompt = SUMMARY_SYSTEM_PROMPT + "\n\n" + context
        
        thread_id = f"monthly_summary_{telegram_id}_{closed_start.strftime('%Y%m')}"
        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 5}
        inputs = {"messages": [HumanMessage(content=user_prompt)]}
        
        try:
            final_response = None
            async for chunk in agent.astream(inputs, config=config, stream_mode="values"):
                final_response = chunk["messages"][-1].content
                
            if final_response:
                logging.info(f"Summary generated for {telegram_id}")
                
                await bot.send_message(
                    chat_id=telegram_id,
                    text=f"📅 *Monthly Financial Summary*\n\n{final_response}",
                    parse_mode="Markdown"
                )
            else:
                logging.warning(f"No response generated for monthly summary of {telegram_id}")
                
        except Exception as e:
            logging.error(f"Error generating summary for user {telegram_id}: {e}")
            
        # Add a delay between users to avoid hammering the LLM API and hitting rate limits
        await asyncio.sleep(10)

    logging.info("Scheduled monthly summaries completed.")
