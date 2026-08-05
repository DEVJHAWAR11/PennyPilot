# PennyPilot — Telegram Expense Tracker Bot

A Telegram bot that lets you log income and expenses by sending a plain message, voice note, or receipt photo. Get back balances, category stats, charts, and exports — all running on free-tier infrastructure.

## Tech Stack

- **Language:** Python 3.11+
- **Telegram Framework:** aiogram (async)
- **Database:** SQLite via aiosqlite
- **Voice Transcription:** Groq API (Whisper model)
- **Receipt Extraction:** Groq vision-capable model
- **Charts:** matplotlib
- **PDF Statements:** ReportLab
- **CSV Export:** Python built-in csv module

## Setup

1. Clone this repo
2. Create a virtual environment and activate it
3. Install dependencies: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and fill in your real values
5. Run the bot: `python main.py`

## Project Status

🚧 Under active development — Stage 0 (Project Bootstrap) complete.
