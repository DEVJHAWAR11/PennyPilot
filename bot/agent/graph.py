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
    
    system_prompt = (
        "You are PennyPilot, a helpful financial assistant.\n"
        "You have access to MCP tools to query transactions, balances, totals, and generate charts.\n"
        "IMPORTANT RULES:\n"
        "1. Only answer using the exact numbers returned by the tools. Do not hallucinate or guess numbers.\n"
        "2. If you cannot find the answer via tools, say so.\n"
        "3. You must ALWAYS use the provided `user_id` argument for all tool calls.\n"
        "4. If you generate a chart, the tool will return a filepath. Tell the user you've generated the chart and include the filepath strictly formatted as `[CHART_PATH:<filepath>]` in your final text. The system will handle parsing it.\n"
    )
    
    _global_agent = create_react_agent(llm, tools=tools, prompt=system_prompt)
    return _global_agent

async def close_agent():
    global _global_exit_stack
    if _global_exit_stack is not None:
        await _global_exit_stack.aclose()
        _global_exit_stack = None

async def ask_agent(user_id: int, question: str) -> str:
    agent = await init_agent()
    
    # We inject the user_id into the prompt so the agent knows who to query for
    prompt = f"The user (user_id={user_id}) asks: {question}"
    
    response = await agent.ainvoke({"messages": [("user", prompt)]})
    return response["messages"][-1].content
