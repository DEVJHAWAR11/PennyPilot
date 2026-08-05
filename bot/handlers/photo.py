"""
Photo input handler for processing receipts using Groq Vision.
Downloads images, encodes them to base64, asks the LLaMA Vision model to extract
the amount and merchant, and feeds the text directly into the text parser.
"""

import io
import base64
import logging
import aiohttp
import re

from aiogram import Router, F, Bot
from aiogram.types import Message

from bot.config import GROQ_API_KEY
from bot.handlers.logging import process_transaction_text

router = Router()

GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"
VISION_MODEL = "qwen/qwen3.6-27b"

@router.message(F.photo)
async def handle_photo_message(message: Message, bot: Bot) -> None:
    """Handle receipt photos by extracting text via Groq Vision."""
    
    if not GROQ_API_KEY or GROQ_API_KEY == "your-groq-api-key-here":
        await message.reply(
            "⚠️ **Vision input is disabled.**\n"
            "The `GROQ_API_KEY` is not configured in the `.env` file.",
            parse_mode="Markdown"
        )
        return

    # Acknowledge receipt
    status_msg = await message.reply("📸 Analyzing receipt...")

    try:
        # 1. Download the highest resolution photo to memory
        photo = message.photo[-1]  # The last one is the largest
        file_info = await bot.get_file(photo.file_id)
        photo_bytes = io.BytesIO()
        await bot.download_file(file_info.file_path, destination=photo_bytes)
        
        # 2. Encode to base64
        base64_image = base64.b64encode(photo_bytes.getvalue()).decode('utf-8')
        
        # 3. Call Groq Vision API via aiohttp
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": VISION_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": "Extract the total amount and a 1-2 word merchant or category from this receipt. Reply ONLY with the number followed by the words, for example: '45 Walmart' or '120.50 Dinner'. Do not explain or add any other text."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.1,  # Keep it deterministic
            "reasoning_effort": "none",
            "max_tokens": 50
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(GROQ_CHAT_COMPLETIONS_URL, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logging.error(f"Groq Vision API Error: {error_text}")
                    await status_msg.edit_text("❌ Failed to analyze the receipt. Please try typing it instead.")
                    return
                    
                result = await response.json()
                raw_text = result['choices'][0]['message']['content']
                extracted_text = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL).strip()

        logging.info(f"Groq Vision API Extracted: '{extracted_text}'")

        if not extracted_text:
            await status_msg.edit_text("I couldn't read the amount clearly. Please try again or type it instead.")
            return

        # 4. Feed into the text parser with confirmation step enabled
        await status_msg.delete()
        await process_transaction_text(message, extracted_text, needs_confirmation=True)

    except Exception as e:
        logging.exception("Error processing photo message")
        await status_msg.edit_text("❌ An error occurred while processing the receipt photo.")
