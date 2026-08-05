"""
Category and keyword management via inline keyboards.
Implements the /categories command flow.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from bot.db.crud import (
    get_categories,
    get_category_by_id,
    add_category,
    delete_category,
    rename_category,
    get_keywords_for_category,
    add_keyword,
    delete_keyword
)

router = Router()

# ────────────────── Callback Data ──────────────────

class CatListCb(CallbackData, prefix="cl"):
    pass

class CatViewCb(CallbackData, prefix="cv"):
    cat_id: int

class CatAddCb(CallbackData, prefix="ca"):
    pass

class CatTypeCb(CallbackData, prefix="ct"):
    type: str # 'income' or 'expense'

class CatDelCb(CallbackData, prefix="cd"):
    cat_id: int

class CatRenCb(CallbackData, prefix="cr"):
    cat_id: int

class KwAddCb(CallbackData, prefix="ka"):
    cat_id: int

class KwDelListCb(CallbackData, prefix="kdl"):
    cat_id: int

class KwDelCb(CallbackData, prefix="kd"):
    kw_id: int
    cat_id: int

# ────────────────── FSM States ──────────────────

class CategoryFSM(StatesGroup):
    waiting_for_new_name = State()
    waiting_for_new_type = State()
    waiting_for_rename = State()
    waiting_for_new_keyword = State()


# ────────────────── Handlers ──────────────────

@router.message(Command("categories"))
async def cmd_categories(message: Message, state: FSMContext) -> None:
    """Entry point for /categories."""
    # Guarantee user exists in DB
    from bot.db.crud import get_or_create_user
    await get_or_create_user(message.from_user.id)
    
    await state.clear()
    await show_categories_list(message.from_user.id, message.answer)


async def show_categories_list(telegram_id: int, send_or_edit_func) -> None:
    """Helper to display the list of categories."""
    categories = await get_categories(telegram_id)
    
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(
            text=f"{cat['emoji']} {cat['name']} ({cat['type']})",
            callback_data=CatViewCb(cat_id=cat['id']).pack()
        )
    
    # 1 button per row for readability
    builder.adjust(1)
    
    # Add category button at the bottom
    builder.row(InlineKeyboardButton(text="➕ Add New Category", callback_data=CatAddCb().pack()))

    text = "📁 **Your Categories**\nSelect a category to manage it or add a new one."
    
    # send_or_edit_func is either message.answer or query.message.edit_text
    if getattr(send_or_edit_func, "__self__", None) and hasattr(getattr(send_or_edit_func, "__self__"), "edit_text"):
        # it's an edit
        await send_or_edit_func(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    else:
        # it's a new message
        await send_or_edit_func(text=text, reply_markup=builder.as_markup(), parse_mode="Markdown")


@router.callback_query(CatListCb.filter())
async def cb_cat_list(query: CallbackQuery, state: FSMContext) -> None:
    """Return to the categories list."""
    await state.clear()
    await show_categories_list(query.from_user.id, query.message.edit_text)


@router.callback_query(CatViewCb.filter())
async def cb_cat_view(query: CallbackQuery, callback_data: CatViewCb, state: FSMContext) -> None:
    """View details of a specific category."""
    await state.clear()
    cat = await get_category_by_id(callback_data.cat_id)
    if not cat:
        await query.answer("Category not found.", show_alert=True)
        return
        
    keywords = await get_keywords_for_category(cat['id'])
    kw_texts = [k['keyword'] for k in keywords]
    kw_str = ", ".join(kw_texts) if kw_texts else "_None_"
    
    text = (
        f"📁 **Category:** {cat['emoji']} {cat['name']}\n"
        f"📊 **Type:** {cat['type'].capitalize()}\n"
        f"🔑 **Keywords:** {kw_str}"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Rename", callback_data=CatRenCb(cat_id=cat['id']).pack())
    builder.button(text="🗑️ Delete", callback_data=CatDelCb(cat_id=cat['id']).pack())
    builder.button(text="➕ Add Keyword", callback_data=KwAddCb(cat_id=cat['id']).pack())
    
    if keywords:
        builder.button(text="➖ Delete a Keyword", callback_data=KwDelListCb(cat_id=cat['id']).pack())
        
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="⬅️ Back to List", callback_data=CatListCb().pack()))
    
    await query.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")


# ─── Add Category Flow ───

@router.callback_query(CatAddCb.filter())
async def cb_cat_add(query: CallbackQuery, state: FSMContext) -> None:
    """Start the add category flow."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Cancel", callback_data=CatListCb().pack())
    
    await query.message.edit_text(
        "Please type the name of the new category (you can include an emoji at the start):",
        reply_markup=builder.as_markup()
    )
    await state.set_state(CategoryFSM.waiting_for_new_name)


