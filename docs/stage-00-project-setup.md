# Stage 00: Project Bootstrap & Git Setup

## Features implemented in this stage
- Complete project folder structure matching the prescribed layout
- Git repository initialized and connected to GitHub remote (https://github.com/DEVJHAWAR11/PennyPilot.git)
- First commit pushed to `main` branch
- Python virtual environment with initial dependencies installed (aiogram 3.30.0, aiosqlite 0.22.1, python-dotenv 1.2.2)
- `.gitignore` covering `.env`, database files, `__pycache__`, venv folders, IDE and OS files
- `.env.example` listing all environment variable names needed across the project
- `bot/config.py` — centralized config module that loads secrets from `.env`
- `README.md` with project description, tech stack, and setup instructions
- `main.py` entry point placeholder

## Commands run
```bash
git init
git remote add origin https://github.com/DEVJHAWAR11/PennyPilot.git
python -m venv venv
.\venv\Scripts\pip.exe install -r requirements.txt
.\venv\Scripts\pip.exe show aiogram aiosqlite python-dotenv
git add -A
git status
git commit -m "Set up project structure, gitignore, env template, and initial dependencies"
git branch -M main
git push -u origin main
git status
```

## Code built

### `.gitignore`
```
# Virtual environment
venv/
.venv/
env/

# Environment variables
.env

# Database files
data/*.db

# Python cache
__pycache__/
*.py[cod]
*$py.class
*.pyo

# IDE files
.vscode/
.idea/
*.swp
*.swo

# OS files
.DS_Store
Thumbs.db

# Distribution / packaging
*.egg-info/
dist/
build/

# Byte-compiled files
*.pyc
```
**What it does:** Tells Git which files and folders to never track. This is critical because some files should never end up in version control:
- `.env` contains real secrets (bot token, API keys) — if this were pushed to GitHub, anyone could steal your credentials.
- `data/*.db` is the SQLite database. It's generated at runtime and can be large. Each developer/environment creates its own.
- `__pycache__/` and `*.pyc` are compiled Python bytecode files — they're auto-generated and machine-specific.
- `venv/` is the virtual environment folder with all installed packages. It can be hundreds of megabytes and is recreated via `pip install -r requirements.txt`.

**Why it's built this way:** We list patterns, not individual files. For example, `data/*.db` catches any `.db` file inside `data/`, so future databases are also ignored without updating `.gitignore`.

---

### `.env.example`
```
# Bot Configuration
BOT_TOKEN=your-telegram-bot-token-here

# Groq API (used for voice transcription and receipt photo extraction)
GROQ_API_KEY=your-groq-api-key-here
```
**What it does:** This is a *template* for the `.env` file. It lists every environment variable the project needs, with dummy placeholder values. A new developer cloning the repo copies this to `.env` and fills in real values.

**Why it's built this way:** The actual `.env` is gitignored (for security), so without `.env.example`, a new developer would have no idea which variables to set. This file acts as documentation — it's a living reference that we update whenever we add a new secret.

---

### `requirements.txt`
```
aiogram>=3.0,<4.0
aiosqlite>=0.19.0
python-dotenv>=1.0.0
```
**What it does:** Lists all Python packages the project depends on, with version constraints. Running `pip install -r requirements.txt` installs them.

**Why it's built this way:**
- `aiogram>=3.0,<4.0` means "any version of aiogram 3.x, but not 4.x." This is called a *compatible release* constraint. We pin to the major version because aiogram 3 and aiogram 2 have completely different APIs (different import paths, different function names). But within 3.x, updates are safe.
- Same logic for the other packages — we set a minimum version we've tested with, but allow minor/patch updates.
- More dependencies (matplotlib, reportlab, groq) will be added in later stages as we need them.

---

### `bot/__init__.py`
```python
# bot package
```
**What it does:** This file makes the `bot/` directory a Python package. Without it, Python would not recognize `bot` as a module, and you couldn't write `from bot.config import BOT_TOKEN`.

**Why it's built this way:** The file is nearly empty because it doesn't need to do anything — its mere existence is what matters. The comment is just for clarity. The same applies to `__init__.py` files in `handlers/`, `parser/`, `db/`, and `services/`.

---

### `bot/config.py`
```python
"""
Configuration module — loads environment variables from .env file.
"""

import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
```
**What it does:** This is the single place where all secrets and configuration values are loaded. It reads the `.env` file (via `load_dotenv()`), then exposes each value as a simple Python variable.

**Why it's built this way:**
- `load_dotenv()` reads the `.env` file and loads each `KEY=VALUE` pair into the process's environment variables.
- `os.getenv("BOT_TOKEN")` then reads that environment variable. If the `.env` file is missing or the key isn't set, it returns `None` — we'll add validation later.
- Having a single `config.py` means no other file in the project needs to know about `.env` or `os.getenv`. They just `from bot.config import BOT_TOKEN`. If we ever switch to a different config mechanism, only this one file changes.

---

### `main.py`
```python
"""
PennyPilot — Telegram Expense Tracker Bot

Entry point. Starts the bot using aiogram's polling mechanism.
"""
```
**What it does:** Currently just a placeholder docstring. In Stage 1, this will contain the actual bot startup code — creating the aiogram Bot and Dispatcher objects, registering handlers, and starting the polling loop.

**Why it's built this way:** We create it now (even though it's empty) so the folder structure is complete from day one. This makes the first commit a clean "here's the skeleton" snapshot.

