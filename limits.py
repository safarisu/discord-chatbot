"""
limits.py — In-memory rate limiting (resets on bot restart; extend with Redis/SQLite for persistence).
"""

from collections import defaultdict
from datetime import datetime, timezone
import time
import config


class RateLimiter:
    def __init__(self):
        # user_id -> list of UTC timestamps of bot responses
        self._user_timestamps: dict[int, list[float]] = defaultdict(list)
        # channel_id -> list of UTC timestamps
        self._channel_timestamps: dict[int, list[float]] = defaultdict(list)
        # last global response timestamp
        self._last_global: float = 0.0

    # ── Public API ──────────────────────────────────────────────────────────

    def check(self, user_id: int, channel_id: int) -> tuple[bool, str]:
        """
        Returns (allowed: bool, reason: str).
        Call this BEFORE responding. If allowed, call .record() after.
        """
        now = time.time()

        # Global cooldown
        if now - self._last_global < config.GLOBAL_COOLDOWN_SECONDS:
            remaining = int(config.GLOBAL_COOLDOWN_SECONDS - (now - self._last_global))
            return False, f"⏳ The bot is cooling down globally. Try again in {remaining}s."

        # Per-user cooldown
        user_times = self._user_timestamps[user_id]
        if user_times and (now - user_times[-1]) < config.COOLDOWN_PER_USER_SECONDS:
            remaining = int(config.COOLDOWN_PER_USER_SECONDS - (now - user_times[-1]))
            return False, f"⏳ Please wait {remaining}s before asking again."

        # Per-user daily limit
        today_start = self._today_start_ts()
        daily_count = sum(1 for t in user_times if t >= today_start)
        if daily_count >= config.DAILY_LIMIT_PER_USER:
            return False, (
                f"📵 You've reached your daily limit of {config.DAILY_LIMIT_PER_USER} "
                "responses. Limit resets at UTC midnight."
            )

        # Per-channel hourly limit
        hour_ago = now - 3600
        channel_times = self._channel_timestamps[channel_id]
        hourly_count = sum(1 for t in channel_times if t >= hour_ago)
        if hourly_count >= config.HOURLY_LIMIT_PER_CHANNEL:
            return False, (
                f"📵 This channel has hit its hourly limit of "
                f"{config.HOURLY_LIMIT_PER_CHANNEL} responses. Try again later."
            )

        return True, ""

    def record(self, user_id: int, channel_id: int):
        """Record that a response was just sent."""
        now = time.time()
        self._last_global = now
        self._user_timestamps[user_id].append(now)
        self._channel_timestamps[channel_id].append(now)
        self._prune()

    def stats(self, user_id: int) -> dict:
        """Return current usage stats for a user."""
        now = time.time()
        today_start = self._today_start_ts()
        hour_ago = now - 3600
        user_times = self._user_timestamps[user_id]
        return {
            "daily_used": sum(1 for t in user_times if t >= today_start),
            "daily_limit": config.DAILY_LIMIT_PER_USER,
            "last_response_ago_s": int(now - user_times[-1]) if user_times else None,
        }

    # ── Internals ───────────────────────────────────────────────────────────

    @staticmethod
    def _today_start_ts() -> float:
        now = datetime.now(timezone.utc)
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return midnight.timestamp()

    def _prune(self):
        """Remove timestamps older than 25 hours to keep memory tidy."""
        cutoff = time.time() - 90_000
        for uid in list(self._user_timestamps):
            self._user_timestamps[uid] = [t for t in self._user_timestamps[uid] if t > cutoff]
        for cid in list(self._channel_timestamps):
            self._channel_timestamps[cid] = [t for t in self._channel_timestamps[cid] if t > cutoff]
