from dataclasses import replace
from typing import Annotated

import httpx
import pytest
from fastapi import Query

from kodzu_thon.db import SCHEMA_VERSION
from kodzu_thon.web.app import check_schema, create_app
from kodzu_thon.web.security import SessionDep
from tests.unit.web.fake_repo import FakeRepository


async def test_check_schema_accepts_current_and_rejects_old():
    repo = FakeRepository()
    assert await check_schema(repo) == SCHEMA_VERSION
    repo.version = SCHEMA_VERSION - 1
    with pytest.raises(RuntimeError, match="older than required"):
        await check_schema(repo)
    repo.version = None
    with pytest.raises(RuntimeError):
        await check_schema(repo)


async def test_healthz(client, fake_repo):
    r = await client.get("/healthz")
    assert r.status_code == 200 and r.text == "ok"
    fake_repo.ping_ok = False
    r = await client.get("/healthz")
    assert r.status_code == 503 and r.text == "unavailable"


async def test_security_headers_on_every_response(client):
    r = await client.get("/healthz")
    assert r.headers["content-security-policy"].startswith("default-src 'self'; script-src 'none';")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["referrer-policy"] == "no-referrer"
    assert r.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"
    assert "strict-transport-security" not in r.headers
    assert "cache-control" not in r.headers  # plain text, not HTML

    html = await client.get("/nope")
    assert html.status_code == 404
    assert html.headers["cache-control"] == "no-store"
    assert html.headers["content-type"].startswith("text/html")
    assert "Not found" in html.text


async def test_hsts_only_when_cookie_secure(web_settings, fake_repo):
    app = create_app(replace(web_settings, cookie_secure=True), repo=fake_repo)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        r = await c.get("/healthz")
    assert r.headers["strict-transport-security"] == "max-age=31536000"


async def test_api_docs_are_disabled(client):
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert (await client.get(path)).status_code == 404


async def test_static_files_are_served(client):
    r = await client.get("/static/style.css")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/css")
    r = await client.get("/static/avatar.svg")
    assert r.status_code == 200 and "svg" in r.headers["content-type"]


async def test_unauthenticated_request_redirects_to_login(app, client):
    @app.get("/secret")
    async def secret(session: SessionDep):
        return {"ok": True}

    r = await client.get("/secret")
    assert r.status_code == 303 and r.headers["location"] == "/login"


async def test_server_error_renders_500_without_traceback(app, client, capsys):
    @app.get("/boom")
    async def boom():
        raise RuntimeError("very secret detail")

    r = await client.get("/boom")
    assert r.status_code == 500
    assert "Internal error" in r.text and "very secret detail" not in r.text
    assert r.headers["x-content-type-options"] == "nosniff"
    assert "very secret detail" in capsys.readouterr().err  # logged server-side only


async def test_validation_error_renders_422_page(app, client):
    @app.get("/n")
    async def n(x: Annotated[int, Query()]):
        return {"x": x}

    r = await client.get("/n?x=abc")
    assert r.status_code == 422 and "Bad request" in r.text
