import os
import asyncio
from contextlib import AsyncExitStack

from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools

from dotenv import load_dotenv
load_dotenv()

_global_exit_stack = None
_global_agent = None

async def init_agent():
    global _global_exit_stack, _global_agent
    
    if _global_agent is not None:
        return _global_agent

    PYTHON_EXE = os.path.join(os.getcwd(), "venv", "Scripts", "python.exe")
    if not os.path.exists(PYTHON_EXE):
        PYTHON_EXE = "python"

    server_params = StdioServerParameters(
        command=PYTHON_EXE,
        args=["-m", "bot.agent.mcp_server"],
        env={"PYTHONPATH": os.getcwd(), **os.environ}
    )
    
    _global_exit_stack = AsyncExitStack()
    read, write = await _global_exit_stack.enter_async_context(stdio_client(server_params))
    
    session = await _global_exit_stack.enter_async_context(ClientSession(read, write))
    await session.initialize()
    
    tools = await load_mcp_tools(session)
    
    # We use llama-3.3-70b-versatile for tool calling
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    
    # Compress system prompt to extreme brevity
    system_prompt = (
        "PennyPilot finance AI. Use MCP tools.\n"
        "RULES:\n"
        "1.No guessing nums. Use tool output.\n"
        "2.Pass `uid`.\n"
        "3.Chart: return `[CHART_PATH:<filepath>]`.\n"
        "4.Use `log_txn` for expenses.\n"
        "5.Use ₹, not $.\n"
        "6.Confirm: '✅ ₹400-Swiggy(Food)'.\n"
        "7.List: '₹45-Zomato(Food)'.\n"
        "8.Edits: use del_txn/upd_cat.\n"
        "9.EXTREME BREVITY."
    )
    
    from langgraph.checkpoint.memory import MemorySaver
    from langchain_core.messages import trim_messages, SystemMessage
    
    memory = MemorySaver()
    
    # Trim to the last 20 messages to ensure tool call history and the initial prompt are preserved
    trimmer = trim_messages(
        max_tokens=20,
        strategy="last",
        token_counter=len,
        include_system=True,
        allow_partial=False,
        start_on="human"
    )
    
    def custom_modifier(state):
        trimmed = trimmer.invoke(state["messages"])
        return [SystemMessage(content=system_prompt)] + trimmed
        
    _global_agent = create_react_agent(llm, tools=tools, checkpointer=memory, prompt=custom_modifier)
    return _global_agent

async def close_agent():
    global _global_exit_stack
    if _global_exit_stack is not None:
        await _global_exit_stack.aclose()
        _global_exit_stack = None

async def ask_agent(user_id: int, question: str) -> str:
    agent = await init_agent()
    
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    
    # We inject the user_id and current date into the prompt
    prompt = f"The user (user_id={user_id}) asks: {question}\n\n[System Context: Today's date is {today}]"
    
    # Pass a configurable thread_id so LangGraph maintains memory for this user's conversation
    response = await agent.ainvoke(
        {"messages": [("user", prompt)]},
        config={"configurable": {"thread_id": str(user_id)}}
    )
    
    content = response["messages"][-1].content
    
    # Clean up any hallucinated XML/HTML tags (like <function=...>) from Groq to prevent Telegram crashes
    import re
    cleaned_content = re.sub(r"<[^>]+>", "", content).strip()
    
    return cleaned_content if cleaned_content else "I couldn't process that properly."
