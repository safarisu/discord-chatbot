"""
bot.py — Discord LLM Bot entry point.

Setup:
  1. pip install -r requirements.txt
  2. Copy .env.example to .env and fill in DISCORD_TOKEN + your LLM keys
  3. Edit config.py for rate limits, trigger mode, model, etc.
  4. python bot.py
"""

import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta

import discord
from discord.ext import commands
from dotenv import load_dotenv

import config
import llm
from limits import RateLimiter

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# ── Bot setup ──────────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True   # required to read message text

bot = commands.Bot(command_prefix=config.BOT_PREFIX, intents=intents)
limiter = RateLimiter()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _should_respond(message: discord.Message) -> bool:
    """Check trigger mode and channel restrictions."""
    if message.author.bot:
        return False

    # Channel filter
    if config.ALLOWED_CHANNEL_IDS and message.channel.id not in config.ALLOWED_CHANNEL_IDS:
        return False

    mode = config.TRIGGER_MODE.lower()
    if mode == "mention":
        return bot.user in message.mentions
    elif mode == "prefix":
        return message.content.startswith(config.BOT_PREFIX)
    elif mode == "always":
        return True
    return False


def _clean_content(message: discord.Message) -> str:
    """Strip bot mention and prefix from the message text."""
    content = message.content
    if config.TRIGGER_MODE == "mention":
        content = content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "")
    elif config.TRIGGER_MODE == "prefix":
        content = content[len(config.BOT_PREFIX):]
    return content.strip()


async def _build_messages(message: discord.Message) -> list[dict]:
    """
    Build the message list to send to the LLM:
      [system] + [recent channel history] + [current user message]
    """
    messages = [{"role": "system", "content": config.SYSTEM_PROMPT}]

    # Fetch channel history
    history = []
    cutoff = None
    if config.HISTORY_MAX_AGE_MINUTES > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=config.HISTORY_MAX_AGE_MINUTES)

    async for msg in message.channel.history(
        limit=config.HISTORY_CONTEXT_MESSAGES + 1,  # +1 to exclude the triggering message
        before=message,
    ):
        if cutoff and msg.created_at < cutoff:
            break
        if msg.author.bot and msg.author.id == bot.user.id:
            role = "assistant"
        else:
            role = "user"
            # prefix username so the model knows who said what
            msg_content = f"[{msg.author.display_name}]: {msg.content}"
            history.append({"role": role, "content": msg_content})
            continue
        history.append({"role": role, "content": msg.content})

    # History is newest-first; reverse for chronological order
    messages.extend(reversed(history))

    # Add current message
    user_text = _clean_content(message)
    messages.append({
        "role": "user",
        "content": f"[{message.author.display_name}]: {user_text}",
    })

    return messages


def _split_message(text: str, limit: int = config.MAX_DISCORD_MESSAGE_LENGTH) -> list[str]:
    """Split a long response into Discord-sized chunks."""
    if len(text) <= limit:
        return [text]
    chunks, current = [], ""
    for paragraph in text.split("\n"):
        if len(current) + len(paragraph) + 1 > limit:
            if current:
                chunks.append(current.strip())
            current = paragraph
        else:
            current += ("\n" if current else "") + paragraph
    if current:
        chunks.append(current.strip())
    return chunks


# ── Events ─────────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    log.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    log.info(f"Provider: {config.LLM_PROVIDER}  Model: {config.LLM_MODEL}")
    log.info(f"Trigger: {config.TRIGGER_MODE}  History: {config.HISTORY_CONTEXT_MESSAGES} msgs")


@bot.event
async def on_message(message: discord.Message):
    if not _should_respond(message):
        await bot.process_commands(message)
        return

    user_id = message.author.id
    channel_id = message.channel.id

    # Rate limit check
    allowed, reason = limiter.check(user_id, channel_id)
    if not allowed:
        await message.reply(reason, mention_author=False)
        return

    async with message.channel.typing():
        try:
            msg_list = await _build_messages(message)
            reply_text = await llm.chat(msg_list)
        except Exception as e:
            log.exception("LLM error")
            await message.reply(f"⚠️ Sorry, something went wrong: `{e}`", mention_author=False)
            return

    # Record usage AFTER a successful response
    limiter.record(user_id, channel_id)

    for chunk in _split_message(reply_text):
        await message.reply(chunk, mention_author=False)

    await bot.process_commands(message)


# ── Slash / prefix commands ────────────────────────────────────────────────────

@bot.command(name="mystats")
async def mystats(ctx: commands.Context):
    """Show your current usage stats."""
    stats = limiter.stats(ctx.author.id)
    last = (
        f"{stats['last_response_ago_s']}s ago"
        if stats["last_response_ago_s"] is not None
        else "never"
    )
    await ctx.reply(
        f"📊 **Your stats**\n"
        f"Responses today: **{stats['daily_used']} / {stats['daily_limit']}**\n"
        f"Last response: {last}",
        mention_author=False,
    )


@bot.command(name="botinfo")
async def botinfo(ctx: commands.Context):
    """Show bot configuration info."""
    await ctx.reply(
        f"🤖 **Bot Info**\n"
        f"Provider: `{config.LLM_PROVIDER}` | Model: `{config.LLM_MODEL}`\n"
        f"Trigger: `{config.TRIGGER_MODE}` | History: `{config.HISTORY_CONTEXT_MESSAGES}` msgs\n"
        f"Daily limit/user: `{config.DAILY_LIMIT_PER_USER}` | "
        f"Cooldown: `{config.COOLDOWN_PER_USER_SECONDS}s`",
        mention_author=False,
    )


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN not set. Create a .env file (see .env.example).")
    bot.run(token)
