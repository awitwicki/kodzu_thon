from datetime import timedelta

from fastapi.responses import Response

from kodzu_thon.web import auth
from kodzu_thon.web.security import (
    COOKIE_NAME,
    CsrfDep,
    OptionalSessionDep,
    apply_security_headers,
)
from tests.unit.web.fake_repo import NOW
from tests.unit.web.helpers import set_now


def test_apply_security_headers_marks_html_no_store():
    html = Response(content="<p>x</p>", media_type="text/html")
    apply_security_headers(html, hsts=False)
    assert html.headers["cache-control"] == "no-store"
    plain = Response(content="x", media_type="text/plain")
    apply_security_headers(plain, hsts=True)
    assert "cache-control" not in plain.headers
    assert plain.headers["strict-transport-security"] == "max-age=31536000"


async def _seed_session(fake_repo, state=auth.STATE_AUTHED, now=NOW):
    token, session = await auth.create_session(
        fake_repo, state=state, username="admin", ip="127.0.0.1", user_agent="t", now=now
    )
    return token, session


def _add_me_route(app):
    @app.get("/me")
    async def me(session: OptionalSessionDep):
        return {"state": session["state"] if session else None}


async def test_csrf_requires_session_and_matching_token(app, client, fake_repo):
    @app.post("/act")
    async def act(session: CsrfDep):
        return {"state": session["state"]}

    assert (await client.post("/act", data={"csrf_token": "x"})).status_code == 403
    token, session = await _seed_session(fake_repo)
    client.cookies.set(COOKIE_NAME, token)
    assert (await client.post("/act", data={"csrf_token": "wrong"})).status_code == 403
    assert (await client.post("/act", data={})).status_code == 403
    ok = await client.post("/act", data={"csrf_token": session["csrf_token"]})
    assert ok.status_code == 200 and ok.json() == {"state": "authed"}


async def test_csrf_non_ascii_token_is_403_not_500(app, client, fake_repo):
    """secrets.compare_digest raises TypeError on non-ASCII str-vs-str input; verify_csrf
    must encode both sides to bytes first so this is a clean 403, not an unhandled 500."""

    @app.post("/act")
    async def act(session: CsrfDep):
        return {"state": session["state"]}

    token, _session = await _seed_session(fake_repo)
    client.cookies.set(COOKIE_NAME, token)
    for bad_token in ("café", "日本語"):
        r = await client.post("/act", data={"csrf_token": bad_token})
        assert r.status_code == 403


async def test_expired_session_is_ignored(app, client, fake_repo, mocker):
    _add_me_route(app)
    set_now(mocker, NOW)
    token, _ = await _seed_session(fake_repo, now=NOW)
    client.cookies.set(COOKIE_NAME, token)
    assert (await client.get("/me")).json() == {"state": "authed"}
    set_now(mocker, NOW + timedelta(hours=13))
    assert (await client.get("/me")).json() == {"state": None}


async def test_session_is_touched_at_most_once_per_minute(app, client, fake_repo, mocker):
    _add_me_route(app)
    token, session = await _seed_session(fake_repo, now=NOW)
    client.cookies.set(COOKIE_NAME, token)
    set_now(mocker, NOW + timedelta(seconds=30))
    await client.get("/me")
    assert fake_repo.sessions[session["token_hash"]]["last_seen_at"] == NOW
    set_now(mocker, NOW + timedelta(minutes=2))
    await client.get("/me")
    stored = fake_repo.sessions[session["token_hash"]]
    assert stored["last_seen_at"] == NOW + timedelta(minutes=2)
    assert stored["expires_at"] == NOW + timedelta(minutes=2) + auth.SESSION_IDLE


async def test_anon_sessions_are_not_touched(app, client, fake_repo, mocker):
    _add_me_route(app)
    token, session = await _seed_session(fake_repo, state=auth.STATE_ANON, now=NOW)
    client.cookies.set(COOKIE_NAME, token)
    set_now(mocker, NOW + timedelta(minutes=5))
    assert (await client.get("/me")).json() == {"state": "anon"}
    assert fake_repo.sessions[session["token_hash"]]["expires_at"] == NOW + timedelta(hours=1)


async def test_expired_sessions_are_swept_at_most_hourly(app, client, fake_repo, mocker):
    _add_me_route(app)
    await _seed_session(fake_repo, now=NOW - timedelta(days=1))  # expired 12 h later
    set_now(mocker, NOW)
    await client.get("/me")  # any session-aware request triggers the first sweep
    assert fake_repo.sessions == {}
    await _seed_session(fake_repo, now=NOW - timedelta(days=1))
    await client.get("/me")  # within the hour: no sweep
    assert len(fake_repo.sessions) == 1
    set_now(mocker, NOW + timedelta(hours=2))
    await client.get("/me")
    assert fake_repo.sessions == {}
