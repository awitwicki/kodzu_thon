from dataclasses import replace

import httpx
import pyotp

from kodzu_thon.web import auth
from kodzu_thon.web.app import create_app
from kodzu_thon.web.security import COOKIE_NAME, SessionDep
from tests.unit.web.fake_repo import NOW
from tests.unit.web.helpers import PASSWORD, csrf_from, login, set_now

SECRET = pyotp.random_base32()


def add_secret_route(app):
    @app.get("/secret")
    async def secret(session: SessionDep):
        return {"user": session["username"]}


async def test_get_login_creates_anon_session_and_sets_cookie(client, fake_repo):
    r = await client.get("/login")
    assert r.status_code == 200 and 'name="csrf_token"' in r.text
    cookie = r.headers["set-cookie"]
    assert (
        cookie.startswith(f"{COOKIE_NAME}=")
        and "HttpOnly" in cookie
        and "SameSite=strict" in cookie
    )
    assert "Secure" not in cookie
    token = client.cookies.get(COOKIE_NAME)
    session = fake_repo.sessions[auth.token_hash(token)]
    assert session["state"] == "anon" and csrf_from(r.text) == session["csrf_token"]

    again = await client.get("/login")
    assert "set-cookie" not in again.headers  # existing anon session is reused
    assert len(fake_repo.sessions) == 1


async def test_login_success_rotates_session_and_records_attempt(app, client, fake_repo):
    add_secret_route(app)
    page = await client.get("/login")
    anon_token = client.cookies.get(COOKIE_NAME)

    r = await client.post(
        "/login",
        data={"csrf_token": csrf_from(page.text), "username": "admin", "password": PASSWORD},
    )
    assert r.status_code == 303 and r.headers["location"] == "/"
    new_token = client.cookies.get(COOKIE_NAME)
    assert new_token != anon_token
    assert auth.token_hash(anon_token) not in fake_repo.sessions
    assert fake_repo.sessions[auth.token_hash(new_token)]["state"] == "authed"
    assert fake_repo.attempts[-1]["success"] is True

    assert (await client.get("/secret")).json() == {"user": "admin"}
    assert (await client.get("/login")).headers["location"] == "/"


async def test_wrong_password_and_wrong_user_give_same_generic_error(client, fake_repo):
    r = await login(client, password="nope")
    assert r.status_code == 401 and "Invalid credentials" in r.text
    assert fake_repo.attempts[-1]["username"] == "admin"
    assert fake_repo.attempts[-1]["success"] is False
    r = await login(client, username="root", password=PASSWORD)
    assert r.status_code == 401 and "Invalid credentials" in r.text
    assert fake_repo.attempts[-1]["username"] == "root"
    token = client.cookies.get(COOKIE_NAME)
    assert fake_repo.sessions[auth.token_hash(token)]["state"] == "anon"


async def test_login_is_rate_limited_per_ip(client, fake_repo, mocker):
    spy = mocker.spy(auth, "verify_password")
    for _ in range(5):
        assert (await login(client, password="nope")).status_code == 401
    r = await login(client, password=PASSWORD)
    assert r.status_code == 429 and r.headers["retry-after"] == "900"
    assert "Too many attempts" in r.text
    assert spy.call_count == 5  # the sixth attempt never reached the password check


async def test_login_is_rate_limited_per_username_across_ips(client, fake_repo):
    for _ in range(20):
        await fake_repo.record_login_attempt("203.0.113.9", "admin", False)
    r = await login(client, password=PASSWORD)
    assert r.status_code == 429


async def test_login_post_without_csrf_is_forbidden(client):
    await client.get("/login")
    r = await client.post("/login", data={"username": "admin", "password": PASSWORD})
    assert r.status_code == 403
    r = await client.post(
        "/login", data={"csrf_token": "bad", "username": "admin", "password": PASSWORD}
    )
    assert r.status_code == 403


async def test_login_post_without_any_session_is_forbidden(client):
    r = await client.post(
        "/login", data={"csrf_token": "x", "username": "admin", "password": PASSWORD}
    )
    assert r.status_code == 403


async def test_logout_deletes_session_and_clears_cookie(app, client, fake_repo):
    add_secret_route(app)
    await login(client)
    token = client.cookies.get(COOKIE_NAME)
    csrf = fake_repo.sessions[auth.token_hash(token)]["csrf_token"]

    assert (await client.post("/logout", data={})).status_code == 403
    r = await client.post("/logout", data={"csrf_token": csrf})
    assert r.status_code == 303 and r.headers["location"] == "/login"
    assert auth.token_hash(token) not in fake_repo.sessions
    assert (
        'kodzuthon_session=""' in r.headers["set-cookie"] or "Max-Age=0" in r.headers["set-cookie"]
    )
    assert (await client.get("/secret")).status_code == 303


async def test_secure_cookie_flag_follows_settings(web_settings, fake_repo):
    app = create_app(replace(web_settings, cookie_secure=True), repo=fake_repo)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="https://test"
    ) as c:
        r = await c.get("/login")
    assert "Secure" in r.headers["set-cookie"]


async def totp_client(web_settings, fake_repo):
    app = create_app(replace(web_settings, totp_secret=SECRET), repo=fake_repo)
    add_secret_route(app)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def test_totp_flow(web_settings, fake_repo, mocker):
    set_now(mocker, NOW)
    async with await totp_client(web_settings, fake_repo) as client:
        r = await login(client)
        assert r.status_code == 303 and r.headers["location"] == "/login/totp"
        token = client.cookies.get(COOKIE_NAME)
        session = fake_repo.sessions[auth.token_hash(token)]
        assert session["state"] == "pending_totp"
        assert (await client.get("/secret")).status_code == 303  # not authed yet
        assert (await client.get("/login")).headers["location"] == "/login/totp"

        page = await client.get("/login/totp")
        assert page.status_code == 200 and 'name="code"' in page.text
        csrf = session["csrf_token"]

        bad = await client.post("/login/totp", data={"csrf_token": csrf, "code": "000000"})
        assert bad.status_code == 401 and "Invalid code" in bad.text
        assert fake_repo.attempts[-1]["success"] is False

        code = pyotp.TOTP(SECRET).at(NOW)
        ok = await client.post("/login/totp", data={"csrf_token": csrf, "code": code})
        assert ok.status_code == 303 and ok.headers["location"] == "/"
        assert fake_repo.sessions[auth.token_hash(token)]["state"] == "authed"
        assert fake_repo.totp_counter == pyotp.TOTP(SECRET).timecode(NOW)
        assert (await client.get("/secret")).json() == {"user": "admin"}


async def test_totp_code_cannot_be_replayed(web_settings, fake_repo, mocker):
    set_now(mocker, NOW)
    async with await totp_client(web_settings, fake_repo) as client:
        await login(client)
        token = client.cookies.get(COOKIE_NAME)
        csrf = fake_repo.sessions[auth.token_hash(token)]["csrf_token"]
        code = pyotp.TOTP(SECRET).at(NOW)
        ok = await client.post("/login/totp", data={"csrf_token": csrf, "code": code})
        assert ok.status_code == 303
        # log out and start over: the same code within the same window must be refused
        await client.post("/logout", data={"csrf_token": csrf})
        await login(client)
        token = client.cookies.get(COOKIE_NAME)
        csrf = fake_repo.sessions[auth.token_hash(token)]["csrf_token"]
        replay = await client.post("/login/totp", data={"csrf_token": csrf, "code": code})
        assert replay.status_code == 401


async def test_totp_page_redirects_when_not_configured(client):
    r = await client.get("/login/totp")
    assert r.status_code == 303 and r.headers["location"] == "/login"
