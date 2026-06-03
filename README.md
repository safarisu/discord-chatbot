# Discord LLM Bot

A configurable Discord bot that uses LLMs to read and respond to messages, with
support for multiple personalities, per-server context, vision (image inputs), and
rate limiting to prevent token burn.

---

## Quick Start

```bash
git clone <your-repo>
cd discord-llm-bot
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # then edit .env with your keys
# edit config.py for model, limits, trigger mode, vision
# edit personas.json for personalities and server contexts
python bot.py
```

---

## Project Structure

```
bot.py          — Entry point, Discord event handling
config.py       — All tuneable settings
llm.py          — LLM provider abstraction (OpenAI / Anthropic / Ollama / OpenRouter)
limits.py       — In-memory rate limiting
personas.json   — Personalities and per-server context
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

## Personalities

Personalities are defined in `personas.json`. The bot ships with three:

| Key | Description |
|---|---|
| `slopchan` | Unhelpful, incoherent AI parody (default) |
| `helpful` | Straightforward, genuinely useful assistant |
| `chaos` | Unhinged conspiracy theorist |

**Switching personality for a server** (requires Manage Server permission):
```
!slop persona helpful
```

**Listing available personalities:**
```
!slop personas
```

**One-shot personality override** (any user, doesn't change the server default):
```
!slop ask chaos why is the sky blue?
```
If an unknown personality name is given, the server default is used.

### Adding a personality

Add an entry to the `personalities` object in `personas.json`:

```json
"mybot": {
  "name": "MyBot",
  "description": "Short description shown in !slop personas",
  "system_prompt": "You are ..."
}
```

---

## Per-Server Context

Server-specific context is appended to the system prompt so the bot can tailor
responses to each community. Add an entry to the `servers` object in `personas.json`,
keyed by the Discord guild ID (as a string):

```json
"123456789012345678": {
  "name": "My Server",
  "context": "This is a community about retro gaming and speedrunning. Members appreciate technical breakdowns."
}
```

If no entry exists for a guild, the `"default"` entry is used (empty context).

---

## System Prompt Composition

Every response is built from up to four layers, concatenated in order:

1. **Meta prompt** — universal Discord-chatbot instructions (`meta_prompt` in `personas.json`)
2. **Personality** — character and tone for the active personality
3. **Server context** — community-specific information for the current guild
4. **Channel context** — injected at runtime: channel name/topic, or "DM" for direct messages

---

## Vision (Image Inputs)

Enable image support in `config.py`:

```python
VISION_ENABLED = True
```

When enabled, images attached to the triggering message are downloaded and forwarded
to the model. The model must support vision (e.g. `gemma4`, `gpt-4o`, `claude-3+`).

**History images** are off by default (each request would re-send every image in the
context window). Control this with:

```python
VISION_HISTORY = False        # include images from past messages
VISION_HISTORY_LIMIT = 2      # max past messages that may carry images (0 = unlimited)
```

---

## Configuration (config.py)

### LLM

| Setting | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `"ollama"` | `"openai"`, `"anthropic"`, `"ollama"`, `"openrouter"` |
| `LLM_MODEL` | `"gemma4:e2b"` | Model identifier (provider-specific) |
| `OLLAMA_BASE_URL` | `"http://localhost:11434"` | Ollama endpoint |

### Behaviour

| Setting | Default | Description |
|---|---|---|
| `TRIGGER_MODE` | `"mention"` | `"mention"`, `"prefix"`, `"always"` |
| `BOT_PREFIX` | `"!slop "` | Prefix for commands (and messages in prefix mode) |
| `HISTORY_CONTEXT_MESSAGES` | `10` | Max past messages sent as context |
| `HISTORY_MAX_AGE_MINUTES` | `60` | Ignore messages older than this |
| `ALLOWED_CHANNEL_IDS` | `[]` (all) | Restrict bot to specific channel IDs |

### Context Enrichment

| Setting | Default | Description |
|---|---|---|
| `PERSONAS_FILE` | `"personas.json"` | Path to personalities and server config |
| `INCLUDE_USER_ROLES` | `False` | Append guild role names to usernames in context |

### Vision

| Setting | Default | Description |
|---|---|---|
| `VISION_ENABLED` | `True` | Forward image attachments to the model |
| `VISION_HISTORY` | `False` | Include images from message history |
| `VISION_HISTORY_LIMIT` | `2` | Max history messages with images (0 = unlimited) |

### Rate Limiting

| Setting | Default | Description |
|---|---|---|
| `DAILY_LIMIT_PER_USER` | `10` | Max responses per user per day |
| `COOLDOWN_PER_USER_SECONDS` | `30` | Minimum gap between responses to same user |
| `GLOBAL_COOLDOWN_SECONDS` | `5` | Minimum gap between any two responses |
| `HOURLY_LIMIT_PER_CHANNEL` | `20` | Max responses per channel per hour |

---

## Commands

| Command | Who | Description |
|---|---|---|
| `!slop personas` | anyone | List available personalities and the active one |
| `!slop persona <name>` | Manage Server | Switch active personality for this server |
| `!slop ask <persona> <message>` | anyone | One-shot reply using a specific personality |
| `!slop mystats` | anyone | Show your daily usage stats |
| `!slop botinfo` | anyone | Show current bot configuration |

---

## Extending

- **Persistent rate limits** (survive restarts): swap `limits.py` to use SQLite or Redis
- **Per-server limits**: extend `RateLimiter` with `guild_id`
- **Streaming responses**: supported by OpenAI/Anthropic — edit `llm.py` to stream and edit a Discord message in-place
