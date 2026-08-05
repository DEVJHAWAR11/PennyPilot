# Stage 06: Receipt Photo Input

## Features implemented in this stage
- **Vision Integration (`photo.py`)**: A handler that listens for `F.photo` messages.
- **Image Processing**: Downloads the highest resolution version of the photo sent by the user and encodes it to a base64 string.
- **Groq Vision API (`qwen/qwen3.6-27b`)**: Sends the base64 image along with a prompt to extract the total amount and merchant/category.
- **Reasoning Model Handling**: `qwen/qwen3.6-27b` is a reasoning model, meaning it outputs its internal thought process inside `<think>...</think>` tags before generating the final answer. We use a regular expression to strip this block so our strict text parser only sees the final answer.
- **Integration with Text Parser**: Passes the extracted text (e.g., `27.35 Green Supermarket`) into `process_transaction_text()` with `needs_confirmation=True`. This triggers the same confirmation flow built in Stage 5, ensuring the user always verifies the OCR output before it hits the database.

## Notes on Token Usage
- Because `qwen/qwen3.6-27b` is a reasoning model, it can generate hundreds or thousands of "thinking" tokens per receipt. 
- While this causes a spike in the token graph on the Groq console, Groq's API is extremely fast and provides generous free tiers (e.g., hundreds of thousands of tokens per day). For a personal finance bot, this volume is completely negligible and well within free limits.

## How to Test
1. Send a clear photo of a receipt to the bot.
2. The bot replies with an "Analyzing..." message.
17. The bot extracts the total and merchant, and presents an inline keyboard to Confirm or Edit the transaction.
18. Tapping Confirm logs the transaction to the database.

## Q&A and Troubleshooting
**Q: The bot consumes a massive amount of tokens for a single receipt image (e.g. 2,000+ output tokens)!**
**A:** This is because Groq's only available vision model (`qwen/qwen3.6-27b`) is a "reasoning model", meaning it normally outputs a massive `<think>...</think>` block before answering. To fix this, we updated the API payload to explicitly include `"reasoning_effort": "none"`. This forces the model to skip the thinking block entirely, reducing the output to just ~20 tokens and preventing you from hitting Groq's 8K Tokens Per Minute rate limit.
