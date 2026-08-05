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
async def get_txns(uid: int, sdt: str, edt: str, cat: Optional[str] = None) -> str:
    """Get txns in date range (YYYY-MM-DD). Optional category."""
    transactions = await get_transactions_for_period(uid, sdt, edt)
    if cat:
        cat = cat.lower()
        transactions = [t for t in transactions if t["category_name"].lower() == cat]
    
    if not transactions:
        return "None"
        
    res = "id,amt,typ,cat,note,date\n"
    for t in transactions:
        res += f"{t['id']},{t['amount']},{t['type'][0]},{t['category_name']},{t['note']},{t['date']}\n"
    return res

@mcp.tool()
async def get_cat_totals(uid: int, sdt: str, edt: str) -> dict[str, float]:
    """Get expense totals per category (YYYY-MM-DD)."""
    transactions = await get_transactions_for_period(uid, sdt, edt)
    
    cat_totals = defaultdict(float)
    for t in transactions:
        if t["type"] == "expense":
            name = t["category_name"]
            cat_totals[name] += t["amount"]
            
    return dict(cat_totals)

@mcp.tool()
async def get_bal(uid: int, sdt: str, edt: str) -> dict[str, float]:
    """Get total income, expenses, net (YYYY-MM-DD)."""
    transactions = await get_transactions_for_period(uid, sdt, edt)
    
    income = sum(t["amount"] for t in transactions if t["type"] == "income")
    expenses = sum(t["amount"] for t in transactions if t["type"] == "expense")
    net = income - expenses
    
    return {
        "inc": income,
        "exp": expenses,
        "net": net
    }

@mcp.tool()
async def chart(uid: int, sdt: str, edt: str) -> str:
    """Pie chart for date range (YYYY-MM-DD), returns filepath."""
    transactions = await get_transactions_for_period(uid, sdt, edt)
    
    cat_totals = defaultdict(float)
    for t in transactions:
        if t["type"] == "expense":
            cat_totals[t["category_name"]] += t["amount"]
            
    if not cat_totals:
        return "No expenses"
        
    chart_bytes = generate_pie_chart(cat_totals)
    
    temp_dir = tempfile.gettempdir()
    filepath = os.path.join(temp_dir, f"chart_{uid}_{sdt}_{edt}.png")
    
    with open(filepath, "wb") as f:
        f.write(chart_bytes)
        
    return filepath

@mcp.tool()
async def log_txn(uid: int, amt: float, typ: str, cat: str, nt: str, dt: str) -> str:
    """Log txn. typ: 'income'|'expense'. dt: YYYY-MM-DD."""
    categories = await get_categories(uid)
    c = next((x for x in categories if x["name"].lower() == cat.lower()), None)
    
    if not c:
        valid_cats = ", ".join([x["name"] for x in categories])
        return f"Err: Cat not found. Available: {valid_cats}"

    await add_transaction(uid, amt, typ, c["id"], nt, dt)
    return f"Logged"

@mcp.tool()
async def del_txn(tid: int) -> str:
    """Delete txn by ID."""
    txn = await get_transaction_by_id(tid)
    if not txn:
        return f"Err: ID {tid} not found."
        
    await delete_transaction(tid)
    return f"Deleted"

@mcp.tool()
async def upd_cat(uid: int, tid: int, ncat: str) -> str:
    """Change category of txn by ID."""
    txn = await get_transaction_by_id(tid)
    if not txn:
        return f"Err: ID {tid} not found."

    categories = await get_categories(uid)
    c = next((x for x in categories if x["name"].lower() == ncat.lower()), None)
    
    if not c:
        valid_cats = ", ".join([x["name"] for x in categories])
        return f"Err: Cat not found. Available: {valid_cats}"

    await update_transaction(tid, category_id=c["id"])
    return f"Updated"

if __name__ == "__main__":
    mcp.run(transport="stdio")
