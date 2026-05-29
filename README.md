# Discord LLM Bot

A configurable Discord bot that uses LLMs to read and respond to messages, with
rate limiting to prevent token burn.

---

## Quick Start

```bash
git clone <your-repo>
cd discord-llm-bot
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # then edit .env with your keys
# edit config.py for model, limits, trigger mode
python bot.py
```

---

## Project Structure

```
bot.py          — Entry point, Discord event handling
config.py       — All tuneable settings
llm.py          — LLM provider abstraction (OpenAI / Anthropic / Ollama / OpenRouter)
limits.py       — In-memory rate limiting
requirements.txt
.env.example
```

---

## Discord Bot Setup

1. Go to https://discord.com/developers/applications
2. Create New Application → Bot → Add Bot
3. Under "Bot" enable **Message Content Intent**
4. Copy the token into `.env` as `DISCORD_TOKEN`
5. Invite URL: OAuth2 → URL Generator → scopes: `bot` → permissions: `Send Messages`, `Read Message History`, `View Channels`

---

## Configuration (config.py)

| Setting | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `"openrouter"` | `"openai"`, `"anthropic"`, `"ollama"`, `"openrouter"` |
| `LLM_MODEL` | llama free model | Model identifier (provider-specific) |
| `TRIGGER_MODE` | `"mention"` | `"mention"`, `"prefix"`, `"always"` |
| `HISTORY_CONTEXT_MESSAGES` | 10 | Max past messages sent as context |
| `HISTORY_MAX_AGE_MINUTES` | 60 | Ignore messages older than this |
| `DAILY_LIMIT_PER_USER` | 10 | Max responses per user per day |
| `COOLDOWN_PER_USER_SECONDS` | 30 | Minimum gap between responses to same user |
| `GLOBAL_COOLDOWN_SECONDS` | 5 | Minimum gap between any two responses |
| `HOURLY_LIMIT_PER_CHANNEL` | 20 | Max responses per channel per hour |
| `ALLOWED_CHANNEL_IDS` | `[]` (all) | Restrict bot to specific channels |

---

## Commands

| Command | Description |
|---|---|
| `!ask mystats` | Show your daily usage |
| `!ask botinfo` | Show bot configuration |

(prefix is `!ask ` by default, configurable in config.py)

---

## Extending

- **Persistent rate limits** (survive restarts): swap `limits.py` to use SQLite or Redis
- **Per-server limits**: extend `RateLimiter` with `guild_id`
- **Admin override**: check `message.author.guild_permissions.administrator`
- **Streaming responses**: supported by OpenAI/Anthropic — edit `llm.py` to stream and edit a Discord message in-place
