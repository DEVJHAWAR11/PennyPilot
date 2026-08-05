# Stage 11: Agentic Environment Setup & API Verification

## Features implemented in this stage
- Installed `langgraph`, `mcp`, `fastmcp`, `langchain-mcp-adapters`, and their dependencies into the virtual environment.
- Created `hello_mcp.py` to verify the `FastMCP` server starts and correctly handles JSON-RPC standard I/O streams.
- Created `hello_langgraph.py` to verify that `StateGraph` can be compiled and invoked successfully without errors.

## Commands run
```bash
.\venv\Scripts\pip install langgraph mcp fastmcp langchain-mcp-adapters
.\venv\Scripts\python hello_langgraph.py
Write-Output "" | .\venv\Scripts\python hello_mcp.py
```
*(Both test scripts executed successfully, confirming the API architecture works locally).*

## Code built

`hello_mcp.py` (Trivial MCP Server test)
```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("HelloServer")

@mcp.tool()
def hello_world(name: str) -> str:
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

`hello_langgraph.py` (Trivial LangGraph test)
```python
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

class State(TypedDict):
    message: str

def dummy_node(state: State):
    return {"message": state["message"] + " World!"}

graph = StateGraph(State)
graph.add_node("dummy", dummy_node)
graph.add_edge(START, "dummy")
graph.add_edge("dummy", END)
app = graph.compile()

if __name__ == "__main__":
    result = app.invoke({"message": "Hello"})
    print("LangGraph result:", result)
```

## Interview Q&A

**Q: What is MCP and why use it instead of just calling functions directly?**
A: MCP (Model Context Protocol) is an open standard that standardizes how AI models interact with data sources and tools. If we just wrote Python functions and fed them to a specific LLM SDK (like OpenAI's function calling), our code becomes tightly coupled to that specific LLM provider. By wrapping our database queries in an MCP server, we decouple the tools from the LLM. The LangGraph agent communicates with the server via a standard JSON-RPC protocol over standard I/O (stdio). This means in the future, any other AI model, client, or even local IDE (like Cursor) could connect to this exact same MCP server and interact with the user's financial data without rewriting the tool definitions.

**Q: What is a state graph in LangGraph and why not just a simple loop?**
A: A state graph structures the agent's workflow as a series of nodes (functions) connected by edges (conditional logic), passing a shared `State` object between them. While a simple `while` loop (like the classic ReAct loop) works for basic queries, it becomes brittle as complexity scales. A LangGraph state graph allows for explicit, deterministic control over the flow of execution—making it easier to add human-in-the-loop checkpoints, handle parallel tool executions, implement custom anomaly detection routing, and gracefully recover from LLM hallucinations, which a naive `while` loop cannot do effectively.

**Q: Why use `stdio` transport instead of `SSE` (Server-Sent Events) for the MCP server in this project?**
A: The `stdio` transport runs the MCP server as a local subprocess, communicating directly via standard input and output streams. This is ideal for our Telegram bot architecture because the agent and the tools live on the same physical server instance. It avoids the overhead of managing a separate HTTP server, dealing with port conflicts, and securing network traffic. `SSE` would be necessary if the MCP server was hosted on a completely different machine or microservice.

**Q: How does `FastMCP` simplify the creation of an MCP server compared to the low-level SDK?**
A: `FastMCP` acts as a high-level wrapper (similar to FastAPI for HTTP servers) that abstracts away the boilerplate of manually registering JSON-RPC request handlers and schema definitions. By simply decorating a standard Python function with `@mcp.tool()`, `FastMCP` automatically infers the input schema from type hints and exposes it as a standard MCP tool, drastically reducing development time and potential bugs.

**Q: What challenges could arise when upgrading LangGraph in the future?**
A: LangGraph is currently in heavy development, and its core abstractions (like how states are typed, how reducers merge data, and the prebuilt `create_react_agent` implementation) evolve rapidly. A major challenge is breaking API changes. To mitigate this, we always verify the exact current patterns via a "hello world" setup (as done in this stage) rather than relying on stale muscle memory, and we freeze our dependencies in `requirements.txt` to prevent silent breakage in production.
