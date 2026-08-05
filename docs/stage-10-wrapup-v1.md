# Stage 10: Wrap-up & Final Features

## Features implemented in this stage
- Added `/recent` command to view the last 10 transactions.
- Built an interactive inline keyboard interface for `/recent` that allows the user to drill down into a transaction, edit its amount via a finite state machine (FSM), or delete it entirely.
- Added a `/reset` command to completely wipe a user's data (transactions, keywords, and categories) and restore the default category seed. Included a "DANGER ZONE" confirmation step to prevent accidental deletions.
- Updated `bot/db/crud.py` to add the `reset_user_data` and transaction update functions.
- Finalized the `README.md` with complete setup instructions, feature lists, and the technology stack.
- Updated the bot's default commands list in `main.py` to expose all built commands (`/recent`, `/reset`, `/export`, etc.) directly to the Telegram UI menu.

## Commands run
```bash
git add .
git commit -m "v1.0-minimal final release"
git tag v1.0-minimal
git push origin main
git push origin v1.0-minimal
```

## Code built

`bot/handlers/recent.py`
```python
@router.message(Command("recent"))
async def cmd_recent(message: Message, state: FSMContext) -> None:
    """Show the list of recent transactions."""
    await state.clear()
    await show_recent_list(message.from_user.id, message.answer)

async def show_recent_list(telegram_id: int, send_or_edit_func) -> None:
    """Helper to display the recent transactions list."""
    transactions = await get_recent_transactions(telegram_id, limit=10)
    ...
```
This module handles retrieving the 10 most recent transactions from SQLite and presenting them as a vertically stacked list of inline buttons. Selecting a button opens the details view.

```python
@router.message(RecentFSM.waiting_for_new_amount)
async def process_new_amount(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    txn_id = data.get("edit_txn_id")
    
    try:
        new_amount = float(message.text.strip())
        ...
```
If a user taps "Edit Amount", the bot enters an FSM state waiting for numerical input. Upon receiving a valid number, it issues an `UPDATE` query to SQLite and refreshes the transaction list.

`bot/db/crud.py`
```python
async def reset_user_data(telegram_id: int) -> None:
    """Wipes all records and categories for a user, then seeds the default categories."""
    ...
        # Delete transactions
        await db.execute("DELETE FROM transactions WHERE user_id = ?", (user_id,))
        # Delete keywords
        await db.execute("DELETE FROM keywords WHERE user_id = ?", (user_id,))
        # Delete categories
        await db.execute("DELETE FROM categories WHERE user_id = ?", (user_id,))
        await db.commit()
        
    # Re-seed default categories
    await seed_categories_for_user(user_id)
```
The reset function performs a cascade delete on all user data without dropping the actual `users` row. This allows the bot to retain the user's settings (like their financial start day) while clearing out their financial history and custom keyword mappings. We then immediately call the original `seed_categories_for_user` function to restore the default state.

## Interview Q&A

**Q: Why limit `/recent` to only the last 10 transactions?**
A: Telegram limits the length of inline keyboards and messages. Sending a massive list of buttons would result in API errors or a very poor user experience. If a user needs to see older data, they can use `/stats` for aggregated data or `/export` to download their entire history.

**Q: How do you prevent accidental data deletion with `/reset`?**
A: The `/reset` command itself doesn't execute the deletion. It simply sends a warning message with an inline keyboard. The data is only deleted if the user explicitly taps the "⚠️ Yes, Wipe Everything" button, which triggers a separate callback query.

**Q: How does the edit flow work without conflicting with the main text parser from Stage 3?**
A: We use `aiogram.fsm` (Finite State Machine). When the user clicks "Edit", we set their state to `RecentFSM.waiting_for_new_amount`. Any message they type next is intercepted by this specific handler rather than falling through to the generic NLP text parser. Once the edit is saved, we clear their state (`state.clear()`) so the bot goes back to normal listening mode.

## Next Steps
This concludes the `v1.0-minimal` version of PennyPilot! The bot is fully functional, capable of processing natural language text, voice notes, and photo receipts, and it provides comprehensive tracking, charting, and export tools purely within Telegram.
