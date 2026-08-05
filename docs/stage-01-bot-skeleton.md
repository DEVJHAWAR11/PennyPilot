# Stage 01: Telegram Bot Skeleton

## Features implemented in this stage
- Bot connects to Telegram via long-polling using aiogram 3.30.0
- `/start` command — sends a welcome message explaining how to log transactions
- `/help` command — lists available commands and usage instructions
- Handler code separated into its own file using aiogram's Router pattern
- Bot token validation at startup — exits with a clear error if token is missing
- Structured logging to stdout so you can see every update the bot handles

## Commands run
```bash
.\venv\Scripts\pip.exe show aiogram aiosqlite python-dotenv
# (verified installed versions: aiogram 3.30.0, aiosqlite 0.22.1, python-dotenv 1.2.2)

git add -A
git commit -m "Wired up the /start and /help command handlers with aiogram polling"
.\venv\Scripts\python.exe main.py
# (bot started, sent /start in Telegram, confirmed reply arrived)

git push
```

## Code built

### `bot/handlers/commands.py`
```python
"""
Command handlers — /start and /help for the bot skeleton.
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    """Greet the user and explain what the bot does."""
    await message.answer(
        "Hey! 👋 I'm PennyPilot — your personal expense tracker.\n\n"
        "Send me an amount and what it was for, like:\n"
        "• `45 groceries`\n"
        "• `2500 salary`\n"
        "• `200 beer 2025-01-15`\n\n"
        "I'll log it instantly. You can also send a 🎙 voice note "
        "or a 📸 receipt photo and I'll figure it out.\n\n"
        "Type /help to see everything I can do.",
        parse_mode="Markdown",
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Show available commands."""
    await message.answer(
        "📖 *Here's what I can do:*\n\n"
        "*Log a transaction* — just send a message like `45 groceries` "
        "or `2500 salary`.\n\n"
        "*Commands:*\n"
        "/start — Welcome message\n"
        "/help — This help menu\n\n"
        "🚧 More commands coming soon — categories, balance, stats, "
        "charts, exports, and more!",
        parse_mode="Markdown",
    )
```

**What it does:**
This file defines two Telegram command handlers — functions that run when a user sends `/start` or `/help` to the bot.

**How it works, line by line:**

- `from aiogram import Router` — A `Router` is aiogram 3's way of grouping related handlers together. Think of it like a mini-app. Instead of registering every handler directly on the main Dispatcher, you create a Router in each file and register handlers on it. Then the main file includes that router into the dispatcher.

- `from aiogram.filters import Command` — `Command` is a built-in filter that matches messages starting with `/`. When you write `@router.message(Command("start"))`, aiogram will only call that function if the incoming message is exactly `/start`.

- `from aiogram.types import Message` — `Message` is the type representing a Telegram message. It gives you access to the message text, the sender's user ID, a method to reply (`message.answer()`), and more.

- `router = Router()` — Creates a new router instance. All handlers in this file register on this router. Later, `main.py` includes this router into the dispatcher.

- `@router.message(Command("start"))` — This decorator tells aiogram: "When a message arrives and it matches the `/start` command, call the function below." The `@` syntax is Python's decorator pattern — it wraps the function with extra behavior (in this case, registering it as a handler).

- `async def cmd_start(message: Message) -> None:` — The handler is an `async` function because Telegram bot operations (sending replies, downloading files) involve network I/O. Using `async/await` lets the bot handle other users' messages while waiting for the network, instead of blocking.

- `await message.answer(...)` — Sends a reply to the user in the same chat. `answer()` is a convenience method on `Message` — it automatically knows which chat to send to. The `await` keyword is required because sending a message is a network call to the Telegram API.

- `parse_mode="Markdown"` — Tells Telegram to render the reply with Markdown formatting. Backticks become inline code, asterisks become bold, etc.

