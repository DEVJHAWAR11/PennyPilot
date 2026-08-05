# Stage 16: Production Hardening & Deployment

## Overview
Stage 16 finalizes the PennyPilot bot for production deployment. This involves migrating away from local SQLite to a persistent PostgreSQL database (Supabase), transitioning from long-polling to Webhooks (using `aiohttp`), and ensuring the server stays awake on free-tier hosting providers.

## Key Upgrades

### 1. Supabase PostgreSQL Migration
Initially, PennyPilot was built using `aiosqlite` and a local `penny.db` file. While this is great for local development, it is unacceptable for cloud free-tier hosting (like Render), which uses **Ephemeral Storage**. Ephemeral storage means that every time the server spins down due to inactivity, the local disk is wiped clean and re-created from the GitHub repository, permanently deleting the SQLite database.

To solve this, the entire database layer (`bot/db/schema.py` and `bot/db/crud.py`) was rewritten to use `asyncpg` and connect to a remote, hosted Supabase PostgreSQL database. This guarantees persistent data.
- Replaced `?` parameter binding with PostgreSQL `$1` binding.
- Replaced `AUTOINCREMENT` with `SERIAL`.
- Transitioned to `asyncpg.Pool` for highly-concurrent connection pooling.

### 2. Webhook Architecture
Long-polling (using `dp.start_polling()`) requires the bot to constantly ping Telegram for updates. Cloud free-tiers monitor incoming HTTP requests to determine if a service is "active." Since polling initiates outbound requests, the hosting provider believes the server is inactive and forcibly spins it down.

To solve this, `main.py` was refactored to support **Webhooks**. By defining a `WEBHOOK_URL` in the environment variables, the bot launches an `aiohttp` web server. Telegram now actively sends HTTP POST requests to this server whenever a user sends a message.

### 3. Server Keep-Alive
Render's free tier spins down web services after 15 minutes of receiving no inbound HTTP requests. To prevent the cold-start delay (which can take 1-2 minutes and cause Telegram to timeout and retry messages), a `/health` endpoint was added to the `aiohttp` server. Users can use a free service like `cron-job.org` to ping `/health` every 14 minutes, keeping the bot awake 24/7.

## Questions and Answers

**Q: What are the real limitations of running this on a free tier?**
A: Free tiers have three primary limitations:
1. **Cold Starts:** If the server spins down, the next user to message the bot will experience a 1-2 minute delay while the server boots up. (Mitigated by the `/health` keep-alive ping).
2. **Ephemeral Disk:** As mentioned, free tiers don't save local files. If you generate PDF exports or use SQLite, those files are lost on restart. (Mitigated by migrating to Supabase).
3. **Monthly Hours:** Render provides 750 free hours a month. Since a month has 730-744 hours, keeping the bot awake 24/7 uses almost your entire quota. You cannot run multiple free services simultaneously without running out of hours.

**Q: What would you change for real production use?**
A: For a true, scaled production release:
1. **Move to a paid hosting tier:** Upgrading to a $7/mo Render instance prevents sleep, eliminates cold starts, and provides persistent disk storage, removing the need for hacky cron-job pings.
2. **Message Queuing (Celery/Redis):** Currently, if an LLM API call (like the AI Anomaly Agent) takes 30 seconds, it holds up the `asyncio` event loop or blocks the webhook response. Telegram expects a webhook response within seconds. For heavy LLM workloads, the webhook should instantly return `200 OK` and offload the actual LLM generation to a background Redis worker.
3. **Database Migrations:** Use a tool like Alembic to manage PostgreSQL schema changes safely, rather than running `CREATE TABLE IF NOT EXISTS` on startup.
