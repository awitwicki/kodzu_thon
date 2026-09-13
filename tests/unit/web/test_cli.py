import re

import pyotp
from argon2 import PasswordHasher

from kodzu_thon.web import __main__ as cli

ENV = {
    "WEB_DATABASE_URL": "postgresql://ro:pw@db:5432/kodzu_messages",
    "WEB_ADMIN_USER": "admin",
    "WEB_ADMIN_PASSWORD_HASH": "$argon2id$v=19$m=65536,t=3,p=4$c2FsdA$aGFzaA",
}


def test_hash_password_prints_quoted_env_line(capsys):
    code = cli.hash_password_command(read_password=lambda prompt: "correct horse battery staple")
    assert code == 0
    out, err = capsys.readouterr()
    match = re.fullmatch(r"WEB_ADMIN_PASSWORD_HASH='(\$argon2id\$[^']+)'\n", out)
    assert match, out
    assert PasswordHasher().verify(match.group(1), "correct horse battery staple")
    assert "single quotes" in err


def test_hash_password_rejects_short_passwords(capsys):
    assert cli.hash_password_command(read_password=lambda prompt: "short") == 1
    out, err = capsys.readouterr()
    assert out == "" and "at least 12" in err


def test_totp_secret_prints_secret_and_uri(capsys):
    assert cli.totp_secret_command("bob") == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0].startswith("WEB_TOTP_SECRET=")
    secret = out[0].split("=", 1)[1]
    assert len(secret) == 32 and pyotp.TOTP(secret).now().isdigit()
    assert (
        out[1].startswith("otpauth://totp/kodzuthon:bob?secret=") and "issuer=kodzuthon" in out[1]
    )


def test_main_dispatches(mocker, capsys):
    hp = mocker.patch.object(cli, "hash_password_command", return_value=0)
    ts = mocker.patch.object(cli, "totp_secret_command", return_value=0)
    assert cli.main(["hash-password"]) == 0 and hp.called
    assert cli.main(["totp-secret"]) == 0 and ts.call_args.args == ("admin",)
    assert cli.main(["totp-secret", "eve"]) == 0 and ts.call_args.args == ("eve",)
    assert cli.main(["bogus"]) == 2
    assert "usage:" in capsys.readouterr().err


def test_serve_runs_uvicorn_with_settings(mocker, monkeypatch):
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("WEB_FORWARDED_ALLOW_IPS", raising=False)
    run = mocker.patch("uvicorn.run")
    create_app = mocker.patch("kodzu_thon.web.app.create_app", return_value="APP")

    assert cli.main([]) == 0
    create_app.assert_called_once()
    assert create_app.call_args.args[0].admin_user == "admin"
    kwargs = run.call_args.kwargs
    assert run.call_args.args == ("APP",)
    assert kwargs["host"] == "0.0.0.0" and kwargs["port"] == 8080
    assert kwargs["proxy_headers"] is False and kwargs["forwarded_allow_ips"] == "127.0.0.1"
    assert kwargs["access_log"] is True


def test_serve_enables_proxy_headers_when_configured(mocker, monkeypatch):
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("WEB_FORWARDED_ALLOW_IPS", "10.0.0.2")
    run = mocker.patch("uvicorn.run")
    mocker.patch("kodzu_thon.web.app.create_app", return_value="APP")
    assert cli.main(["serve"]) == 0
    kwargs = run.call_args.kwargs
    assert kwargs["proxy_headers"] is True and kwargs["forwarded_allow_ips"] == "10.0.0.2"


def test_serve_reports_configuration_errors(mocker, monkeypatch, capsys):
    for k in ENV:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    run = mocker.patch("uvicorn.run")
    assert cli.main([]) == 1
    assert "Configuration error" in capsys.readouterr().err
    run.assert_not_called()
