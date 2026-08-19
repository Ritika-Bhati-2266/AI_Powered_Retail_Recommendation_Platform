"""
Simple in-memory login rate limiter.

A small, dependency-free throttle for /api/auth/login: buckets keyed by
(client IP, normalized email), 5 attempts per 15-minute window, then 429.

This is an in-process limiter — correct for the single-instance demo/prototype
deployment the project targets. It does NOT distribute across processes, so a
multi-worker or load-balanced production deployment should swap this for a
Redis-backed limiter (e.g. slowapi with a Redis limit storage) instead.
"""
import logging
import time

from fastapi import HTTPException

logger = logging.getLogger(__name__)

LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 15 * 60

# key=(ip, email) -> list of monotonic attempt timestamps (newest last)
_login_attempts: dict[tuple[str, str], list[float]] = {}
_prune_counter = 0


def _prune_if_due(now: float) -> None:
    """Best-effort sweep so expired buckets don't accumulate unboundedly."""
    global _prune_counter
    _prune_counter += 1
    if _prune_counter % 32 != 0:
        return
    expired = []
    for key, timestamps in _login_attempts.items():
        if not timestamps or now - timestamps[-1] >= LOGIN_WINDOW_SECONDS:
            expired.append(key)
    for key in expired:
        _login_attempts.pop(key, None)


def check_login_rate(client_host: str | None, email: str) -> None:
    """Enforce the login attempt budget for (IP, email). Raise 429 when exhausted."""
    key = (client_host or "unknown", (email or "").strip().lower())
    now = time.monotonic()

    _prune_if_due(now)

    attempts = [t for t in _login_attempts.get(key, []) if now - t < LOGIN_WINDOW_SECONDS]
    if len(attempts) >= LOGIN_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail=(
                "Too many failed login attempts. Please wait 15 minutes before "
                "trying again."
            ),
        )

    attempts.append(now)
    _login_attempts[key] = attempts


def record_login_success(client_host: str | None, email: str) -> None:
    """Clear the attempt bucket after a successful login."""
    key = (client_host or "unknown", (email or "").strip().lower())
    _login_attempts.pop(key, None)