@router.message(CategoryFSM.waiting_for_new_name)
async def process_new_cat_name(message: Message, state: FSMContext) -> None:
    """Receive the new category name and ask for its type."""
    name = message.text.strip()
    await state.update_data(new_cat_name=name)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🟢 Income", callback_data=CatTypeCb(type="income").pack())
    builder.button(text="🔴 Expense", callback_data=CatTypeCb(type="expense").pack())
    builder.button(text="⬅️ Cancel", callback_data=CatListCb().pack())
    builder.adjust(2, 1)
    
    await message.answer(
        f"Got it. Is **{name}** an income or expense?",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await state.set_state(CategoryFSM.waiting_for_new_type)


@router.callback_query(CategoryFSM.waiting_for_new_type, CatTypeCb.filter())
async def cb_cat_type(query: CallbackQuery, callback_data: CatTypeCb, state: FSMContext) -> None:
    """Receive the category type and create it."""
    data = await state.get_data()
    name = data.get("new_cat_name")
    
    # Basic emoji extraction - just treat the first char as emoji if it's not alphanumeric
    emoji = ""
    clean_name = name
    if name and not name[0].isalnum():
        emoji = name[0]
        clean_name = name[1:].strip()
        if not clean_name:
            clean_name = name # fallback
            
    await add_category(query.from_user.id, clean_name, callback_data.type, emoji)
    
    await query.answer("Category created!")
    await state.clear()
    # Go back to list
    await show_categories_list(query.from_user.id, query.message.edit_text)


# ─── Rename Category Flow ───

@router.callback_query(CatRenCb.filter())
async def cb_cat_rename(query: CallbackQuery, callback_data: CatRenCb, state: FSMContext) -> None:
    await state.update_data(rename_cat_id=callback_data.cat_id)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Cancel", callback_data=CatViewCb(cat_id=callback_data.cat_id).pack())
    
    await query.message.edit_text(
        "Type the new name for this category:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(CategoryFSM.waiting_for_rename)


@router.message(CategoryFSM.waiting_for_rename)
async def process_rename(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    cat_id = data.get("rename_cat_id")
    new_name = message.text.strip()
    
    await rename_category(cat_id, new_name)
    await message.answer("✅ Category renamed.")
    await state.clear()
    
    # We can't edit the previous message easily from here, so send a new view
    cat = await get_category_by_id(cat_id)
    
    # Trick: construct a fake callback query or just call the helper logic
    # Actually, simplest is to just send the new list
    await show_categories_list(message.from_user.id, message.answer)


# ─── Delete Category Flow ───

@router.callback_query(CatDelCb.filter())
async def cb_cat_delete(query: CallbackQuery, callback_data: CatDelCb) -> None:
    # Delete immediately without confirmation for simplicity in this bot,
    # or could add a confirm state. Let's just delete.
    await delete_category(callback_data.cat_id)
    await query.answer("Category deleted.", show_alert=True)
    await show_categories_list(query.from_user.id, query.message.edit_text)


# ─── Keywords Flow ───

@router.callback_query(KwAddCb.filter())
async def cb_kw_add(query: CallbackQuery, callback_data: KwAddCb, state: FSMContext) -> None:
    await state.update_data(kw_cat_id=callback_data.cat_id)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Cancel", callback_data=CatViewCb(cat_id=callback_data.cat_id).pack())
    
    await query.message.edit_text(
        "Type the new keyword to link to this category:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(CategoryFSM.waiting_for_new_keyword)


@router.message(CategoryFSM.waiting_for_new_keyword)
async def process_new_keyword(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    cat_id = data.get("kw_cat_id")
    keyword = message.text.strip().lower()
    
    await add_keyword(message.from_user.id, keyword, cat_id)
    await message.answer(f"✅ Keyword `{keyword}` added.", parse_mode="Markdown")
    await state.clear()
    await show_categories_list(message.from_user.id, message.answer)


@router.callback_query(KwDelListCb.filter())
async def cb_kw_del_list(query: CallbackQuery, callback_data: KwDelListCb) -> None:
    """Show list of keywords to delete."""
    cat_id = callback_data.cat_id
    keywords = await get_keywords_for_category(cat_id)
    
    builder = InlineKeyboardBuilder()
    for kw in keywords:
        builder.button(
            text=f"❌ {kw['keyword']}",
            callback_data=KwDelCb(kw_id=kw['id'], cat_id=cat_id).pack()
        )
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="⬅️ Back", callback_data=CatViewCb(cat_id=cat_id).pack()))
    
    await query.message.edit_text(
        "Tap a keyword to delete it:",
        reply_markup=builder.as_markup()
    )


@router.callback_query(KwDelCb.filter())
async def cb_kw_delete(query: CallbackQuery, callback_data: KwDelCb) -> None:
    await delete_keyword(callback_data.kw_id)
    await query.answer("Keyword deleted.")
    
    # Refresh keyword deletion list
    await cb_kw_del_list(query, KwDelListCb(cat_id=callback_data.cat_id))
