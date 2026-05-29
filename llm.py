"""
llm.py — Unified LLM interface supporting OpenAI, Anthropic, Ollama, OpenRouter.
"""

import httpx
import json
import config


async def chat(messages: list[dict]) -> str:
    """Send a list of {role, content} messages and return the assistant reply."""
    provider = config.LLM_PROVIDER.lower()

    if provider == "openai":
        return await _openai(messages)
    elif provider == "anthropic":
        return await _anthropic(messages)
    elif provider == "ollama":
        return await _ollama(messages)
    elif provider == "openrouter":
        return await _openrouter(messages)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider!r}")


# ── OpenAI ─────────────────────────────────────────────────────────────────────

async def _openai(messages: list[dict]) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
            json={
                "model": config.LLM_MODEL,
                "messages": messages,
                "max_tokens": config.MAX_RESPONSE_TOKENS,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()


# ── Anthropic ──────────────────────────────────────────────────────────────────

async def _anthropic(messages: list[dict]) -> str:
    # Anthropic requires system prompt as a separate field
    system = config.SYSTEM_PROMPT
    non_system = [m for m in messages if m["role"] != "system"]

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": config.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": config.LLM_MODEL,
                "system": system,
                "messages": non_system,
                "max_tokens": config.MAX_RESPONSE_TOKENS,
            },
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"].strip()


# ── Ollama (local) ─────────────────────────────────────────────────────────────

async def _ollama(messages: list[dict]) -> str:
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{config.OLLAMA_BASE_URL}/api/chat",
            json={
                "model": config.LLM_MODEL,
                "messages": messages,
                "stream": False,
                "options": {"num_predict": config.MAX_RESPONSE_TOKENS},
            },
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()


# ── OpenRouter ─────────────────────────────────────────────────────────────────

async def _openrouter(messages: list[dict]) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://discord-bot",   # required by OpenRouter
            },
            json={
                "model": config.LLM_MODEL,
                "messages": messages,
                "max_tokens": config.MAX_RESPONSE_TOKENS,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
