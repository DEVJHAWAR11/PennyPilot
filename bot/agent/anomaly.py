import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot
from langchain_core.messages import HumanMessage

from bot.db.crud import get_all_users
from bot.agent.graph import init_agent

# The anomaly prompt instructs the agent to reuse its existing tools (query_transactions, get_category_totals)
# to compare the last 7 days of spending with the 30 days prior.
ANOMALY_SYSTEM_PROMPT = """You are an autonomous anomaly detection agent for PennyPilot. 
Your job is to check the user's spending data and send a proactive alert ONLY IF you find a statistical anomaly.

Rules:
1. Use the `get_category_totals` tool to get spending per category for the LAST 7 DAYS.
2. Use the same tool to get spending per category for the 30 DAYS PRIOR TO THAT (i.e. days -37 to -7).
3. Compare the 7-day spend to the 30-day average. 
4. THRESHOLD: A genuine anomaly occurs if a category's 7-day spend is MORE THAN 50% HIGHER than the prorated weekly average of the prior 30-day period. (i.e. 7-day spend > 1.5 * (30-day spend * 7 / 30)). Ignore tiny amounts (under ₹500).
5. If NO anomalies are found across any categories, you must output exactly and only: `[NO_ANOMALIES]`
6. If an anomaly IS found, you must output exactly: `[ANOMALY] <Your short, conversational warning message to the user>`
   Example: `[ANOMALY] I noticed a spike in your 'Entertainment' spending! You've spent ₹8,500 in the last 7 days, which is much higher than your usual weekly average of ₹1,200.`
7. NEVER guess or hallucinate numbers. Use the exact output from the tools.

Check for anomalies now. Output only the requested format.
"""

async def check_user_anomalies(bot: Bot) -> None:
    """
    Scheduled job: Iterates through all users, runs the LangGraph anomaly agent,
    and sends a proactive message if an anomaly is flagged.
    """
    logging.info("Starting scheduled anomaly checks...")
    users = await get_all_users()
    
    agent = await init_agent()
    if not agent:
        logging.error("Cannot run anomaly check: LangGraph agent not initialized.")
        return

    today = datetime.now()
    end_7d = today.strftime("%Y-%m-%d")
    start_7d = (today - timedelta(days=6)).strftime("%Y-%m-%d")
    end_30d = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    start_30d = (today - timedelta(days=36)).strftime("%Y-%m-%d")

    # Inject the date context into the prompt so the agent doesn't have to guess today's date
    prompt = ANOMALY_SYSTEM_PROMPT + f"\nContext:\nUser ID: {{user_id}}\nLast 7 days: {start_7d} to {end_7d}\nPrior 30 days: {start_30d} to {end_30d}"

    for user in users:
        telegram_id = user["telegram_id"]
        
        # We start a fresh thread for the anomaly check so it doesn't pollute the user's conversational memory
        thread_id = f"anomaly_check_{telegram_id}_{today.strftime('%Y%m%d')}"
        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 5}
        
        user_prompt = prompt.format(user_id=telegram_id)
        inputs = {"messages": [HumanMessage(content=user_prompt)]}
        
        logging.info(f"Running anomaly check for user {telegram_id}...")
        
        try:
            # We use stream to wait for the final completion
            final_response = None
            async for chunk in agent.astream(inputs, config=config, stream_mode="values"):
                final_response = chunk["messages"][-1].content
                
            if final_response:
                if "[ANOMALY]" in final_response:
                    # Extract the message
                    warning = final_response.replace("[ANOMALY]", "").strip()
                    logging.info(f"Anomaly found for user {telegram_id}: {warning}")
                    
                    # Proactively message the user!
                    await bot.send_message(
                        chat_id=telegram_id,
                        text=f"⚠️ *Proactive Spending Alert*\n\n{warning}",
                        parse_mode="Markdown"
                    )
                elif "[NO_ANOMALIES]" in final_response:
                    logging.info(f"No anomalies for user {telegram_id}.")
                else:
                    logging.warning(f"Unexpected anomaly output for {telegram_id}: {final_response}")
                    
        except Exception as e:
            logging.error(f"Error checking anomalies for user {telegram_id}: {e}")
            
        # Add a delay between users to avoid hammering the LLM API and hitting rate limits
        await asyncio.sleep(10)

    logging.info("Scheduled anomaly checks completed.")