**Why it's built this way:**
The Router pattern keeps handler files independent. This file knows nothing about the bot token, the database, or other handlers. As the project grows (Stage 3 adds a text parser handler, Stage 5 adds voice, Stage 6 adds photos), each gets its own file with its own router, and `main.py` just includes them all. This is the same pattern used in web frameworks like Flask's Blueprints or Express's Router.

---

### `main.py`
```python
"""
PennyPilot — Telegram Expense Tracker Bot

Entry point. Creates the Bot and Dispatcher, registers handler routers,
and starts polling for updates from Telegram.
"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher

from bot.config import BOT_TOKEN
from bot.handlers.commands import router as commands_router


def main() -> None:
    """Set up logging, build the bot, register routers, and start polling."""

    # Configure logging so we can see what's happening in the console
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )

    # Validate that the bot token is set
    if not BOT_TOKEN:
        logging.error(
            "BOT_TOKEN is not set. "
            "Copy .env.example to .env and fill in your Telegram bot token."
        )
        sys.exit(1)

    # Create the bot and dispatcher
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Register handler routers
    dp.include_router(commands_router)

    # Start polling (blocks until stopped with Ctrl+C)
    logging.info("PennyPilot is starting...")
    asyncio.run(dp.start_polling(bot))


if __name__ == "__main__":
    main()
```

**What it does:**
This is the entry point — the file you run with `python main.py` to start the bot. It wires everything together: creates the bot object, attaches all handler routers, and starts listening for messages.

**How it works, step by step:**

1. **Logging setup** — `logging.basicConfig(...)` configures Python's built-in logging module to print timestamped messages to the console. This is how you see lines like `2026-08-05 10:10:24 [INFO] aiogram.dispatcher: Start polling`. Without this, you'd have no visibility into what the bot is doing.

2. **Token validation** — `if not BOT_TOKEN:` checks whether the token was loaded from `.env`. If someone clones the repo and forgets to create `.env`, the bot exits immediately with a clear error message instead of crashing with a cryptic Telegram API error.

3. **`Bot(token=BOT_TOKEN)`** — Creates an aiogram `Bot` instance. This object represents your bot's connection to the Telegram API. It holds the token and provides methods like `send_message()`, `download()`, etc.

4. **`Dispatcher()`** — The Dispatcher is the brain of the bot. It receives incoming updates from Telegram, figures out which handler should process each update (based on filters like `Command("start")`), and calls the right handler function.

5. **`dp.include_router(commands_router)`** — Registers the router from `bot/handlers/commands.py` into the dispatcher. As we add more handler files in later stages, we'll add more `include_router()` calls here.

6. **`asyncio.run(dp.start_polling(bot))`** — This is what actually starts the bot. `start_polling()` enters an infinite loop: it calls Telegram's `getUpdates` API, receives any new messages, dispatches them to handlers, then calls `getUpdates` again. `asyncio.run()` wraps this in Python's async event loop. The program blocks here until you press Ctrl+C.

**Why it's built this way:**
- **Polling, not webhooks** — Polling is simpler for development. The bot calls Telegram repeatedly ("any new messages?"). Webhooks require a public HTTPS URL, which we don't have yet. Polling works on any machine, behind any firewall, with no server setup.
- **Dispatcher doesn't take bot in constructor** — This is an aiogram 3.x design decision. The bot is passed to `start_polling()` instead. This allows one dispatcher to work with multiple bots if needed.
- **`main()` is a regular function, not async** — We use `asyncio.run()` inside it to start the async event loop. This keeps the entry point simple and compatible with `if __name__ == "__main__"`.

---

### `.env` (not committed — gitignored)
```
# Bot Configuration
BOT_TOKEN=<your-real-token-here>

# Groq API (used for voice transcription and receipt photo extraction)
GROQ_API_KEY=your-groq-api-key-here
```
**What it does:** Holds the real bot token. Loaded by `bot/config.py` using `python-dotenv`. This file is never committed to Git.

## Interview Q&A

