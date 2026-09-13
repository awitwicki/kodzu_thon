"""Shared constants and request helpers for the web test-suite."""

import re
from datetime import datetime

import httpx

from kodzu_thon.web.auth import hash_password

PASSWORD = "correct horse battery staple"
PASSWORD_HASH = hash_password(PASSWORD)  # hashed once per test session; argon2 is slow

_CSRF_RE = re.compile(r'name="csrf_token" value="([^"]+)"')


def csrf_from(html: str) -> str:
    match = _CSRF_RE.search(html)
    assert match, "no csrf_token field in page"
    return match.group(1)


async def login(client: httpx.AsyncClient, username: str = "admin", password: str = PASSWORD):
    """GET /login for a CSRF token, then POST the credentials. Returns the POST response."""
    page = await client.get("/login")
    return await client.post(
        "/login",
        data={"csrf_token": csrf_from(page.text), "username": username, "password": password},
    )


def set_now(mocker, when: datetime) -> None:
    """Pin the web package's clock. Do NOT use freezegun in tests that talk to the app:
    FastAPI builds route dependants lazily on the first request, and with freezegun's
    patched `datetime.date` in place pydantic cannot generate schemas (500s everywhere).
    Every time-dependent code path in kodzu_thon.web reads `auth.utcnow()`, so patching
    that one function is enough."""
    mocker.patch("kodzu_thon.web.auth.utcnow", return_value=when)
