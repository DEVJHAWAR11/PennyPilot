from mcp.server.fastmcp import FastMCP

mcp = FastMCP("HelloServer")

@mcp.tool()
def hello_world(name: str) -> str:
    """Say hello to someone."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run(transport="stdio")
