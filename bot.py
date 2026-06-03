"""
bot.py — Discord LLM Bot entry point.

Setup:
  1. pip install -r requirements.txt
  2. Copy .env.example to .env and fill in DISCORD_TOKEN + your LLM keys
  3. Edit config.py for rate limits, trigger mode, model, etc.
  4. python bot.py
"""

import os
import json
import base64
import asyncio
import logging
from datetime import datetime, timezone, timedelta

import httpx
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

# ── Persona loading ────────────────────────────────────────────────────────────

with open(config.PERSONAS_FILE, encoding="utf-8") as _f:
    _personas_data: dict = json.load(_f)

_meta_prompt: str = _personas_data.get("meta_prompt", "")
_personalities: dict = _personas_data["personalities"]
_servers: dict = _personas_data["servers"]
_default_personality: str = _personas_data["default_personality"]

# Active personality key per guild (in-memory; resets on restart)
_guild_personalities: dict[int, str] = {}


def _channel_context(channel) -> str:
    if isinstance(channel, discord.DMChannel):
        return f"You are in a direct message (DM) with {channel.recipient}."
    if isinstance(channel, discord.Thread):
        parent = f" in #{channel.parent.name}" if channel.parent else ""
        return f"You are in a thread named \"{channel.name}\"{parent}."
    if isinstance(channel, discord.TextChannel):
        topic = f" Topic: {channel.topic}" if channel.topic else ""
        return f"You are in #{channel.name}.{topic}"
    return ""


def _get_system_prompt(guild_id: int | None, personality_override: str | None = None) -> str:
    """Build the full system prompt for a guild: personality + server context."""
    key = personality_override or _guild_personalities.get(guild_id, _default_personality)
    personality = _personalities.get(key) or _personalities[_default_personality]

    server_key = str(guild_id) if guild_id and str(guild_id) in _servers else "default"
    server = _servers.get(server_key) or _servers.get("default", {})

    parts = [p for p in [_meta_prompt, personality["system_prompt"], server.get("context", "")] if p]
    return "\n\n".join(parts)


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


def _format_author(author) -> str:
    """Return display name with roles for guild members, plain name otherwise."""
    if config.INCLUDE_USER_ROLES and isinstance(author, discord.Member):
        roles = [r.name for r in author.roles if r.name != "@everyone"]
        if roles:
            return f"{author.display_name} [{', '.join(roles)}]"
    return author.display_name


async def _fetch_images(attachments: list[discord.Attachment]) -> list[dict]:
    """Download image attachments and return as base64 dicts for the LLM."""
    if not config.VISION_ENABLED or not attachments:
        return []
    images = []
    async with httpx.AsyncClient(timeout=30) as client:
        for att in attachments:
            mime = (att.content_type or "").split(";")[0]
            if mime.startswith("image/"):
                try:
                    resp = await client.get(att.url)
                    resp.raise_for_status()
                    images.append({
                        "data": base64.b64encode(resp.content).decode(),
                        "mime_type": mime,
                    })
                except Exception:
                    pass
    return images


def _clean_content(message: discord.Message) -> str:
    """Strip bot mention and prefix from the message text."""
    content = message.content
    if config.TRIGGER_MODE == "mention":
        content = content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "")
    elif config.TRIGGER_MODE == "prefix":
        content = content[len(config.BOT_PREFIX):]
    return content.strip()