---

### `data/.gitkeep` and `docs/.gitkeep`
```
# This directory holds the SQLite database file (expenses.db).
# The .db file is gitignored — it's created at runtime.
```
**What they do:** Git does not track empty directories. If we want `data/` and `docs/` to exist in the repo (so the folder structure is visible to anyone who clones it), we need at least one tracked file inside each. `.gitkeep` is a widely-used convention for this — it's not a Git feature, just a naming convention.

---

### `README.md`
```markdown
# PennyPilot — Telegram Expense Tracker Bot
...
```
**What it does:** The front page of the GitHub repository. It describes what the project is, lists the tech stack, and gives setup instructions. This is the first thing a recruiter or interviewer sees.

**Why it's built this way:** We start with a minimal but complete README now and will expand it significantly in Stage 10 with screenshots and a full feature list.

---

### Folder structure overview
```
PennyPilot/
├── bot/
│   ├── __init__.py          # Makes bot/ a Python package
│   ├── handlers/            # Will hold one file per command group
│   │   └── __init__.py
│   ├── parser/              # Will hold deterministic text/date parsing
│   │   └── __init__.py
│   ├── db/                  # Will hold schema + CRUD functions
│   │   └── __init__.py
│   ├── services/            # Will hold Whisper, vision, charts, exports
│   │   └── __init__.py
│   └── config.py            # Loads .env, exposes config variables
├── docs/                    # One file per stage (documentation)
│   └── .gitkeep
├── data/                    # SQLite database lives here at runtime
│   └── .gitkeep
├── .env.example             # Template for .env
├── .gitignore               # Files Git should never track
├── requirements.txt         # Python dependencies
├── main.py                  # Bot entry point
└── README.md                # Project description
```

## Interview Q&A

**Q: Why did you choose SQLite instead of PostgreSQL or MySQL for this project?**
A: SQLite is a file-based database — it doesn't need a separate server process. For a personal Telegram bot serving one user (or a small number of users), SQLite is plenty fast and has zero infrastructure cost. There's no database server to install, configure, or pay for. The entire database lives in a single file (`data/expenses.db`). If the project ever scales to thousands of concurrent users, we could migrate to PostgreSQL, but for a free-tier personal finance bot, SQLite avoids unnecessary complexity. It also makes development simpler — clone the repo, run the bot, and the database is created automatically.

**Q: Why is `.env` gitignored? What would happen if you accidentally committed it?**
A: The `.env` file contains real secrets — your Telegram bot token and your Groq API key. If this file were committed and pushed to GitHub, anyone browsing the repo could steal those credentials. With the bot token, someone could impersonate your bot and read all messages sent to it. With the Groq API key, someone could make API calls on your account and exhaust your free-tier quota. Gitignoring `.env` is a security best practice. We provide `.env.example` with placeholder values so developers know which variables to set without exposing real secrets.

**Q: Why do you have a `.env.example` file if `.env` is gitignored?**
A: Without `.env.example`, a new developer cloning the repo would have no idea what environment variables the project expects. They'd have to read through the code, find every `os.getenv()` call, and guess the variable names. `.env.example` acts as self-documenting configuration — it lists every required variable with a placeholder value and comments explaining what each one is for. The developer copies it to `.env` and fills in real values.

**Q: What does `__init__.py` do, and why is it in every subdirectory?**
A: In Python, `__init__.py` marks a directory as a *package* — a collection of modules that can be imported. Without it, Python treats the directory as a regular folder and you can't write `from bot.handlers import something`. The file can be empty (or contain just a comment) — its existence is what matters. We have it in `bot/`, `bot/handlers/`, `bot/parser/`, `bot/db/`, and `bot/services/` so each of these is importable as a Python package.

**Q: Why separate `handlers` from `services` from `db`? Why not put everything in one file?**
A: This is called *separation of concerns*. Each directory has a single responsibility:
- `handlers/` deals with Telegram-specific logic: receiving messages, parsing commands, sending replies.
- `services/` deals with external integrations: calling the Groq API for voice transcription, generating charts with matplotlib, creating PDF reports.
- `db/` deals with data storage: the SQLite schema and CRUD (Create, Read, Update, Delete) functions.
This means a change to how we generate charts doesn't touch the Telegram command handlers. A change to the database schema doesn't touch the Groq API integration. It makes the code easier to understand, test, and modify. In an interview, this shows you understand architectural separation, not just "make it work."

