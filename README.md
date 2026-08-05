# PennyPilot: Advanced Agentic Finance Bot

🤖 **Try the live bot here: [@PennyPilot_bot](https://t.me/PennyPilot_bot)**

## Problem Statement
Personal finance apps are inherently frictionless to install but incredibly high-friction to maintain. Users forget to log expenses, find it tedious to manually enter data, and struggle to query their own spending habits. PennyPilot solves this by bringing expense tracking directly into the platform where users already spend their time: Telegram. By combining deterministic parsing for quick logs and advanced LLM agentic flows for voice inputs, natural language queries, and anomaly detection, it provides a frictionless, autonomous financial assistant.

## Features List

### Input Methods
- **Quick Text Logging**: Fast, deterministic regex parsing for standard entries (e.g., "200 food").
- **Voice Memos**: Send an audio note ("I spent 400 on swiggy") and Whisper API transcribes it.
- **Image Parsing**: Upload a receipt and the bot automatically extracts the amount and category.

### Agentic Capabilities (LLM-Driven)
- **Natural Language Queries**: Ask complex questions ("How much did I spend on food this month?") and the AI agent retrieves data via MCP tools to answer.
- **Autonomous Anomaly Alerting**: A scheduled background job that analyzes recent spending patterns, detects anomalies (e.g., spending 50% more on food than usual), and proactively messages the user.
- **Automated Monthly Summaries**: Automatically generates and sends a summary report on the 1st of every month.

### System & Management
- **Category Management**: Create, delete, and customize categories with emojis.
- **Visual Analytics**: In-memory generation of pie charts to visualize spending distribution.
- **Data Export**: Export entire transaction history to CSV, or generate a formatted PDF statement for any month.
- **Zero-Downtime Resilience**: Deployed via Webhooks on Render with a separate worker database pool configured to respect free-tier constraints.

## Tech Stack
| Component | Technology | Purpose |
| --- | --- | --- |
| **Language** | Python 3.11+ | Core application logic. |
| **Bot Framework** | aiogram (v3) | Async handling of Telegram webhooks and commands. |
| **Database** | Supabase (PostgreSQL) | Persistent, cloud-hosted relational database. |
| **DB Driver** | asyncpg | High-performance async driver with pool limits. |
| **Agent Framework**| LangGraph | Orchestrates the AI agent's decision-making loop. |
| **Tooling Protocol**| MCP (FastMCP) | Standardized, isolated tool execution in a background process. |
| **LLM Provider** | Groq API | Fast, free-tier access for LLaMA 3 and Whisper. |
| **Scheduling** | APScheduler | Background cron jobs for anomalies and summaries. |
| **Data Viz** | matplotlib / reportlab | Chart and PDF generation in-memory. |

## Architecture Diagram
```text
┌────────────────┐      (Webhook)       ┌────────────────────────┐
│ Telegram Cloud │ ───────────────────> │ aiohttp Webhook Server │
└────────────────┘                      └──────────┬─────────────┘
                                                   │
    ┌──────────────────────────────────────────────┴───────────────────────────────────────────┐
    │                                aiogram Dispatcher                                        │
    └──────────┬─────────────────────────────┬───────────────────────────┬─────────────────────┘
               │                             │                           │
      [Deterministic Flow]          [Scheduled Background]       [Agentic Flow (LangGraph)]
     Regex Parsers / Menus           APScheduler (Cron)          ┌───────────────────────┐
               │                             │                   │   LangGraph Agent     │
               │                             │                   │  (LLaMA 3 via Groq)   │
               │                             │                   └──────────┬────────────┘
               │                             │                              │  Tool Calls
               │                             │                              V 
               │                             │                   ┌───────────────────────┐
               │                             │                   │      MCP Server       │
               │                             │                   │ (Background Process)  │
               └─────────────────────────────┼───────────────────┴───────────────────────┘
                                             │
                                   ┌─────────V──────────┐
                                   │ asyncpg Conn Pool  │
                                   └─────────┬──────────┘
                                             V
                                   ┌────────────────────┐
                                   │ Supabase Postgres  │
                                   └────────────────────┘
```

## Setup Instructions
1. **Clone the repo**
   ```bash
   git clone https://github.com/DEVJHAWAR11/PennyPilot.git
   cd PennyPilot
   ```
2. **Install Dependencies**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. **Environment Variables**
   Create a `.env` file:
   ```env
   BOT_TOKEN=your_telegram_bot_token
   GROQ_API_KEY=your_groq_api_key
   DATABASE_URL=postgresql://user:pass@pooler.supabase.com:6543/postgres
   WEBHOOK_URL=https://your-render-app.onrender.com/webhook
   ```
4. **Run Locally**
   *(Remove `WEBHOOK_URL` to run in local polling mode)*
   ```bash
   python main.py
   ```

## Deployment & Free-Tier Limitations
- **Render Zero-Downtime:** This bot is configured to safely handle Render's blue-green deployments without race conditions on Telegram's `setWebhook` endpoint.
- **Supabase Limits:** The `asyncpg` pool is strictly capped at `max_size=5` to prevent exhausting the Supabase free-tier session limit (15) during rolling deployments.
- **File System:** All charts and PDFs are generated purely in-memory (using `io.BytesIO`) to respect Render's ephemeral filesystem.
