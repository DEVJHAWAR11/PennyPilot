# Stage 13: LangGraph Query Agent

## Features implemented in this stage
- Created `bot/agent/mcp_server.py` using FastMCP to expose database operations (query, chart, log, edit, delete) as standardized MCP tools over stdio.
- Created `bot/agent/graph.py` to compile a LangGraph `create_react_agent` powered by Groq (`llama-3.3-70b-versatile`).
- Added conversational memory to the agent using LangGraph's `MemorySaver`, keyed to the user's Telegram ID, so the bot remembers context across messages.
- Added `delete_transaction_tool` and `update_transaction_category_tool` to the MCP server so the agent can autonomously fix mistakes.
- Implemented aggressive token optimizations by compressing the System Prompt and MCP tool docstrings to drastically reduce input token overhead.
- Wired the agent as an implicit fallback in `bot/handlers/logging.py` (for complex logging like "I spent 300 on food") and as an explicit query handler.
- Configured the agent to intercept `[CHART_PATH:...]` strings and return native Telegram images.

## Commands run
```bash
.\venv\Scripts\pip install langchain-groq langgraph mcp fastmcp langchain-mcp-adapters
```

## Code built

**`bot/agent/mcp_server.py`**
This file defines our Model Context Protocol (MCP) server. Instead of giving the LLM raw Python functions, we wrap our database CRUD operations (`get_transactions_for_period`, `add_transaction`, `delete_transaction`, etc.) in `@mcp.tool()` decorators. This standardizes the inputs/outputs. We intentionally kept the `"""docstrings"""` extremely brief here to save input tokens, because LangGraph sends these docstrings to the LLM on every single query.

**`bot/agent/graph.py`**
This is the "brain" of the bot. We establish an `AsyncExitStack` to keep the MCP subprocess running persistently (warm start). We compile a LangGraph agent using `create_react_agent`. We pass it the MCP tools, the Groq Llama 3.3 70B model, and a strictly compressed `system_prompt`. We also attach a `MemorySaver()` checkpointer here, passing `{"configurable": {"thread_id": telegram_id}}` during invocation, so the agent remembers what you said previously.

**`bot/handlers/logging.py`**
We updated our core deterministic parser fallback. If the user types a sentence with more than 2 words (e.g., "I spent 45 on swiggy"), our regex parser skips it and routes it directly to `ask_agent` from `graph.py`. The agent parses the natural language, picks the right category, uses the MCP tool to log it, and replies.

**`bot/handlers/ask.py`**
This handles the explicit `/ask` command. It takes the user's query and passes it to `ask_agent`. If the agent returns a special `[CHART_PATH:...]` string, this handler intercepts it, uses aiogram's `FSInputFile` to read the PNG from disk, and sends it as a native Telegram photo to the user.

## Interview Q&A

**Q: Why use LangGraph for this agent instead of just writing a custom loop to handle Groq's tool calls?**
A: A custom loop works for trivial tasks, but LangGraph provides a robust framework for managing complex state, recovering from LLM errors, handling cyclic execution paths, and memory checkpointing. It abstracts the boilerplate of managing tool execution histories while keeping the orchestration highly deterministic. (Reference: `bot/agent/graph.py`)

**Q: Why do we maintain a global MCP session in `graph.py` rather than opening a new subprocess on every query?**
A: Spinning up a new Python subprocess to run the MCP server for every single incoming Telegram message adds massive latency and burns CPU. By maintaining a global `AsyncExitStack`, we keep the MCP server "warm", meaning queries resolve near-instantly since the subprocess is already running.

**Q: How does the LangGraph agent handle returning charts (images) to the user?**
A: Since LLMs and MCP operate over text (JSON-RPC), the `generate_chart` MCP tool saves the chart locally and returns a string like `[CHART_PATH:/temp/chart.png]`. We instructed the LLM in its prompt to output this string. The Telegram handler uses regex to detect this tag, reads the image file using `FSInputFile`, and sends a native Telegram photo. (Reference: `bot/handlers/logging.py`)