**Q: What is "polling" and how does it differ from webhooks?**
A: Polling means the bot repeatedly asks Telegram "do you have any new messages for me?" in a loop. It's a pull model — the bot initiates every request. Webhooks are a push model — you give Telegram a public HTTPS URL, and Telegram sends new messages to that URL as they arrive. Polling is simpler (no server needed, works behind firewalls, great for development), but slightly less efficient because of the constant asking. Webhooks are better for production because they're instant and use fewer resources, but they require a public server with SSL. We use polling here because it works anywhere with no setup. (See `main.py`, the `dp.start_polling(bot)` call.)

**Q: What does `async def` mean and why are all the handlers async?**
A: `async def` defines a coroutine — a function that can be paused and resumed. When the bot sends a reply with `await message.answer(...)`, it makes a network call to Telegram's API server. That call might take 100-500 milliseconds. With a regular `def`, the entire bot would freeze during that wait — no other messages could be processed. With `async def` and `await`, Python pauses that specific handler, goes to handle another user's message, and comes back when the network call finishes. This is called concurrency (not parallelism — it's one thread doing many things by switching smartly). It's the reason aiogram can handle many users simultaneously without multi-threading. (See `bot/handlers/commands.py`, every handler is `async def`.)

**Q: What is a Router in aiogram 3.x and why use it instead of registering handlers directly on the Dispatcher?**
A: A Router is a container for a group of related handlers. You could register every handler directly on the Dispatcher, but as the bot grows (text parsing, voice, photos, categories, stats), that would mean one massive file with dozens of handlers all mixed together. The Router pattern lets you split handlers into separate files — one for commands, one for text parsing, one for voice, etc. Each file creates its own Router, registers its handlers on it, and the main file includes all routers into the Dispatcher with `dp.include_router()`. It's the same concept as Flask's Blueprints — modular, organized, and each file can be understood independently. (See `bot/handlers/commands.py` where the router is created, and `main.py` where it's included.)

**Q: Why validate the bot token at startup instead of letting aiogram crash on its own?**
A: Without validation, if someone forgets to create `.env`, the bot would crash with `aiogram.exceptions.TelegramUnauthorizedError: Telegram server says - Unauthorized`. That error tells you nothing about what went wrong — you'd have to trace through the code to realize the token is missing. Our validation in `main.py` catches this early and prints a clear, human-readable error: "BOT_TOKEN is not set. Copy .env.example to .env and fill in your Telegram bot token." This is called a "fail fast" pattern — detect problems as early as possible and give actionable error messages. It saves debugging time for anyone setting up the project. (See `main.py`, lines 30-35.)

**Q: What does `message.answer()` do vs `bot.send_message()`?**
A: Both send a message, but `message.answer()` is a convenience method on the `Message` object. It automatically knows which chat to reply to (it uses `message.chat.id` internally). With `bot.send_message()`, you'd have to manually specify the chat ID: `await bot.send_message(chat_id=message.chat.id, text="Hello")`. Using `message.answer()` is shorter, less error-prone, and more readable. They're functionally identical — `answer()` just wraps `send_message()` with the chat ID pre-filled. (See `bot/handlers/commands.py`, every handler uses `message.answer()`.)

**Q: What does `parse_mode="Markdown"` do in `message.answer()`?**
A: By default, Telegram treats message text as plain text — no formatting. Setting `parse_mode="Markdown"` tells Telegram to interpret Markdown syntax in the message: `*bold*` becomes **bold**, backtick-wrapped text becomes `inline code`, etc. Telegram supports two markup languages — "Markdown" (simpler, the one we use) and "MarkdownV2" (stricter, requires escaping special characters). We use the simpler one because our messages don't need advanced formatting. If we had special characters like dots or dashes in formatted text, we'd switch to MarkdownV2 or HTML parse mode. (See `bot/handlers/commands.py`, the `parse_mode` argument.)

**Q: What happens if two users send /start at the exact same time?**
A: Both messages are handled correctly without any conflict. Here's why: aiogram's polling fetches a batch of updates from Telegram, then processes each one as a separate coroutine on Python's async event loop. Since our `/start` handler doesn't access any shared state (no database reads/writes, no global variables being modified), there's no risk of a race condition. Each handler call gets its own `message` object pointing to a different user and chat. Even when we add database access in later stages, `aiosqlite` handles concurrent access safely because SQLite uses file-level locking. (See `main.py`, `dp.start_polling(bot)` handles the event loop.)

**Q: Why use `logging` instead of `print()` statements?**
A: `print()` gives you no control — every message looks the same, you can't filter by severity, and you can't redirect output easily. Python's `logging` module gives you: (1) severity levels (DEBUG, INFO, WARNING, ERROR) so you can filter noise in production, (2) timestamps on every message so you can trace when things happened, (3) the logger name (like `aiogram.dispatcher`) so you know which component logged it, and (4) easy redirection to files, external services, etc. In our setup, `logging.basicConfig(level=logging.INFO)` shows INFO and above but hides DEBUG-level noise. In production, you'd change this to WARNING to only see problems. (See `main.py`, the `logging.basicConfig(...)` call.)

**Q: What does `if __name__ == "__main__"` do and why is it needed?**
A: This is a Python idiom. When you run `python main.py`, Python sets the special variable `__name__` to `"__main__"` for that file. But if another file imports `main.py` (like `from main import something`), `__name__` would be `"main"` instead. The `if __name__ == "__main__"` guard ensures that `main()` only runs when you execute the file directly, not when it's imported. Without this guard, importing `main.py` from anywhere would immediately start the bot — which is never what you want. It's a standard Python best practice for any file that can be both run and imported. (See `main.py`, last two lines.)

**Q: Why did you put the bot token in `.env` instead of passing it as a command-line argument or hardcoding it in config.py?**
A: Three options, three problems: (1) Hardcoding in `config.py` means the token is in your source code, visible in git history forever — a security disaster. (2) Command-line arguments (`python main.py --token=XXX`) mean the token appears in shell history and process listings (anyone running `ps aux` on the server could see it). (3) A `.env` file is readable only by the file owner, is gitignored so it never enters version control, and is loaded automatically by `python-dotenv`. It's the industry standard for managing secrets in development. In production, you'd use actual environment variables set by the deployment platform (Heroku, Railway, etc.) — and `os.getenv()` reads those too, so the same code works. (See `bot/config.py` for the loading, and `.env.example` for the template.)

**Q: Explain the flow from when a user sends /start to when they see the reply.**
A: Here's the exact sequence: (1) The user types `/start` in Telegram and hits send. (2) Telegram's servers receive the message and store it as an "update." (3) Our bot's `dp.start_polling(bot)` loop calls Telegram's `getUpdates` API and receives this update. (4) The Dispatcher inspects the update — it's a message, so it checks all registered message handlers' filters. (5) The `Command("start")` filter on `cmd_start` matches, so the Dispatcher calls `cmd_start(message)`. (6) Inside `cmd_start`, `await message.answer(...)` makes an HTTP POST to Telegram's `sendMessage` API with the reply text and the chat ID. (7) Telegram's servers receive the `sendMessage` call and deliver the reply to the user's Telegram app. The whole round trip typically takes 200-800ms. (See `bot/handlers/commands.py` for step 5-6, and `main.py` for step 3-4.)

**Q: What would you change if this bot needed to handle 10,000 users simultaneously?**
A: Several things: (1) Switch from polling to webhooks — polling creates unnecessary load at scale because you're constantly asking Telegram for updates even when there are none. Webhooks push updates instantly. (2) Switch from SQLite to PostgreSQL — SQLite locks the entire database file on writes, which becomes a bottleneck with many concurrent users. PostgreSQL handles concurrent writes with row-level locking. (3) Deploy behind a reverse proxy like nginx with HTTPS (required for webhooks). (4) Add connection pooling for the database. (5) Consider Redis for caching frequently accessed data like category lookups. But for a personal finance bot with a handful of users, these are premature optimizations — SQLite and polling are perfectly adequate and much simpler to operate.
