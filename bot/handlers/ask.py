"""
Handler for the /ask command to query the LangGraph financial agent.
"""
import re
from aiogram import Router
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command

from bot.agent.graph import ask_agent

router = Router()

@router.message(Command("ask"))
async def cmd_ask(message: Message) -> None:
    """Explicitly ask the AI agent a financial question."""
    
    # Guarantee user exists in DB
    from bot.db.crud import get_or_create_user
    await get_or_create_user(message.from_user.id)
    
    # Extract the question by stripping the "/ask" prefix
    question = message.text.replace("/ask", "", 1).strip()
    
    if not question:
        await message.answer(
            "Please provide a question after the command. 🤓\n"
            "Example: `/ask how much did I spend on food this month?`",
            parse_mode="Markdown"
        )
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    try:
        reply = await ask_agent(message.from_user.id, question)
        
        if "[CHART_PATH:" in reply:
            match = re.search(r"\[CHART_PATH:(.*?)\]", reply)
            if match:
                chart_path = match.group(1)
                clean_reply = re.sub(r"\[CHART_PATH:.*?\]", "", reply).strip()
                photo = FSInputFile(chart_path)
                await message.answer_photo(photo=photo, caption=clean_reply)
            else:
                await message.answer(reply)
        else:
            await message.answer(reply)
            
    except Exception as e:
        await message.answer(f"An error occurred while asking the agent: {e}")