async def _build_messages(
    message: discord.Message,
    personality_override: str | None = None,
    content_override: str | None = None,
) -> list[dict]:
    """
    Build the message list to send to the LLM:
      [system] + [recent channel history] + [current user message]
    """
    guild_id = message.guild.id if message.guild else None
    system = _get_system_prompt(guild_id, personality_override)
    channel_note = _channel_context(message.channel)
    if channel_note:
        system += f"\n\n{channel_note}"
    messages = [{"role": "system", "content": system}]

    # Fetch channel history
    history = []
    cutoff = None
    vision_history_count = 0
    if config.HISTORY_MAX_AGE_MINUTES > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=config.HISTORY_MAX_AGE_MINUTES)

    async for msg in message.channel.history(
        limit=config.HISTORY_CONTEXT_MESSAGES + 1,  # +1 to exclude the triggering message
        before=message,
    ):
        if cutoff and msg.created_at < cutoff:
            break
        if msg.author.bot and msg.author.id == bot.user.id:
            history.append({"role": "assistant", "content": msg.content})
        else:
            entry: dict = {
                "role": "user",
                "content": f"[{_format_author(msg.author)}]: {msg.content}",
            }
            under_limit = config.VISION_HISTORY_LIMIT == 0 or vision_history_count < config.VISION_HISTORY_LIMIT
            if config.VISION_HISTORY and under_limit:
                imgs = await _fetch_images(msg.attachments)
                if imgs:
                    entry["images"] = imgs
                    vision_history_count += 1
            history.append(entry)

    # History is newest-first; reverse for chronological order
    messages.extend(reversed(history))

    # Add current message
    user_text = content_override if content_override is not None else _clean_content(message)
    current: dict = {
        "role": "user",
        "content": f"[{_format_author(message.author)}]: {user_text}",
    }
    imgs = await _fetch_images(message.attachments)
    if imgs:
        current["images"] = imgs
    messages.append(current)

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

    if not reply_text:
        log.warning("LLM returned empty response, skipping send")
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


@bot.command(name="personas")
async def list_personas(ctx: commands.Context):
    """List all available personalities."""
    lines = []
    active_key = _guild_personalities.get(ctx.guild.id if ctx.guild else None, _default_personality)
    for key, p in _personalities.items():
        marker = " ◀ active" if key == active_key else ""
        lines.append(f"`{key}` — **{p['name']}**: {p['description']}{marker}")
    await ctx.reply("🎭 **Available personalities**\n" + "\n".join(lines), mention_author=False)


@bot.command(name="ask")
async def ask_as(ctx: commands.Context, persona: str, *, message: str):
    """Send a one-shot message using any personality without changing the server default."""
    if persona not in _personalities:
        # available = ", ".join(f"`{k}`" for k in _personalities)
        # await ctx.reply(f"❌ Unknown personality `{persona}`. Available: {available}", mention_author=False)
        # return
        persona = _default_personality

    allowed, reason = limiter.check(ctx.author.id, ctx.channel.id)
    if not allowed:
        await ctx.reply(reason, mention_author=False)
        return

    async with ctx.typing():
        try:
            msg_list = await _build_messages(ctx.message, personality_override=persona, content_override=message)
            reply_text = await llm.chat(msg_list)
        except Exception as e:
            log.exception("LLM error")
            await ctx.reply(f"⚠️ Sorry, something went wrong: `{e}`", mention_author=False)
            return

    if not reply_text:
        log.warning("LLM returned empty response, skipping send")
        return

    limiter.record(ctx.author.id, ctx.channel.id)
    for chunk in _split_message(reply_text):
        await ctx.reply(chunk, mention_author=False)


@ask_as.error
async def ask_as_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.MissingRequiredArgument):
        available = ", ".join(f"`{k}`" for k in _personalities)
        await ctx.reply(
            f"Usage: `{config.BOT_PREFIX}askas <persona> <message>` — available: {available}",
            mention_author=False,
        )


@bot.command(name="persona")
@commands.has_permissions(manage_guild=True)
async def set_persona(ctx: commands.Context, name: str):
    """Switch the active personality for this server (requires Manage Server)."""
    if name not in _personalities:
        available = ", ".join(f"`{k}`" for k in _personalities)
        await ctx.reply(f"❌ Unknown personality `{name}`. Available: {available}", mention_author=False)
        return
    guild_id = ctx.guild.id if ctx.guild else None
    _guild_personalities[guild_id] = name
    p = _personalities[name]
    await ctx.reply(f"✅ Switched to **{p['name']}** — {p['description']}", mention_author=False)


@set_persona.error
async def set_persona_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.MissingPermissions):
        await ctx.reply("❌ You need **Manage Server** permission to change the personality.", mention_author=False)
    elif isinstance(error, commands.MissingRequiredArgument):
        available = ", ".join(f"`{k}`" for k in _personalities)
        await ctx.reply(f"Usage: `{config.BOT_PREFIX}persona <name>` — available: {available}", mention_author=False)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN not set. Create a .env file (see .env.example).")
    bot.run(token)
