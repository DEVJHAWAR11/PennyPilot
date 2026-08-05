import os
import tempfile
from collections import defaultdict
from typing import Optional
from fastmcp import FastMCP

from bot.db.crud import get_transactions_for_period, add_transaction, get_categories, delete_transaction, update_transaction, get_transaction_by_id
from bot.services.charts import generate_pie_chart

# We need to initialize the fastmcp app
mcp = FastMCP("PennyPilot")

@mcp.tool()
async def query_transactions(user_id: int, start_date: str, end_date: str, category: Optional[str] = None) -> list[dict]:
    """Get txns in date range (YYYY-MM-DD). Optional category filter."""
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
    """Get expense totals per category (YYYY-MM-DD)."""
    transactions = await get_transactions_for_period(user_id, start_date, end_date)
    
    cat_totals = defaultdict(float)
    for t in transactions:
        if t["type"] == "expense":
            name = t["category_name"]
            cat_totals[name] += t["amount"]
            
    return dict(cat_totals)

@mcp.tool()
async def get_balance(user_id: int, start_date: str, end_date: str) -> dict[str, float]:
    """Get total income, expenses, and net (YYYY-MM-DD)."""
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
    """Generate pie chart for date range (YYYY-MM-DD), returns filepath."""
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

@mcp.tool()
async def log_transaction(user_id: int, amount: float, txn_type: str, category_name: str, note: str, date: str) -> str:
    """Log a txn. type: 'income'|'expense'. date: YYYY-MM-DD. category_name must be known."""
    categories = await get_categories(user_id)
    cat = next((c for c in categories if c["name"].lower() == category_name.lower()), None)
    
    if not cat:
        valid_cats = ", ".join([c["name"] for c in categories])
        return f"Error: Category '{category_name}' not found. Please choose from: {valid_cats}"

    await add_transaction(user_id, amount, txn_type, cat["id"], note, date)
    
    return f"Successfully logged {txn_type} of {amount} in {cat['name']} on {date}. Note: {note}"

@mcp.tool()
async def delete_transaction_tool(txn_id: int) -> str:
    """Delete a txn by ID (find ID first via query_transactions)."""
    txn = await get_transaction_by_id(txn_id)
    if not txn:
        return f"Error: Transaction with ID {txn_id} not found."
        
    await delete_transaction(txn_id)
    return f"Successfully deleted transaction ID {txn_id}."

@mcp.tool()
async def update_transaction_category_tool(user_id: int, txn_id: int, new_category_name: str) -> str:
    """Change the category of an existing txn by ID."""
    txn = await get_transaction_by_id(txn_id)
    if not txn:
        return f"Error: Transaction with ID {txn_id} not found."

    categories = await get_categories(user_id)
    cat = next((c for c in categories if c["name"].lower() == new_category_name.lower()), None)
    
    if not cat:
        valid_cats = ", ".join([c["name"] for c in categories])
        return f"Error: Category '{new_category_name}' not found. Please choose from: {valid_cats}"

    await update_transaction(txn_id, category_id=cat["id"])
    return f"Successfully updated transaction ID {txn_id} to category '{cat['name']}'."

if __name__ == "__main__":
    mcp.run(transport="stdio")
