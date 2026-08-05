"""
Handler for the /export command.
"""
from datetime import date
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

from bot.db.crud import get_or_create_user, get_transactions_for_period
from bot.utils.dates import get_past_financial_months
from bot.services.export import generate_csv, generate_pdf

router = Router()

class ExportMonthCb(CallbackData, prefix="exp_mo"):
    start_date: str
    end_date: str
    label: str

@router.message(Command("export"))
async def cmd_export(message: Message) -> None:
    """Show options for exporting data."""
    user = await get_or_create_user(message.from_user.id)
    start_day = user["month_start_day"]
    
    today = date.today()
    periods = get_past_financial_months(today, start_day, count=3)
    
    builder = InlineKeyboardBuilder()
    
    for p_start, p_end in periods:
        label = f"{p_start.strftime('%b %Y')}"
        if start_day != 1:
            label = f"{p_start.strftime('%b %d')} - {p_end.strftime('%b %d')}"
            
        builder.button(
            text=f"📄 PDF: {label}", 
            callback_data=ExportMonthCb(
                start_date=p_start.isoformat(), 
                end_date=p_end.isoformat(),
                label=label
            ).pack()
        )
        
    builder.button(text="📊 CSV: All Transactions", callback_data="export_all_csv")
    builder.adjust(1)
    
    await message.answer(
        "📥 **Export your data**\n\n"
        "Choose to download a monthly PDF statement, or export your entire history as a CSV.",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "export_all_csv")
async def cb_export_csv(query: CallbackQuery) -> None:
    """Generate and send a CSV of all transactions."""
    await query.answer("Generating CSV...")
    
    # We can get all transactions by passing an extremely wide date range
    transactions = await get_transactions_for_period(
        query.from_user.id, "1970-01-01", "2100-01-01"
    )
    
    csv_bytes = generate_csv(transactions)
    document = BufferedInputFile(csv_bytes, filename="all_transactions.csv")
    
    await query.message.answer_document(
        document=document,
        caption="📊 Here is your full transaction history in CSV format."
    )

@router.callback_query(ExportMonthCb.filter())
async def cb_export_pdf(query: CallbackQuery, callback_data: ExportMonthCb) -> None:
    """Generate and send a PDF statement for a specific month."""
    await query.answer("Generating PDF statement...")
    
    transactions = await get_transactions_for_period(
        query.from_user.id, callback_data.start_date, callback_data.end_date
    )
    
    income = sum(t["amount"] for t in transactions if t["type"] == "income")
    expenses = sum(t["amount"] for t in transactions if t["type"] == "expense")
    net = income - expenses
    
    summary = {
        "income": income,
        "expenses": expenses,
        "net": net
    }
    
    pdf_bytes = generate_pdf(transactions, callback_data.label, summary)
    
    filename = f"statement_{callback_data.label.replace(' ', '_')}.pdf"
    document = BufferedInputFile(pdf_bytes, filename=filename)
    
    await query.message.answer_document(
        document=document,
        caption=f"📄 Here is your PDF statement for {callback_data.label}."
    )
