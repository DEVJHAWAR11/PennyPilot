# PennyPilot 🚁

A lightweight, agentic Telegram bot for tracking expenses and income seamlessly. Built with Python and `aiogram`, it allows you to log transactions via text, voice, or photo receipts.

## Features

- **Text Logging:** Send messages like `45 groceries` or `2500 salary`.
- **Voice Logging:** Send a voice note (powered by Groq Whisper).
- **Receipt Parsing:** Send a photo of a receipt to extract the total amount (powered by Groq Vision).
- **Categories:** Add, rename, and delete custom categories, and map keywords to them.
- **Charts & Stats:** View monthly breakdowns, pie charts, and net balance.
- **Exports:** Download your financial history as a CSV or a monthly PDF statement.
- **Recent:** View and edit your most recent transactions.
- **No Spreadsheets:** Stop wrangling formulas and let the bot do the work.

## Tech Stack

- **Python 3.11+**
- **aiogram (v3)** — Modern async Telegram bot framework
- **asyncpg** — High-performance async PostgreSQL driver
- **matplotlib** — For generating in-memory pie charts
- **reportlab** — For generating PDF financial statements
- **Groq API** — For fast, free-tier voice transcription and vision extraction

## Setup Instructions

1. Clone this repository:
   ```bash
   git clone https://github.com/DEVJHAWAR11/PennyPilot.git
   cd PennyPilot
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On Linux/Mac:
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Configure your Environment Variables:
   - Copy `.env.example` to `.env`
   - Get a bot token from [@BotFather](https://t.me/BotFather) on Telegram and set `BOT_TOKEN`.
   - Get an API key from [Groq Console](https://console.groq.com) and set `GROQ_API_KEY`.
   - Setup a PostgreSQL database (e.g., Supabase) and set `DATABASE_URL`.
   - (Optional) Set `WEBHOOK_URL` to deploy with `aiohttp` webhooks on cloud platforms.

4. Run the Bot:
   ```bash
   python main.py
   ```

## Usage

Start a chat with your bot on Telegram and send `/start`.

**Commands:**
- `/categories` - Manage your income and expense categories.
- `/balance` - Check your current month's net balance and savings rate.
- `/stats` - View past months and generate visual pie charts.
- `/export` - Download a CSV or PDF of your finances.
- `/recent` - View and edit your latest transactions.
- `/settings` - Configure when your financial month starts.
- `/help` - View help documentation.

## Project Status

✅ Fully complete. Ready for production deployment on Render.
