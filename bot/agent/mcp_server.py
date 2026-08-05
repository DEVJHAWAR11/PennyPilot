import os
import tempfile
from collections import defaultdict
from fastmcp import FastMCP

from bot.db.crud import get_transactions_for_period
from bot.services.charts import generate_pie_chart

# We need to initialize the fastmcp app
mcp = FastMCP("PennyPilot")

@mcp.tool()
async def query_transactions(user_id: int, start_date: str, end_date: str, category: str = None) -> list[dict]:
    """
    Return matching transactions for a user within a date range (YYYY-MM-DD).
    Optionally filter by category name.
    """
    transactions = await get_transactions_for_period(user_id, start_date, end_date)
    if category:
        category = category.lower()
        transactions = [t for t in transactions if t["category_name"].lower() == category]
    
    return [
        {
            "id": t["id"],
            "amount": t["amount"],
            "type": t["type"],
            "category": t["category_name"],
            "note": t["note"],
            "date": t["date"]
        } for t in transactions
    ]

@mcp.tool()
async def get_category_totals(user_id: int, start_date: str, end_date: str) -> dict[str, float]:
    """
    Return aggregated expense totals per category for a user within a date range (YYYY-MM-DD).
    """
    transactions = await get_transactions_for_period(user_id, start_date, end_date)
    
    cat_totals = defaultdict(float)
    for t in transactions:
        if t["type"] == "expense":
            name = t["category_name"]
            cat_totals[name] += t["amount"]
            
    return dict(cat_totals)

@mcp.tool()
async def get_balance(user_id: int, start_date: str, end_date: str) -> dict[str, float]:
    """
    Calculate the total income, total expenses, and net balance for a given date range (YYYY-MM-DD).
    """
    transactions = await get_transactions_for_period(user_id, start_date, end_date)
    
    income = sum(t["amount"] for t in transactions if t["type"] == "income")
    expenses = sum(t["amount"] for t in transactions if t["type"] == "expense")
    net = income - expenses
    
    return {
        "income": income,
        "expenses": expenses,
        "net_balance": net
    }

@mcp.tool()
async def generate_chart(user_id: int, start_date: str, end_date: str) -> str:
    """
    Generate a pie chart of expenses for a date range (YYYY-MM-DD) and return the absolute file path to the saved image.
    The agent can then pass this filepath back to Telegram to send to the user.
    """
    transactions = await get_transactions_for_period(user_id, start_date, end_date)
    
    cat_totals = defaultdict(float)
    for t in transactions:
        if t["type"] == "expense":
            cat_totals[t["category_name"]] += t["amount"]
            
    if not cat_totals:
        return "No expenses found for this period to chart."
        
    chart_bytes = generate_pie_chart(cat_totals)
    
    temp_dir = tempfile.gettempdir()
    filepath = os.path.join(temp_dir, f"chart_{user_id}_{start_date}_{end_date}.png")
    
    with open(filepath, "wb") as f:
        f.write(chart_bytes)
        
    return filepath

if __name__ == "__main__":
    mcp.run(transport="stdio")
