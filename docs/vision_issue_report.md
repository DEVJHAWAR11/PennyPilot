# Deep Dive: The Groq Vision Token Issue

I have thoroughly investigated the API logs, tested the models directly via Python scripts, and researched Groq's latest model availability. 

Here is exactly what is happening, why it consumes so many tokens, and why it is not a bug in the bot's code.

## 1. The Disappearance of Standard Vision Models
When we originally designed the bot, Groq supported two standard vision models: `llama-3.2-11b-vision-preview` and `llama-3.2-90b-vision-preview`. These models would instantly look at an image and spit out a 3-word answer (using exactly 3 output tokens). 

However, as of a few days ago, **Groq decommissioned and completely removed these models** from their platform. 

## 2. The New Model: Qwen 3.6 27B
Right now, the **only** vision model available on Groq is `qwen/qwen3.6-27b`. 

This is a **Reasoning Model** (similar to OpenAI's o1). Reasoning models are hard-coded at the architectural level to "think out loud" before they answer a prompt. When I ask it to extract a receipt total, it forcefully generates an invisible `<think>` block where it literally types out its internal monologue: *"Okay, let's look at the receipt. I see Chicken Tikka for 80.00. Then I see Yellow Dal..."* 

This internal monologue consumes between **1,500 to 3,000 output tokens** per image. 

## 3. The Rate Limit Problem
I ran a test script specifically instructing Qwen to **not** use the `<think>` tags and just give the answer. The model completely ignored the instruction and still outputted 1,516 thinking tokens. There is currently no API setting on Groq to disable this.

Because Groq's free tier imposes a strict limit of **8,000 Tokens Per Minute (TPM)**, a single receipt photo consumes about ~40% of your entire minute's quota (1.3K for the image input + ~2K for the thinking output). If you send 2 or 3 receipts in a row, you will hit the rate limit and the bot will fail.

---

## 🚀 Recommended Solutions

Since we cannot fix Groq's server-side model constraints, we have two options to solve this:

### Option A: Switch to Google Gemini API for Vision (Recommended)
We can keep using Groq for Voice and Text (since it's lightning fast), but switch **only the Photo handler** to use Google's free Gemini API (`gemini-1.5-flash`). 
- **Pros:** Gemini 1.5 Flash is incredibly fast, does not generate 2,000 tokens of useless thinking, and its free tier allows 15 requests per minute (with massive token limits).
- **Cons:** You will need to click a link to generate a free Gemini API key and paste it into the `.env` file.

### Option B: Keep Groq and Live with the Limit
We leave the code exactly as it is right now.
- **Pros:** You don't need to get any new API keys.
- **Cons:** You can only scan 1-2 receipts per minute. If you send too many, the bot will hit the rate limit and fail.

Let me know which option you prefer, and I will write the code immediately!
