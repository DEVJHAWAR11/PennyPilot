# Stage 15: Monthly AI Summary Agent

## Overview
Stage 15 introduces the Monthly AI Summary Agent, a scheduled background job that generates a personalized, unprompted recap of a user's spending at the close of their financial month. Unlike standard periodic reports, this agent leverages LangGraph and MCP tools to produce natural-language insights dynamically.

## Architecture

1. **Trigger Mechanism**: `bot/agent/summary.py` exposes a `send_monthly_summaries` function. This is hooked into `APScheduler` in `main.py` and runs daily (e.g., at 10:00 UTC).
2. **User Selection**: The job iterates over all users in the SQLite database. For each user, it checks if today's date matches their configured `month_start_day`. If it matches, the previous financial month has officially closed.
3. **Date Calculation**: Using `bot.utils.dates.get_past_financial_months()`, the system calculates the exact date boundaries for the just-closed month and the month prior to that (for comparison).
4. **Agent Invocation**: A custom `SUMMARY_SYSTEM_PROMPT` is sent to the LangGraph React agent (using Groq's 70B model). The prompt injects the user ID and the specific date boundaries, strictly instructing the agent to use `get_cat_totals` and `get_bal` MCP tools to fetch the real data.
5. **Rate Limiting Protection**: A crucial `await asyncio.sleep(10)` is enforced between processing each user. This prevents the scheduler from instantly exhausting LLM API limits (Requests Per Minute) by firing off dozens of concurrent complex agent invocations.

## Bug Fixes and Stability
During development, a critical bug was identified and resolved in the agent's memory window (the `trimmer` in `bot/agent/graph.py`). Previously, `max_tokens=4` instructed the trimmer to only retain the last 4 *messages* (not tokens). In a multi-step tool-calling loop, the initial `HumanMessage` containing the instructions and dates would fall out of the context window, causing the agent to forget its objective and enter an infinite loop of failed tool calls, thereby draining the API's token limits. This was fixed by expanding the `max_tokens` (message count) to `20`.

## Verification
The agent was manually verified by:
- Seeding data for the prior month and the closed month.
- Running a test script (`test_summary.py`) that forced the agent to evaluate the user's data.
- Ensuring the generated output was strictly grounded in the database data (no hallucinated figures).

## Questions and Answers

**Q: How does the agent generate the summary without hallucinating numbers?**
A: The agent is instructed in the `SUMMARY_SYSTEM_PROMPT` to rely *only* on the output of its MCP tools (`get_cat_totals`, `get_bal`). It cannot guess expenses. The tool output forms the factual basis of the natural-language response.

**Q: Why was the agent hitting infinite loops and API rate limits previously?**
A: When an agent uses multiple tools, the conversation history grows rapidly (1 Human message, 1 AI tool call message, 1 Tool result message, etc.). If the conversation memory trimmer is configured too aggressively (e.g., retaining only the last 4 messages), the initial instructions (containing the user ID and date ranges) are pruned from the prompt. The LLM then loses context of *why* it is running tools, fails to satisfy the objective, and repeatedly loops in confusion, generating 429 Rate Limit errors. Increasing the context retention size completely resolved this.
