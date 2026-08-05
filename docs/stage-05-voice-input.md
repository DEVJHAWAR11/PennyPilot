# Stage 05: Voice Input

## Features implemented in this stage
- **Voice Message Handler (`bot/handlers/voice.py`)**: A dedicated handler that catches Telegram voice notes, downloads them into an in-memory buffer, and passes them to an AI transcription service.
- **Groq Whisper Integration**: Uses the `whisper-large-v3` model via the Groq API for near-instant, highly accurate speech-to-text transcription.
- **Unified Parsing Pipeline**: The transcribed text is fed directly into the `process_transaction_text` function (the exact same logic used for text messages in Stage 3). No duplicate parsing logic was written.
- **AI Confirmation Step**: Because speech-to-text is not 100% reliable (e.g., mishearing amounts or categories), voice inputs trigger a mandatory confirmation flow. The bot replies with what it heard and asks the user to tap `[✅ Confirm]` or `[❌ Cancel]` before saving the transaction to the database.

## Commands run
```bash
git add -A
git commit -m "Added voice input via Groq Whisper API with confirmation flow"
git push
```

## Code built

### `bot/handlers/voice.py`
```python
@router.message(F.voice)
async def handle_voice_message(message: Message, bot: Bot) -> None:
    # 1. Provide instant feedback to user ("🎙️ Listening...")
    # 2. Download voice file to an io.BytesIO buffer
    # 3. Send to Groq API via aiohttp.FormData
    # 4. Extract transcription
    # 5. Feed into process_transaction_text(..., needs_confirmation=True)
```
**What it does:**
This file acts purely as a bridge between Telegram's voice format and our existing text parser. It uses `aiohttp` to make an asynchronous POST request to Groq, ensuring the bot remains responsive while waiting for the transcription.

### Updates to `bot/handlers/logging.py`
We refactored the core logic from `handle_text_message` into a reusable `process_transaction_text` function. We added a `needs_confirmation` flag. When `True`, instead of calling `add_transaction()` immediately, it saves the transaction data to the `pending_txns` dictionary and sends an inline keyboard with Confirm/Cancel buttons.

## Interview Q&A

**Q: Why use Groq's Whisper API instead of OpenAI or local Whisper?**
A: Groq uses specialized hardware (LPUs) that run open-source models like Whisper at incredible speeds. For a voice-based expense tracker, latency is critical. If it takes 5 seconds to transcribe a 2-second voice note, the user experience feels sluggish. Groq typically returns Whisper transcriptions in milliseconds. We also use the API instead of running it locally to keep the bot's hosting requirements minimal (it can run on a cheap 512MB VPS).

**Q: What happens if Whisper mishears the amount (e.g., hears "forty" instead of "fourteen")?**
A: This is the fundamental challenge with AI transcription. There is no perfect programmatic fix for a misheard audio file. To handle this, we implemented a **Confirmation Step** as a safety net. When the user sends a voice note, the bot does *not* log it immediately. It parses the transcription, builds the transaction, and says: "I heard: Spent ₹40 on Groceries. Is this correct?" with inline Confirm/Cancel buttons. If it's wrong, the user taps Cancel and can try again or type it.

**Q: Why use `io.BytesIO()` instead of saving the voice file to disk?**
A: Telegram allows downloading files into memory buffers. By using `io.BytesIO()`, we hold the audio file in RAM, send it directly to Groq, and let Python's garbage collector clean it up immediately. This avoids disk I/O bottlenecks and completely eliminates the need for cleanup scripts to delete old `.ogg` files from the server.

**Q: Why reuse the Stage 3 text parser instead of asking an LLM to parse the transcribed text?**
A: The transcribed text ("forty five groceries") is structurally identical to what a user types ("45 groceries"). Since we already built a lightning-fast, zero-cost, highly robust deterministic parser in Stage 3, there is absolutely no reason to pass the transcription to a second LLM for data extraction. The pipeline is: Audio -> Whisper (AI) -> Text -> Regex Parser (Deterministic) -> Database. This minimizes AI dependency and maximizes reliability.

**Q: Why use `aiohttp` instead of the official `groq` Python SDK?**
A: The `groq` Python SDK is synchronous by default unless specifically configured for async. Since we only need to hit a single `/audio/transcriptions` endpoint, constructing a direct HTTP request using `aiohttp` (which `aiogram` already installs) is simpler, keeps our dependencies lighter, and guarantees completely non-blocking async execution without having to manage thread pools for the SDK.
