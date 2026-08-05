# Stage 07: Balance & Stats

## Features implemented in this stage
- **Date Utilities (`bot/utils/dates.py`)**: Introduced `get_financial_month` and `get_past_financial_months` to calculate start and end boundaries for periods based on a user's custom `month_start_day`.
- **Settings Handler (`/settings`)**: Created an interactive inline keyboard menu to change the financial month start day (1 to 28). This persists to the `users` table.
- **Balance Handler (`/balance`)**: Calculates the total income, expenses, net balance, and savings rate for the current financial period.
- **Stats Handler (`/stats`)**: Shows a menu of the past 6 financial periods. Tapping a period reveals a category breakdown with percentages, sorted from highest to lowest expense.
- **Telegram Menu Button (`main.py`)**: Added `setup_bot_commands` using `bot.set_my_commands()` to populate the native Telegram menu button with all available bot commands.
- **Localization (`bot/handlers/stats.py`)**: Changed currency formatting across `/balance` and `/stats` outputs to use the Indian Rupee symbol (₹).

## Integration Notes
- Relies on `python-dateutil` for clean relative month calculations across years and varying month lengths.
- Used the existing `get_transactions_for_period` query from `crud.py`.

## How to Test
1. Send `/settings` and tap a new start day (e.g., 15) to change your financial month cycle.
2. Send `/balance` to see your income, expenses, and net balance for the newly calculated month period.
3. Send `/stats` to see the last 6 months. Tap any month to view the category-by-category percentage breakdown of your spending.

## Next Steps
- Implement chart generation for `/stats` to visually represent the category breakdown (Stage 8).

## Q&A and Troubleshooting
**Q: Where do we set our incomes? Is it dummy data?**
**A:** No, it's not dummy data! You can log income exactly the same way as an expense. Simply send a message like `2500 salary`. As long as "salary" is mapped to a category that has `type="income"` (like the default "Salary" category), the bot will automatically log it as positive income, which will show up correctly in `/balance`.

**Q: Users can't see the available commands in Telegram.**
**A:** To fix this, we updated `main.py` to call `bot.set_my_commands()` on startup. This automatically pushes our command list to Telegram so a native "Menu" button appears next to the chat box for all users.
