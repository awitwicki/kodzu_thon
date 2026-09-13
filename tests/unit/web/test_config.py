import pytest

from kodzu_thon.web.config import WebConfigError, WebSettings

HASH = "$argon2id$v=19$m=65536,t=3,p=4$c2FsdHRzYWx0c2FsdA$hashhashhash"


def base_env(**overrides):
    env = {
        "WEB_DATABASE_URL": "postgresql://ro:pw@db:5432/kodzu_messages",
        "WEB_ADMIN_USER": "admin",
        "WEB_ADMIN_PASSWORD_HASH": HASH,
    }
    env.update(overrides)
    return {k: v for k, v in env.items() if v is not None}


def test_from_env_reads_required_and_defaults():
    s = WebSettings.from_env(base_env())
    assert s.database_url == "postgresql://ro:pw@db:5432/kodzu_messages"
    assert s.admin_user == "admin"
    assert s.admin_password_hash == HASH
    assert s.totp_secret is None
    assert s.cookie_secure is False
    assert s.timezone == "Europe/Warsaw"
    assert s.forwarded_allow_ips is None
    assert (s.host, s.port) == ("0.0.0.0", 8080)


def test_web_database_url_falls_back_to_database_url():
    env = base_env(WEB_DATABASE_URL=None, DATABASE_URL="postgresql://rw:pw@db:5432/kodzu_messages")
    assert WebSettings.from_env(env).database_url == "postgresql://rw:pw@db:5432/kodzu_messages"


def test_missing_both_database_urls_is_an_error():
    with pytest.raises(WebConfigError, match="WEB_DATABASE_URL"):
        WebSettings.from_env(base_env(WEB_DATABASE_URL=None))


@pytest.mark.parametrize("missing", ["WEB_ADMIN_USER", "WEB_ADMIN_PASSWORD_HASH"])
def test_missing_required_is_an_error(missing):
    with pytest.raises(WebConfigError, match=missing):
        WebSettings.from_env(base_env(**{missing: None}))


def test_password_hash_must_be_argon2():
    with pytest.raises(WebConfigError, match="hash-password"):
        WebSettings.from_env(base_env(WEB_ADMIN_PASSWORD_HASH="plaintext"))


def test_unknown_timezone_is_an_error():
    with pytest.raises(WebConfigError, match="WEB_TIMEZONE"):
        WebSettings.from_env(base_env(WEB_TIMEZONE="Mars/Olympus"))


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("true", True),
        ("1", True),
        ("YES", True),
        ("on", True),
        ("false", False),
        ("", False),
        ("0", False),
    ],
)
def test_cookie_secure_parsing(raw, expected):
    assert WebSettings.from_env(base_env(WEB_COOKIE_SECURE=raw)).cookie_secure is expected


def test_optional_values():
    s = WebSettings.from_env(
        base_env(
            WEB_TOTP_SECRET="JBSWY3DPEHPK3PXP",
            WEB_FORWARDED_ALLOW_IPS="10.0.0.2",
            WEB_TIMEZONE="Europe/Kyiv",
        )
    )
    assert s.totp_secret == "JBSWY3DPEHPK3PXP"
    assert s.forwarded_allow_ips == "10.0.0.2"
    assert s.timezone == "Europe/Kyiv"


def test_empty_optional_values_become_none():
    s = WebSettings.from_env(base_env(WEB_TOTP_SECRET="", WEB_FORWARDED_ALLOW_IPS=""))
    assert s.totp_secret is None and s.forwarded_allow_ips is None


def test_from_env_defaults_to_os_environ(monkeypatch):
    for k, v in base_env().items():
        monkeypatch.setenv(k, v)
    assert WebSettings.from_env().admin_user == "admin"
