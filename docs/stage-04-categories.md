# Stage 04: Category & Keyword Management

## Features implemented in this stage
- **Interactive Inline Dashboards (`bot/handlers/categories.py`)**: Users can manage their categories entirely via inline keyboards instead of memorizing text commands. This provides a modern, app-like experience within Telegram.
- **Category CRUD**: Users can view all categories, add new categories (specifying a name and choosing Income/Expense via buttons), rename existing categories, and delete categories.
- **Keyword Management**: Users can drill down into a category to view its linked keywords. They can add new keywords manually or delete existing ones.
- **Finite State Machine (FSM)**: Used aiogram's built-in FSM to handle multi-step conversations (e.g., waiting for the user to type a new category name, waiting for a rename, waiting for a new keyword).

## Commands run
```bash
git add -A
git commit -m "Added interactive category and keyword management via inline keyboards and FSM"
git push
```

## Code built

### `bot/handlers/categories.py`
This module introduces stateful conversations and complex callback routing.
```python
class CategoryFSM(StatesGroup):
    waiting_for_new_name = State()
    waiting_for_new_type = State()
    waiting_for_rename = State()
    waiting_for_new_keyword = State()

@router.message(Command("categories"))
async def cmd_categories(message: Message, state: FSMContext) -> None:
    # Clears any stuck state and shows the main list
    pass
```

**What it does:**
It builds dynamic inline keyboards using `InlineKeyboardBuilder`. When a user clicks a button, a specific `CallbackData` payload is sent. We filter these using `CatViewCb.filter()`, `CatAddCb.filter()`, etc.
For actions requiring text input (like renaming), the bot transitions the user into an FSM state (e.g., `CategoryFSM.waiting_for_rename`). The next text message the user sends is intercepted by a handler specifically listening for that state, avoiding conflicts with the general transaction logger.

### Updates to `main.py` and `commands.py`
- Added the `categories_router` to the dispatcher in `main.py`.
- Updated the `/help` text in `commands.py` to document the `/categories` command.

## Interview Q&A

**Q: Why use Inline Keyboards instead of commands like `/addcategory`?**
A: Inline keyboards provide a significantly better user experience. They don't clutter the chat history with command text, they prevent formatting errors (e.g., typing `/addcategory groceries expense` vs `/addcategory groceries, expense`), and they allow users to discover features visually. It transforms the bot from a CLI tool into an interactive app.

**Q: How does aiogram's FSM work for the "Rename Category" flow?**
A: When the user taps "Rename", we do three things: (1) We store the `category_id` in the FSM context (`state.update_data(rename_cat_id=cat_id)`). (2) We set the user's state to `waiting_for_rename`. (3) We ask them to type the new name. The next time the user types a message, aiogram checks their state. Instead of hitting the default transaction parser, the message hits the `process_rename` handler which is bound to `waiting_for_rename`. We read the new name, retrieve the `category_id` from the state data, apply the database update, and then clear the state.

**Q: What happens if a user is in the middle of renaming a category and clicks a different inline button instead of typing text?**
A: Our callback handlers all start with `await state.clear()`. If a user abandons a text input flow and clicks "Back to List" or a different category button, their state is immediately cleared, preventing them from getting permanently stuck in `waiting_for_rename`.

**Q: How do you handle emoji extraction when a user creates a category?**
A: In `cb_cat_type`, we do a lightweight check: if the first character of the category name is not alphanumeric (e.g., `🍔 Dining`), we assume it's an emoji. We split the string, storing `🍔` in the `emoji` column and `Dining` in the `name` column. This keeps the database clean and allows us to format messages cleanly (e.g., `🍔 Dining` instead of `🍔🍔 Dining`).

**Q: If I delete a category, what happens to its keywords and the transactions logged under it?**
A: Because of the `ON DELETE CASCADE` foreign key constraints defined in Stage 2's SQLite schema, deleting a category automatically deletes all linked keywords and all transactions logged under that category. The database handles this referential integrity automatically without requiring multiple DELETE queries in Python. (Note: in a production app, we might want a "soft delete" or a re-assignment flow, but for a minimal personal bot, cascade is standard).
