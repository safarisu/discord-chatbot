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

## Hosting Options

### Free / Low Cost

| Option | Cost | Notes |
|---|---|---|
| **Railway.app** | Free tier (500h/mo) | Easiest deployment, connects to GitHub |
| **Fly.io** | Free tier (3 shared VMs) | More control, good for 24/7 |
| **Render.com** | Free (spins down after inactivity) | Fine for low-traffic bots |
| **Oracle Cloud Free Tier** | Always free | 2 AMD VMs, requires more setup |
| **Your own PC / server** | Free | Run `python bot.py` directly; needs to stay on |
| **Raspberry Pi** | ~$35 one-time | Permanent low-cost home server |

### Deployment on Railway (recommended for beginners)
```bash
# 1. Push code to GitHub (without .env)
# 2. New project on railway.app → Deploy from GitHub
# 3. Add environment variables (DISCORD_TOKEN etc.) in Railway dashboard
# 4. Add a Procfile:
echo "worker: python bot.py" > Procfile
```

---

## Model Options

### Free (no cost)

| Provider | Model | How |
|---|---|---|
| **OpenRouter** | `meta-llama/llama-3.1-8b-instruct:free` | Free tier, set `LLM_PROVIDER="openrouter"` |
| **OpenRouter** | `google/gemma-3-12b-it:free` | Free tier |
| **Ollama (local)** | `llama3.2`, `phi3`, `mistral` | Runs on your machine |
| **Google AI Studio** | `gemini-flash-2.0` | Free API key at aistudio.google.com |

### Cheap (pay-per-use)

| Provider | Model | Rough cost |
|---|---|---|
| OpenRouter | `meta-llama/llama-3.1-8b-instruct` | ~$0.06 / 1M tokens |
| OpenAI | `gpt-4o-mini` | ~$0.15 / 1M input |
| Anthropic | `claude-haiku-4-5` | ~$0.80 / 1M input |

---

## Local Models with Ollama

Run entirely free, no API key needed, no data leaves your machine.

```bash
# Install Ollama: https://ollama.com
ollama pull llama3.2        # 2GB — good balance of speed/quality
ollama pull phi3            # 2.3GB — fast, good for chat
ollama pull mistral         # 4GB — strong reasoning
ollama serve                # starts on localhost:11434
```

Then in config.py:
```python
LLM_PROVIDER = "ollama"
LLM_MODEL = "llama3.2"
```

**Note:** The machine running Ollama must be accessible from wherever the bot is hosted.
If hosting the bot on Railway, you'd need to expose Ollama (e.g. via ngrok or a VPS).
Easiest: run both bot + Ollama on the same machine.

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
