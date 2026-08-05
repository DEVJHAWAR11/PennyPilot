# Stage 12: MCP Server (Expose Financial Tools)

## Features implemented in this stage
- Created `bot/agent/mcp_server.py` containing a `FastMCP` server named "PennyPilot".
- Wrapped the existing SQL operations in `bot/db/crud.py` into four agent-accessible tools:
  - `query_transactions`: Filters transactions by date range and optionally by category.
  - `get_category_totals`: Aggregates expenses by category for a date range.
  - `get_balance`: Calculates income, expenses, and net balance for a date range.
  - `generate_chart`: Reuses the matplotlib charting logic to generate a pie chart and returns the filepath.
- Wrote `test_mcp_direct.py` to directly verify the `@mcp.tool` decorated functions work as expected without booting up an LLM.

## Commands run
```bash
.\venv\Scripts\python test_mcp_direct.py
```
*(Successfully verified the tools returned accurate data and created a temporary chart image).*

## Interview Q&A

**Q: Why do we wrap existing `bot/db/crud.py` functions instead of writing SQL queries directly inside the MCP tool definitions?**
A: This enforces the DRY (Don't Repeat Yourself) principle and ensures business logic consistency. If we ever change the database schema, table structures, or how a "balance" is calculated, we only have to update it in one place (`crud.py`). The MCP server acts strictly as an API presentation layer, not a business logic layer.

**Q: In the `generate_chart` tool, why do we return a file path instead of returning the raw image bytes to the agent?**
A: LLMs process text and struggle to handle or pass around raw binary buffers effectively over JSON-RPC. By saving the generated chart to a temporary file locally on the server and returning the absolute file path as a string, the LLM can easily reason about it and hand that file path back to the Telegram bot, which can then read the file and send the photo.

**Q: What would happen if a user asks for data from a category that doesn't exist?**
A: The `query_transactions` tool optionally filters by category name. If a nonexistent category is passed, it simply returns an empty list `[]`. The LangGraph agent will see this empty list and can naturally respond to the user, e.g., "I couldn't find any transactions for that category," instead of crashing with a SQL error. 

**Q: Is `user_id` passed to the tools securely, or can the LLM access other users' data?**
A: Currently, `user_id` is passed as a parameter to the tool from the LangGraph agent. Since the agent's prompt explicitly injects the user's specific Telegram ID and instructs it to use that ID for all tool calls, the LLM will only request data for that user. However, in a multi-tenant enterprise system, we would rely on the MCP context/session authentication to implicitly inject the `user_id` so the LLM physically cannot request data outside its authorized tenant scope.

**Q: Why use ISO standard string formats (YYYY-MM-DD) for dates in the MCP tools instead of Python `datetime` objects?**
A: MCP communicates over JSON-RPC, meaning all inputs and outputs must be JSON-serializable. Standard Python `datetime` or `date` objects are not natively JSON serializable. ISO 8601 strings are universally understood by LLMs and parse effortlessly across all languages and protocols, making them the standard choice for API dates.