**Q: What happens if the agent hallucinates a tool call or the tool fails?**
A: LangGraph's ReAct agent implementation naturally handles ToolMessage errors by returning the error string back to the LLM in the next node, allowing the model to self-correct and try again. If it fails repeatedly, the agent will naturally inform the user it cannot access the data, preventing crashes.

**Q: Why did you choose the `llama-3.3-70b-versatile` model over a smaller 8B model?**
A: We initially tested an 8B model to save tokens, but smaller models struggle with complex JSON schema adherence for MCP tool calls, causing routing errors. The Llama 3.3 70B model via Groq offers near-instant latency and high-tier reasoning natively tuned for structured tool calling, which is strictly required for the ReAct architecture. (Reference: `bot/agent/graph.py`)

**Q: How do we prevent the LLM from hallucinating financial numbers?**
A: We provided a highly explicit system prompt: *"Never guess numbers. Use exact tool outputs."* Since the LLM is only exposed to the exact data returned by the tools, it grounds its natural language generation entirely on the structured output of the SQL queries.

**Q: Why is the LangGraph agent used as a fallback rather than processing every single message?**
A: Processing every single message through an LLM is expensive and non-deterministic. For simple actions like logging "45 groceries", our regex-based deterministic parser (Stage 3) is 100% accurate and instant. We only invoke the LLM for complex read queries or long sentences where natural language understanding is necessary. (Reference: `bot/handlers/logging.py`)

**Q: How did you optimize the input token costs for the LLM?**
A: We aggressively compressed the `system_prompt` by removing conversational padding. More importantly, we shortened all the `"""docstrings"""` in `mcp_server.py`. Because FastMCP sends the tool definitions to the LLM on every query, dense 1-line docstrings drastically reduce the baseline input tokens per request.

**Q: Why add `MemorySaver` to the LangGraph agent?**
A: Without memory, the LLM treats every message as a brand new conversation. By using `MemorySaver` keyed to the `telegram_id`, the agent can handle follow-up queries like "Delete that last expense" or "How much of that was on food?", giving it conversational context. (Reference: `bot/agent/graph.py`)

**Q: How does the agent know how to edit or delete a transaction?**
A: We added `delete_transaction_tool` and `update_transaction_category_tool` to the MCP server. The LLM's prompt instructs it to first query transactions to find the exact Database ID, and then pass that ID into the update/delete tools, allowing autonomous error correction. (Reference: `bot/agent/mcp_server.py`)

**Q: Why use `stdio` transport instead of `SSE` (Server-Sent Events) for the MCP server?**
A: The `stdio` transport runs the MCP server as a local subprocess, communicating directly via standard input and output streams. This is ideal because our agent and tools live on the same physical server instance. It avoids the overhead of managing a separate HTTP server and port conflicts.

**Q: How does `FastMCP` simplify the creation of an MCP server?**
A: `FastMCP` acts as a high-level wrapper that abstracts away the boilerplate of manually registering JSON-RPC request handlers and schema definitions. By decorating a standard Python function with `@mcp.tool()`, it automatically infers the input schema from type hints.

**Q: What is the risk of using LLMs for database modification?**
A: The risk is destructive actions (like deleting the wrong transaction). We mitigate this by requiring exact IDs for modifications, heavily constraining the tool schemas, and relying on a highly capable 70B model that can accurately read the transaction list before invoking the delete tool.

**Q: How do we handle categories that don't exist when the LLM tries to log a transaction?**
A: Inside the `log_transaction` MCP tool, we query the database for valid categories. If the LLM passes an invalid category, the Python tool returns an error string containing the valid list back to the LLM. The LLM reads this error and self-corrects on the next loop iteration. (Reference: `bot/agent/mcp_server.py`)

**Q: Why enforce strict brevity in the LLM's responses?**
A: LLMs inherently want to be conversational (e.g., "I have successfully logged your transaction! Is there anything else?"). This wastes output tokens. By explicitly commanding "EXTREME BREVITY: Output raw data/confirmations only", we save output tokens (and thus cost/latency) on every single response. (Reference: `bot/agent/graph.py`)
