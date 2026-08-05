"""
Voice input handler.
Downloads voice messages, transcribes them via Groq's Whisper API, 
and feeds them into the text parser with a confirmation step.
"""

import io
import logging
import aiohttp

from aiogram import Router, F, Bot
from aiogram.types import Message

from bot.config import GROQ_API_KEY
from bot.handlers.logging import process_transaction_text

router = Router()

GROQ_TRANSCRIPTION_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

@router.message(F.voice | F.audio)
async def handle_voice_message(message: Message, bot: Bot) -> None:
    """Handle voice/audio messages by transcribing and passing to the text parser."""
    
    if not GROQ_API_KEY or GROQ_API_KEY == "your-groq-api-key-here":
        await message.reply(
            "⚠️ **Voice input is disabled.**\n"
            "The `GROQ_API_KEY` is not configured in the `.env` file.",
            parse_mode="Markdown"
        )
        return

    # Acknowledge receipt
    status_msg = await message.reply("🎙️ Listening...")

    try:
        # 1. Download the voice/audio file to memory
        file_id = message.voice.file_id if message.voice else message.audio.file_id
        file_info = await bot.get_file(file_id)
        voice_bytes = io.BytesIO()
        await bot.download_file(file_info.file_path, destination=voice_bytes)
        
        # 2. Transcribe via Groq API
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
        
        data = aiohttp.FormData()
        # Whisper API expects a file, we provide the raw bytes with an .ogg extension 
        # (Telegram voice notes are typically OGG Opus)
        data.add_field('file', voice_bytes.getvalue(), filename='voice.ogg', content_type='audio/ogg')
        data.add_field('model', 'whisper-large-v3')
        
        async with aiohttp.ClientSession() as session:
            async with session.post(GROQ_TRANSCRIPTION_URL, headers=headers, data=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logging.error(f"Groq API Error: {error_text}")
                    await status_msg.edit_text("❌ Failed to transcribe the voice note. Please try typing it instead.")
                    return
                    
                result = await response.json()
                transcribed_text = result.get('text', '').strip()

        # 3. Handle empty transcription
        if not transcribed_text:
            await status_msg.edit_text("I couldn't hear any words clearly. Please try again or type it instead.")
            return

        # 4. Feed into the text parser with confirmation step enabled
        await status_msg.delete()
        await process_transaction_text(message, transcribed_text, needs_confirmation=True)

    except Exception as e:
        logging.exception("Error processing voice message")
        await status_msg.edit_text("❌ An error occurred while processing the voice note.")
