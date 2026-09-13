"""Password, session and TOTP logic for the web viewer. No FastAPI imports here."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from kodzu_thon.web.config import WebSettings

STATE_ANON = "anon"
STATE_PENDING_TOTP = "pending_totp"
STATE_AUTHED = "authed"

SESSION_IDLE = timedelta(hours=12)
SESSION_MAX = timedelta(days=7)
ANON_LIFETIME = timedelta(hours=1)
TOUCH_INTERVAL = timedelta(minutes=1)
SWEEP_INTERVAL = timedelta(hours=1)
RATE_WINDOW = timedelta(minutes=15)
IP_FAILURE_LIMIT = 5
USERNAME_FAILURE_LIMIT = 20
RETRY_AFTER_SECONDS = 900
TOTP_ISSUER = "kodzuthon"

_hasher = PasswordHasher()
# Verified against whenever the username is wrong, so a bad username costs the same
# time as a bad password and timing does not reveal which one was wrong.
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))


def utcnow() -> datetime:
    return datetime.now(UTC)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def _safe_verify(hash_str: str, password: str) -> bool:
    try:
        return _hasher.verify(hash_str, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def verify_password(settings: WebSettings, username: str, password: str) -> bool:
    if not secrets.compare_digest(username.encode(), settings.admin_user.encode()):
        _safe_verify(_DUMMY_HASH, password)
        return False
    return _safe_verify(settings.admin_password_hash, password)


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> bytes:
    return hashlib.sha256(token.encode()).digest()


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def session_expiry(state: str, created_at: datetime, now: datetime) -> datetime:
    if state == STATE_ANON:
        return now + ANON_LIFETIME
    return min(now + SESSION_IDLE, created_at + SESSION_MAX)


async def create_session(
    repo,
    *,
    state: str,
    username: str | None,
    ip: str,
    user_agent: str | None,
    now: datetime | None = None,
) -> tuple[str, dict]:
    now = now or utcnow()
    token = new_token()
    hashed = token_hash(token)
    csrf = new_csrf_token()
    expires_at = session_expiry(state, now, now)
    await repo.create_session(hashed, state, username, csrf, now, expires_at, ip, user_agent)
    session = {
        "token_hash": hashed,
        "state": state,
        "username": username,
        "csrf_token": csrf,
        "created_at": now,
        "last_seen_at": now,
        "expires_at": expires_at,
    }
    return token, session


async def rotate_session(
    repo,
    old_token_hash: bytes,
    *,
    state: str,
    username: str | None,
    ip: str,
    user_agent: str | None,
    now: datetime | None = None,
) -> tuple[str, dict]:
    await repo.delete_session(old_token_hash)
    return await create_session(
        repo, state=state, username=username, ip=ip, user_agent=user_agent, now=now
    )


async def is_rate_limited(repo, ip: str, username: str, now: datetime | None = None) -> bool:
    since = (now or utcnow()) - RATE_WINDOW
    if await repo.failed_attempts_by_ip(ip, since) >= IP_FAILURE_LIMIT:
        return True
    return await repo.failed_attempts_by_username(username, since) >= USERNAME_FAILURE_LIMIT


def verify_totp(
    secret: str, code: str, last_counter: int | None, now: datetime | None = None
) -> int | None:
    """Return the accepted time-step counter, or None. Accepts the current step and
    its neighbours (valid_window=1) and refuses any counter already consumed."""
    code = code.strip()
    if len(code) != 6 or not code.isascii() or not code.isdigit():
        return None
    totp = pyotp.TOTP(secret)
    current = totp.timecode(now or utcnow())
    for counter in (current - 1, current, current + 1):
        if secrets.compare_digest(totp.generate_otp(counter), code):
            if last_counter is not None and counter <= last_counter:
                return None
            return counter
    return None


def totp_provisioning_uri(secret: str, username: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name=TOTP_ISSUER)


def log_auth_event(event: str, *, username: str | None, ip: str) -> None:
    print(f"web auth: {event} user={username!r} ip={ip}", flush=True)
