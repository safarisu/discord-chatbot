"""
llm.py — Unified LLM interface supporting OpenAI, Anthropic, Ollama, OpenRouter.
"""

import httpx
import config


async def chat(messages: list[dict]) -> str:
    """Send a list of {role, content} messages and return the assistant reply."""
    provider = config.LLM_PROVIDER.lower()

    if provider == "openai":
        return await _openai(messages)
    if provider == "anthropic":
        return await _anthropic(messages)
    if provider == "ollama":
        return await _ollama(messages)
    if provider == "openrouter":
        return await _openrouter(messages)
    raise ValueError(f"Unknown LLM_PROVIDER: {provider!r}")


# ── Per-provider message serialisers ───────────────────────────────────────────
# Internal format: {"role": str, "content": str, "images"?: [{"data": b64, "mime_type": str}]}

def _openai_msg(m: dict) -> dict:
    if not m.get("images"):
        return {"role": m["role"], "content": m["content"]}
    content = [{"type": "text", "text": m["content"]}]
    for img in m["images"]:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{img['mime_type']};base64,{img['data']}"},
        })
    return {"role": m["role"], "content": content}


def _anthropic_msg(m: dict) -> dict:
    if not m.get("images"):
        return {"role": m["role"], "content": m["content"]}
    content = []
    for img in m["images"]:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": img["mime_type"], "data": img["data"]},
        })
    content.append({"type": "text", "text": m["content"]})
    return {"role": m["role"], "content": content}


def _ollama_msg(m: dict) -> dict:
    msg = {"role": m["role"], "content": m["content"]}
    if m.get("images"):
        msg["images"] = [img["data"] for img in m["images"]]
    return msg


# ── OpenAI ─────────────────────────────────────────────────────────────────────

async def _openai(messages: list[dict]) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
            json={
                "model": config.LLM_MODEL,
                "messages": [_openai_msg(m) for m in messages],
                "max_tokens": config.MAX_RESPONSE_TOKENS,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()


# ── Anthropic ──────────────────────────────────────────────────────────────────

async def _anthropic(messages: list[dict]) -> str:
    # Anthropic requires system prompt as a separate top-level field
    system = next((m["content"] for m in messages if m["role"] == "system"), "")
    non_system = [_anthropic_msg(m) for m in messages if m["role"] != "system"]

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
    body: dict = {
        "model": config.LLM_MODEL,
        "messages": [_ollama_msg(m) for m in messages],
        "stream": False,
        "options": {"num_predict": config.MAX_RESPONSE_TOKENS},
    }
    if config.OLLAMA_DISABLE_THINKING:
        body["think"] = False

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{config.OLLAMA_BASE_URL}/api/chat",
            json=body,
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
                "messages": [_openai_msg(m) for m in messages],
                "max_tokens": config.MAX_RESPONSE_TOKENS,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
