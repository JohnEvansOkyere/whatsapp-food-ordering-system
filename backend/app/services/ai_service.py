"""
AI Service — Three-provider cascade.

Primary:  Groq       (llama-3.3-70b-versatile) — fastest, free tier
Fallback: OpenAI     (gpt-4o-mini)             — reliable, affordable
Third:    Gemini     (gemini-1.5-flash)         — free tier backup

Each provider is tried in order. If one fails or times out,
the next is used automatically. Errors are logged per provider.
"""

import logging
from app.config import get_settings

logger = logging.getLogger(__name__)


async def get_ai_response(
    messages: list[dict],
    system_prompt: str,
    max_tokens: int = 300,
    temperature: float = 0.7,
) -> str:
    """
    Try Groq → OpenAI → Gemini in order.
    Returns the first successful response.
    Raises Exception only if all three fail.
    """
    providers = [
        _call_groq,
        _call_openai,
        _call_gemini,
    ]

    last_error: Exception | None = None

    for provider in providers:
        try:
            reply = await provider(
                messages=messages,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            if reply:
                return reply.strip()
        except Exception as e:
            provider_name = provider.__name__.replace("_call_", "")
            logger.warning(f"AI provider '{provider_name}' failed: {e}")
            last_error = e
            continue

    logger.error(f"All AI providers failed. Last error: {last_error}")
    return (
        "Sorry, I'm having trouble right now. "
        "Please try again in a moment or call us directly. 🙏"
    )


# ── GROQ ──────────────────────────────────────────────────────────────────────

async def _call_groq(
    messages: list[dict],
    system_prompt: str,
    max_tokens: int,
    temperature: float,
) -> str:
    from groq import AsyncGroq

    settings = get_settings()
    client = AsyncGroq(api_key=settings.groq_api_key)

    response = await client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": system_prompt},
            *messages,
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )

    return response.choices[0].message.content


# ── OPENAI ────────────────────────────────────────────────────────────────────

async def _call_openai(
    messages: list[dict],
    system_prompt: str,
    max_tokens: int,
    temperature: float,
) -> str:
    from openai import AsyncOpenAI

    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system_prompt},
            *messages,
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )

    return response.choices[0].message.content


# ── GEMINI ────────────────────────────────────────────────────────────────────

async def _call_gemini(
    messages: list[dict],
    system_prompt: str,
    max_tokens: int,
    temperature: float,
) -> str:
    import google.generativeai as genai

    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)

    model = genai.GenerativeModel(
        model_name=settings.gemini_model,
        system_instruction=system_prompt,
        generation_config={
            "max_output_tokens": max_tokens,
            "temperature": temperature,
        },
    )

    # Convert OpenAI-style messages to Gemini format
    gemini_history = []
    for msg in messages[:-1]:  # All but last
        role = "user" if msg["role"] == "user" else "model"
        gemini_history.append({"role": role, "parts": [msg["content"]]})

    chat = model.start_chat(history=gemini_history)

    # Last message is the current user input
    last_message = messages[-1]["content"] if messages else ""
    response = await chat.send_message_async(last_message)

    return response.text
