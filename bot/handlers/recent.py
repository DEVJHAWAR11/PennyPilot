"""
Handlers for viewing, editing, and deleting recent transactions.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from bot.db.crud import get_recent_transactions, delete_transaction, get_transaction_by_id, update_transaction

router = Router()

class TxnViewCb(CallbackData, prefix="tx_v"):
    txn_id: int

class TxnDelCb(CallbackData, prefix="tx_d"):
    txn_id: int

class TxnEditAmountCb(CallbackData, prefix="tx_ea"):
    txn_id: int

class RecentFSM(StatesGroup):
    waiting_for_new_amount = State()

@router.message(Command("recent"))
async def cmd_recent(message: Message, state: FSMContext) -> None:
    """Show the list of recent transactions."""
    await state.clear()
    await show_recent_list(message.from_user.id, message.answer)


async def show_recent_list(telegram_id: int, send_or_edit_func) -> None:
    """Helper to display the recent transactions list."""
    transactions = await get_recent_transactions(telegram_id, limit=10)
    
    if not transactions:
        text = "No recent transactions found."
        builder = None
    else:
        text = "🕒 **Recent Transactions (Last 10)**\nSelect a transaction to edit or delete it."
        builder = InlineKeyboardBuilder()
        for t in transactions:
            emoji = t.get('category_emoji', '💰')
            amount_str = f"₹{t['amount']:,.2f}"
            date_str = t['date'][5:] # MM-DD
            label = f"{emoji} {t['category_name']} | {amount_str} ({date_str})"
            
            builder.button(
                text=label,
                callback_data=TxnViewCb(txn_id=t['id']).pack()
            )
        builder.adjust(1)
        
    reply_markup = builder.as_markup() if builder else None
    
    if getattr(send_or_edit_func, "__self__", None) and hasattr(getattr(send_or_edit_func, "__self__"), "edit_text"):
        await send_or_edit_func(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await send_or_edit_func(text=text, reply_markup=reply_markup, parse_mode="Markdown")


@router.callback_query(TxnViewCb.filter())
async def cb_txn_view(query: CallbackQuery, callback_data: TxnViewCb) -> None:
    """View details of a transaction with edit/delete buttons."""
    txn = await get_transaction_by_id(callback_data.txn_id)
    if not txn:
        await query.answer("Transaction not found.", show_alert=True)
        return
        
    emoji = txn.get('category_emoji', '')
    text = (
        f"📝 **Transaction Details**\n\n"
        f"**Date:** {txn['date']}\n"
        f"**Category:** {emoji} {txn['category_name']} ({txn['type']})\n"
        f"**Amount:** ₹{txn['amount']:,.2f}\n"
        f"**Note:** {txn['note'] or 'None'}\n"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Edit Amount", callback_data=TxnEditAmountCb(txn_id=txn['id']).pack())
    builder.button(text="🗑️ Delete", callback_data=TxnDelCb(txn_id=txn['id']).pack())
    builder.button(text="⬅️ Back to Recent", callback_data="recent_list")
    builder.adjust(2, 1)
    
    await query.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")


@router.callback_query(F.data == "recent_list")
async def cb_recent_list(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await show_recent_list(query.from_user.id, query.message.edit_text)


@router.callback_query(TxnDelCb.filter())
async def cb_txn_delete(query: CallbackQuery, callback_data: TxnDelCb) -> None:
    await delete_transaction(callback_data.txn_id)
    await query.answer("Transaction deleted.", show_alert=True)
    await show_recent_list(query.from_user.id, query.message.edit_text)


@router.callback_query(TxnEditAmountCb.filter())
async def cb_txn_edit_amount(query: CallbackQuery, callback_data: TxnEditAmountCb, state: FSMContext) -> None:
    await state.update_data(edit_txn_id=callback_data.txn_id)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Cancel", callback_data=TxnViewCb(txn_id=callback_data.txn_id).pack())
    
    await query.message.edit_text(
        "Please type the new amount (e.g. 150.50):",
        reply_markup=builder.as_markup()
    )
    await state.set_state(RecentFSM.waiting_for_new_amount)


@router.message(RecentFSM.waiting_for_new_amount)
async def process_new_amount(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    txn_id = data.get("edit_txn_id")
    
    try:
        new_amount = float(message.text.strip())
        if new_amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Please enter a valid positive number.")
        return
        
    await update_transaction(txn_id, amount=new_amount)
    await message.answer("✅ Transaction amount updated.")
    await state.clear()
    await show_recent_list(message.from_user.id, message.answer)
