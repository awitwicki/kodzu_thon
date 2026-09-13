"""Session cookie handling, auth dependencies, CSRF and response hardening."""

import ipaddress
import secrets
from typing import Annotated

from fastapi import Depends, Form, HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from kodzu_thon.web import auth

COOKIE_NAME = "kodzuthon_session"
CSP = (
    "default-src 'self'; script-src 'none'; img-src 'self'; media-src 'self'; "
    "style-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'none'"
)


class NotAuthenticated(Exception):
    """Raised by dependencies; the app turns it into a redirect to /login."""


def client_ip(request: Request) -> str:
    """The peer address as a normalised IP string ("0.0.0.0" when unknown or unparsable),
    so it is always a valid value for the `inet` columns."""
    host = request.client.host if request.client else ""
    try:
        return str(ipaddress.ip_address(host))
    except ValueError:
        return "0.0.0.0"


def user_agent(request: Request) -> str | None:
    ua = request.headers.get("user-agent")
    return ua[:500] if ua else None


def apply_security_headers(response: Response, *, hsts: bool) -> None:
    headers = response.headers
    headers["Content-Security-Policy"] = CSP
    headers["X-Content-Type-Options"] = "nosniff"
    headers["X-Frame-Options"] = "DENY"
    headers["Referrer-Policy"] = "no-referrer"
    headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if hsts:
        headers["Strict-Transport-Security"] = "max-age=31536000"
    if headers.get("content-type", "").startswith("text/html"):
        headers["Cache-Control"] = "no-store"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, hsts: bool = False) -> None:
        super().__init__(app)
        self.hsts = hsts

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        apply_security_headers(response, hsts=self.hsts)
        return response


async def _sweep_expired(request: Request, now) -> None:
    state = request.app.state
    last = getattr(state, "last_sweep", None)
    if last is None or now - last >= auth.SWEEP_INTERVAL:
        state.last_sweep = now
        await state.repo.delete_expired_sessions(now)


async def load_session(request: Request) -> dict | None:
    repo = request.app.state.repo
    now = auth.utcnow()
    await _sweep_expired(request, now)
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    session = await repo.get_session(auth.token_hash(token))
    if session is None or session["expires_at"] <= now:
        return None
    if session["state"] != auth.STATE_ANON and now - session["last_seen_at"] >= auth.TOUCH_INTERVAL:
        expires_at = auth.session_expiry(session["state"], session["created_at"], now)
        await repo.touch_session(session["token_hash"], now, expires_at)
        session = {**session, "last_seen_at": now, "expires_at": expires_at}
    return session


async def current_session(request: Request) -> dict | None:
    return await load_session(request)


OptionalSessionDep = Annotated[dict | None, Depends(current_session)]


async def require_authed(session: OptionalSessionDep) -> dict:
    if session is None or session["state"] != auth.STATE_AUTHED:
        raise NotAuthenticated()
    return session


async def verify_csrf(
    session: OptionalSessionDep, csrf_token: Annotated[str | None, Form()] = None
) -> dict:
    if (
        session is None
        or not csrf_token
        or not secrets.compare_digest(csrf_token.encode(), session["csrf_token"].encode())
    ):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")
    return session


SessionDep = Annotated[dict, Depends(require_authed)]
CsrfDep = Annotated[dict, Depends(verify_csrf)]


def set_session_cookie(response: Response, token: str, *, secure: bool) -> None:
    response.set_cookie(
        COOKIE_NAME, token, httponly=True, samesite="strict", path="/", secure=secure
    )


def clear_session_cookie(response: Response, *, secure: bool) -> None:
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, samesite="strict", secure=secure)
