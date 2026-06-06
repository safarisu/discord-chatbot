# ─────────────────────────────────────────────
#  Bot Configuration
# ─────────────────────────────────────────────

# ── LLM Provider ──────────────────────────────
# Options: "openai", "anthropic", "ollama", "openrouter"
LLM_PROVIDER = "ollama"

# Model name (provider-specific):
#   openai:      "gpt-4o-mini", "gpt-3.5-turbo"
#   anthropic:   "claude-haiku-4-5-20251001"
#   ollama:      "llama3.2", "mistral", "phi3"
#   openrouter:  "meta-llama/llama-3.1-8b-instruct:free"
LLM_MODEL = "qwen3.5:0.8b"

# API keys (leave empty "" if not used)
OPENAI_API_KEY = ""
ANTHROPIC_API_KEY = ""
OPENROUTER_API_KEY = ""   # get free key at openrouter.ai

# Ollama base URL (local or remote)
OLLAMA_BASE_URL = "http://localhost:11434"

# Disable chain-of-thought thinking tokens for models that support it (e.g. Qwen3).
# Prevents the model spending its entire token budget on reasoning with nothing left to say.
OLLAMA_DISABLE_THINKING = True

# ── Personas ───────────────────────────────────
# Personalities and server contexts live in personas.json.
# Use !personas in Discord to list available personalities.
# Use !persona <name> to switch the active personality for this server.
PERSONAS_FILE = "personas.json"

# ── Discord Context ────────────────────────────
# How many previous messages to include as context
HISTORY_CONTEXT_MESSAGES = 20

# Only include messages from the last N minutes in history (0 = no time limit)
HISTORY_MAX_AGE_MINUTES = 0

# ── Rate Limiting ──────────────────────────────
# Max bot responses per user per day (resets at UTC midnight)
DAILY_LIMIT_PER_USER = 50

# Min seconds between responses to the same user
COOLDOWN_PER_USER_SECONDS = 10

# Min seconds between any two bot responses (global)
GLOBAL_COOLDOWN_SECONDS = 5

# Max bot responses per channel per hour
HOURLY_LIMIT_PER_CHANNEL = 50

# ── Spontaneous Replies ────────────────────────
# Probability (0.0–1.0) of replying to any message even without a trigger.
# 0.0 = disabled, 0.05 = 5% chance. Channel restrictions and rate limits still apply.
SPONTANEOUS_REPLY_CHANCE = 0.02

# ── Trigger Mode ───────────────────────────────
# "mention"  — bot replies only when @mentioned
# "prefix"   — bot replies when message starts with BOT_PREFIX
# "always"   — bot replies to all messages in allowed channels (use carefully!)
TRIGGER_MODE = "mention"
BOT_PREFIX = "!slop "

# ── Channel Restrictions ───────────────────────
# List of channel IDs where the bot is allowed to respond.
# Empty list [] means ALL channels are allowed.
ALLOWED_CHANNEL_IDS = []   # e.g. [123456789, 987654321]

# ── Context Enrichment ─────────────────────────
# Include guild role names alongside usernames in the message context
INCLUDE_USER_ROLES = False

# ── Vision ─────────────────────────────────────
# Set to True if your model supports image inputs (e.g. gemma4, gpt-4o, claude-3+)
VISION_ENABLED = True

# Largest allowed side (width or height) in pixels before downscaling (0 = no limit)
VISION_MAX_DIMENSION = 0

# Include images from message history (not just the current message)
VISION_HISTORY = False

# Max number of historical messages that may carry images (0 = unlimited)
# Only applies when VISION_HISTORY = True
VISION_HISTORY_LIMIT = 2

# ── Response Limits ────────────────────────────
MAX_RESPONSE_TOKENS = 400   # max tokens the LLM may generate
MAX_DISCORD_MESSAGE_LENGTH = 1900   # Discord limit is 2000, leave buffer