**Q: Why use `aiogram` instead of `python-telegram-bot` or another Telegram library?**
A: `aiogram` is fully asynchronous — it uses Python's `async/await` syntax. This matters because a Telegram bot spends most of its time waiting: waiting for the Telegram API to respond, waiting for the database query to return, waiting for the Groq API to transcribe audio. With async code, the bot can handle another user's message while it waits, instead of blocking. `python-telegram-bot` also has an async mode now, but `aiogram` was designed async-first from the ground up, and its middleware and routing system is more modern. For a project showcasing async Python skills in interviews, `aiogram` is the stronger choice.

**Q: What does `python-dotenv` do, and why not just use `os.environ` directly?**
A: `os.environ` reads environment variables that are already set in your system's shell. But during development, you don't want to set system-wide environment variables for every project — it's messy and error-prone. `python-dotenv` reads a `.env` file (a simple text file with `KEY=VALUE` lines) and loads those values into the process's environment. This way, each project has its own `.env` file with its own config, completely isolated. In production (like on a server), you'd set real environment variables, and `load_dotenv()` gracefully does nothing if there's no `.env` file — the code works in both scenarios without changes.

**Q: Why use version constraints like `>=3.0,<4.0` in requirements.txt instead of pinning exact versions?**
A: Pinning an exact version (like `aiogram==3.30.0`) means you never get bug fixes or security patches unless you manually update. Using `>=3.0,<4.0` means "any version in the 3.x series." Within a major version, libraries follow *semantic versioning* — minor and patch updates add features and fix bugs without breaking your code. A major version bump (3 → 4) can introduce breaking changes, which is why we cap at `<4.0`. This gives us the sweet spot: we get automatic security patches and bug fixes, but we're protected from breaking API changes.

**Q: What is `.gitkeep` and is it a Git feature?**
A: `.gitkeep` is not a Git feature — it's a community convention. Git only tracks files, not empty directories. If you want an empty directory (like `data/` or `docs/`) to exist in the repo so other developers see the intended structure, you put a small file inside it. The name `.gitkeep` signals "this file exists only to keep this directory in Git." You could name it anything, but `.gitkeep` is the universally recognized convention.

**Q: Why is the `parser` a separate package instead of being part of `handlers`?**
A: The parser converts raw user input (like `"45 groceries yesterday"`) into structured data (amount=45, category="Groceries", date=yesterday). This logic is pure Python — it doesn't know anything about Telegram, databases, or APIs. Keeping it separate means: (1) we can unit test the parser without setting up a Telegram bot or a database, (2) multiple handlers can reuse the same parser (text messages, voice transcription results, and receipt extraction results all feed into the same parser), and (3) if we ever want to use this logic outside Telegram (say, in a web app), we can import `bot.parser` without pulling in Telegram dependencies.

**Q: What's the `data/` folder for? Why not put the database file next to `main.py`?**
A: Putting the database in `data/` is an organizational choice. It separates runtime-generated files from source code. When you look at the project root, you see code files — `main.py`, `bot/`, `requirements.txt`. The `data/` directory clearly signals "files generated at runtime, not part of the source code." This also makes the `.gitignore` cleaner: `data/*.db` ignores all databases in one pattern. If the database were in the root, you'd need to ignore it by exact name, and it would clutter the project listing.

**Q: Walk me through what happens when a developer clones this repo and sets it up for the first time.**
A: They would: (1) `git clone` the repo to get all the source files. (2) Create a virtual environment with `python -m venv venv` — this isolates the project's dependencies from their system Python. (3) Activate the venv (`.\venv\Scripts\activate` on Windows, `source venv/bin/activate` on Mac/Linux). (4) Run `pip install -r requirements.txt` to install aiogram, aiosqlite, and python-dotenv into the venv. (5) Copy `.env.example` to `.env` and fill in their real bot token and Groq API key. (6) Run `python main.py` to start the bot. The database file is created automatically on first run. No database setup, no server configuration — that's the benefit of SQLite and a well-organized project.

**Q: Why use a virtual environment? What problems does it solve?**
A: Without a virtual environment, `pip install` puts packages into your system-wide Python. If Project A needs `aiogram 3.x` and Project B needs `aiogram 2.x`, they'd conflict — you can only have one version installed globally. A virtual environment creates an isolated Python installation for each project. Each venv has its own `site-packages` directory, so Project A and Project B can have different versions of the same library without conflict. It also means you can exactly reproduce the project's environment with `pip install -r requirements.txt` on any machine.

**Q: You committed and pushed in one step. In a team setting, would you do anything differently?**
A: In a team, I'd use feature branches and pull requests. Instead of committing directly to `main`, I'd create a branch like `stage-0-bootstrap`, make my commits there, push the branch, open a pull request, and wait for a code review before merging. For this solo project, committing directly to `main` is fine — I'm the only contributor, and the staged approach (with verification at each stage) acts as my quality gate. But I'd mention the PR workflow in an interview to show I know team practices.
