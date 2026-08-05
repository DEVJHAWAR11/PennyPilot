"""
Handlers for /balance, /stats, and /settings.
Provides financial summaries, past months breakdown, and start day configuration.
"""
from datetime import date
from collections import defaultdict

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

from bot.db.crud import get_or_create_user, update_month_start_day, get_transactions_for_period
from bot.utils.dates import get_financial_month, get_past_financial_months

router = Router()

# Callback data classes
class StartDayCb(CallbackData, prefix="startday"):
    day: int

class StatsMonthCb(CallbackData, prefix="stats"):
    start_date: str
    end_date: str


# -------------------------------------------------------------------------
# BALANCE
# -------------------------------------------------------------------------

@router.message(Command("balance"))
async def cmd_balance(message: Message) -> None:
    """Show the current financial month's balance."""
    user = await get_or_create_user(message.from_user.id)
    start_day = user["month_start_day"]
    
    today = date.today()
    start_date, end_date = get_financial_month(today, start_day)
    
    transactions = await get_transactions_for_period(
        message.from_user.id, 
        start_date.isoformat(), 
        end_date.isoformat()
    )
    
    income = sum(t["amount"] for t in transactions if t["type"] == "income")
    expenses = sum(t["amount"] for t in transactions if t["type"] == "expense")
    net = income - expenses
    
    savings_pct = (net / income * 100) if income > 0 and net > 0 else 0.0
    
    text = (
        f"📊 **Balance ({start_date.strftime('%b %d')} - {end_date.strftime('%b %d')})**\n\n"
        f"🟢 **Income:** ${income:,.2f}\n"
        f"🔴 **Expenses:** ${expenses:,.2f}\n"
        f"────────────────\n"
        f"💰 **Net Balance:** ${net:,.2f}\n"
    )
    
    if savings_pct > 0:
        text += f"📈 **Savings Rate:** {savings_pct:.1f}%\n"
        
    await message.answer(text, parse_mode="Markdown")


# -------------------------------------------------------------------------
# STATS (Past Months)
# -------------------------------------------------------------------------

@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    """Show a list of past financial months."""
    user = await get_or_create_user(message.from_user.id)
    start_day = user["month_start_day"]
    
    today = date.today()
    periods = get_past_financial_months(today, start_day, count=6)
    
    builder = InlineKeyboardBuilder()
    for p_start, p_end in periods:
        label = f"{p_start.strftime('%b %Y')}"
        if start_day != 1:
            label = f"{p_start.strftime('%b %d')} - {p_end.strftime('%b %d')}"
            
        builder.button(
            text=label, 
            callback_data=StatsMonthCb(start_date=p_start.isoformat(), end_date=p_end.isoformat()).pack()
        )
    
    builder.adjust(1)
    await message.answer(
        "📅 **Select a month to view its breakdown:**", 
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@router.callback_query(StatsMonthCb.filter())
async def cb_stats_month(query: CallbackQuery, callback_data: StatsMonthCb) -> None:
    """Show the category breakdown for a specific month."""
    start_date = callback_data.start_date
    end_date = callback_data.end_date
    
    transactions = await get_transactions_for_period(
        query.from_user.id, start_date, end_date
    )
    
    # Calculate breakdown
    income = sum(t["amount"] for t in transactions if t["type"] == "income")
    expenses = sum(t["amount"] for t in transactions if t["type"] == "expense")
    net = income - expenses
    
    # Group expenses by category
    cat_totals = defaultdict(float)
    cat_emojis = {}
    for t in transactions:
        if t["type"] == "expense":
            name = t["category_name"]
            cat_totals[name] += t["amount"]
            cat_emojis[name] = t["category_emoji"]
            
    # Sort categories by amount descending
    sorted_cats = sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)
    
    # Format the message
    # Convert dates to more readable format for the header
    s_date = date.fromisoformat(start_date)
    e_date = date.fromisoformat(end_date)
    header = f"📊 **Breakdown ({s_date.strftime('%b %d')} - {e_date.strftime('%b %d')})**\n\n"
    
    body = ""
    if not sorted_cats:
        body = "No expenses recorded this month."
    else:
        for name, amount in sorted_cats:
            emoji = cat_emojis.get(name, "")
            pct = (amount / expenses * 100) if expenses > 0 else 0
            body += f"{emoji} **{name}**: ${amount:,.2f} ({pct:.0f}%)\n"
            
    footer = (
        f"\n────────────────\n"
        f"🟢 **Income:** ${income:,.2f}\n"
        f"🔴 **Expenses:** ${expenses:,.2f}\n"
        f"💰 **Net Balance:** ${net:,.2f}\n"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Back to Months", callback_data="stats_back")
    
    await query.message.edit_text(
        header + body + footer,
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "stats_back")
async def cb_stats_back(query: CallbackQuery) -> None:
    """Return to the month selection list."""
    await cmd_stats(query.message)


# -------------------------------------------------------------------------
# SETTINGS
# -------------------------------------------------------------------------

@router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    """Show settings menu."""
    user = await get_or_create_user(message.from_user.id)
    current_day = user["month_start_day"]
    
    builder = InlineKeyboardBuilder()
    builder.button(text="⚙️ Change Month Start Day", callback_data="settings_start_day")
    
    await message.answer(
        "⚙️ **Settings**\n\n"
        f"📅 **Current Month Start Day:** {current_day}\n"
        f"*(Your financial month runs from the {current_day}th to the {current_day-1}th)*",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "settings_start_day")
async def cb_settings_start_day(query: CallbackQuery) -> None:
    """Show keyboard to select a day from 1 to 28."""
    builder = InlineKeyboardBuilder()
    
    # Create buttons for days 1, 5, 10, 15, 20, 25, 28 for brevity, 
    # or just a few common ones to avoid a huge keyboard.
    common_days = [1, 5, 10, 15, 20, 25, 28]
    for day in common_days:
        builder.button(text=str(day), callback_data=StartDayCb(day=day).pack())
        
    builder.button(text="⬅️ Cancel", callback_data="settings_cancel")
    builder.adjust(4, 3, 1)
    
    await query.message.edit_text(
        "Select the day your financial month starts (e.g. your payday).\n"
        "*(Limited to 28 to avoid issues with February)*",
        reply_markup=builder.as_markup()
    )

@router.callback_query(StartDayCb.filter())
async def cb_set_start_day(query: CallbackQuery, callback_data: StartDayCb) -> None:
    """Save the new start day."""
    new_day = callback_data.day
    await update_month_start_day(query.from_user.id, new_day)
    
    await query.message.edit_text(
        f"✅ Financial month start day updated to the **{new_day}th**!\n\n"
        "Your /balance and /stats will now calculate based on this period.",
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "settings_cancel")
async def cb_settings_cancel(query: CallbackQuery) -> None:
    """Cancel settings edit."""
    await query.message.delete()
