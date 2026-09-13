from datetime import UTC, datetime, timedelta

import pyotp
from freezegun import freeze_time

from kodzu_thon.web import auth
from kodzu_thon.web.config import WebSettings
from tests.unit.web.fake_repo import FakeRepository

NOW = datetime(2026, 9, 13, 12, 0, tzinfo=UTC)
PASSWORD = "correct horse battery staple"
SECRET = pyotp.random_base32()


def settings(**overrides) -> WebSettings:
    fields = {
        "database_url": "postgresql://x",
        "admin_user": "admin",
        "admin_password_hash": auth.hash_password(PASSWORD),
    }
    fields.update(overrides)
    return WebSettings(**fields)


def test_hash_password_is_argon2id_and_verifies():
    s = settings()
    assert s.admin_password_hash.startswith("$argon2id$")
    assert auth.verify_password(s, "admin", PASSWORD) is True
    assert auth.verify_password(s, "admin", "wrong") is False


def test_verify_password_rejects_unknown_user_but_still_hashes(mocker):
    s = settings()
    spy = mocker.spy(auth, "_safe_verify")
    assert auth.verify_password(s, "root", PASSWORD) is False
    spy.assert_called_once()
    assert spy.call_args.args[0] == auth._DUMMY_HASH


def test_verify_password_survives_garbage_hash():
    assert (
        auth.verify_password(settings(admin_password_hash="$argon2id$garbage"), "admin", "x")
        is False
    )


def test_tokens_and_hashes():
    t1, t2 = auth.new_token(), auth.new_token()
    assert t1 != t2 and len(t1) >= 40
    assert auth.token_hash(t1) != auth.token_hash(t2) and len(auth.token_hash(t1)) == 32
    assert auth.new_csrf_token() != auth.new_csrf_token()


def test_session_expiry_rules():
    created = NOW - timedelta(days=6, hours=20)
    assert auth.session_expiry(auth.STATE_ANON, NOW, NOW) == NOW + timedelta(hours=1)
    assert auth.session_expiry(auth.STATE_AUTHED, NOW, NOW) == NOW + timedelta(hours=12)
    # absolute cap wins when the session is old
    assert auth.session_expiry(auth.STATE_AUTHED, created, NOW) == created + timedelta(days=7)


async def test_create_session_persists_and_returns_token():
    repo = FakeRepository()
    token, session = await auth.create_session(
        repo, state=auth.STATE_ANON, username=None, ip="10.0.0.1", user_agent="ua", now=NOW
    )
    stored = await repo.get_session(auth.token_hash(token))
    assert stored["state"] == "anon" and stored["csrf_token"] == session["csrf_token"]
    assert stored["created_at"] == NOW and stored["expires_at"] == NOW + timedelta(hours=1)
    assert stored["ip"] == "10.0.0.1" and stored["user_agent"] == "ua"
    assert session["token_hash"] == auth.token_hash(token)


async def test_rotate_session_deletes_old_and_creates_new():
    repo = FakeRepository()
    old_token, old = await auth.create_session(
        repo, state=auth.STATE_ANON, username=None, ip="1.1.1.1", user_agent=None, now=NOW
    )
    new_token, new = await auth.rotate_session(
        repo,
        old["token_hash"],
        state=auth.STATE_AUTHED,
        username="admin",
        ip="1.1.1.1",
        user_agent=None,
        now=NOW,
    )
    assert new_token != old_token and new["csrf_token"] != old["csrf_token"]
    assert await repo.get_session(old["token_hash"]) is None
    assert (await repo.get_session(new["token_hash"]))["state"] == "authed"
    assert new["expires_at"] == NOW + timedelta(hours=12)


async def test_rate_limit_by_ip_and_by_username():
    repo = FakeRepository()
    assert await auth.is_rate_limited(repo, "1.1.1.1", "admin") is False
    for _ in range(5):
        await repo.record_login_attempt("1.1.1.1", "someone", False)
    assert await auth.is_rate_limited(repo, "1.1.1.1", "admin") is True
    assert await auth.is_rate_limited(repo, "2.2.2.2", "admin") is False
    for _ in range(20):
        await repo.record_login_attempt("3.3.3.3", "admin", False)
    assert await auth.is_rate_limited(repo, "9.9.9.9", "admin") is True


async def test_rate_limit_window_expires():
    repo = FakeRepository()
    with freeze_time(NOW - timedelta(minutes=16)):
        for _ in range(5):
            await repo.record_login_attempt("1.1.1.1", "admin", False)
    with freeze_time(NOW):
        assert await auth.is_rate_limited(repo, "1.1.1.1", "admin") is False


def test_verify_totp_accepts_current_and_adjacent_windows():
    totp = pyotp.TOTP(SECRET)
    counter = totp.timecode(NOW)
    assert auth.verify_totp(SECRET, totp.generate_otp(counter), None, now=NOW) == counter
    assert auth.verify_totp(SECRET, totp.generate_otp(counter - 1), None, now=NOW) == counter - 1
    assert auth.verify_totp(SECRET, totp.generate_otp(counter + 1), None, now=NOW) == counter + 1
    assert auth.verify_totp(SECRET, totp.generate_otp(counter + 2), None, now=NOW) is None


def test_verify_totp_rejects_replay_and_garbage():
    totp = pyotp.TOTP(SECRET)
    counter = totp.timecode(NOW)
    code = totp.generate_otp(counter)
    assert auth.verify_totp(SECRET, code, counter, now=NOW) is None  # same counter already used
    assert auth.verify_totp(SECRET, code, counter + 5, now=NOW) is None
    assert auth.verify_totp(SECRET, code, counter - 1, now=NOW) == counter
    assert (
        auth.verify_totp(SECRET, " " + code + " ", None, now=NOW) == counter
    )  # whitespace tolerated
    assert auth.verify_totp(SECRET, "12345", None, now=NOW) is None
    assert auth.verify_totp(SECRET, "abcdef", None, now=NOW) is None
    assert auth.verify_totp(SECRET, "١٢٣٤٥٦", None, now=NOW) is None  # non-ASCII digits


def test_totp_provisioning_uri():
    uri = auth.totp_provisioning_uri(SECRET, "admin")
    assert uri.startswith("otpauth://totp/kodzuthon:admin?secret=") and "issuer=kodzuthon" in uri


def test_log_auth_event_goes_to_stdout(capsys):
    auth.log_auth_event("login ok", username="admin", ip="1.1.1.1")
    out = capsys.readouterr().out
    assert "web auth: login ok user='admin' ip=1.1.1.1" in out
