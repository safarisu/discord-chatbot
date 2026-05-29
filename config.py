# ─────────────────────────────────────────────
#  Bot Configuration
# ─────────────────────────────────────────────

# ── LLM Provider ──────────────────────────────
# Options: "openai", "anthropic", "ollama", "openrouter"
LLM_PROVIDER = "openrouter"

# Model name (provider-specific):
#   openai:      "gpt-4o-mini", "gpt-3.5-turbo"
#   anthropic:   "claude-haiku-4-5-20251001"
#   ollama:      "llama3.2", "mistral", "phi3"
#   openrouter:  "meta-llama/llama-3.1-8b-instruct:free"
LLM_MODEL = "meta-llama/llama-3.1-8b-instruct:free"

# API keys (leave empty "" if not used)
OPENAI_API_KEY = ""
ANTHROPIC_API_KEY = ""
OPENROUTER_API_KEY = ""   # get free key at openrouter.ai

# Ollama base URL (local or remote)
OLLAMA_BASE_URL = "http://localhost:11434"

# ── System Prompt ──────────────────────────────
SYSTEM_PROMPT = """You are a helpful assistant in a Discord server.
Be concise, friendly, and helpful. Keep responses under 400 words unless asked for detail."""

# ── Discord Context ────────────────────────────
# How many previous messages to include as context
HISTORY_CONTEXT_MESSAGES = 10

# Only include messages from the last N minutes in history (0 = no time limit)
HISTORY_MAX_AGE_MINUTES = 60

# ── Rate Limiting ──────────────────────────────
# Max bot responses per user per day (resets at UTC midnight)
DAILY_LIMIT_PER_USER = 10

# Min seconds between responses to the same user
COOLDOWN_PER_USER_SECONDS = 30

# Min seconds between any two bot responses (global)
GLOBAL_COOLDOWN_SECONDS = 5

# Max bot responses per channel per hour
HOURLY_LIMIT_PER_CHANNEL = 20

# ── Trigger Mode ───────────────────────────────
# "mention"  — bot replies only when @mentioned
# "prefix"   — bot replies when message starts with BOT_PREFIX
# "always"   — bot replies to all messages in allowed channels (use carefully!)
TRIGGER_MODE = "mention"
BOT_PREFIX = "!ask "

# ── Channel Restrictions ───────────────────────
# List of channel IDs where the bot is allowed to respond.
# Empty list [] means ALL channels are allowed.
ALLOWED_CHANNEL_IDS = []   # e.g. [123456789, 987654321]

# ── Response Limits ────────────────────────────
MAX_RESPONSE_TOKENS = 400   # max tokens the LLM may generate
MAX_DISCORD_MESSAGE_LENGTH = 1900   # Discord limit is 2000, leave buffer
