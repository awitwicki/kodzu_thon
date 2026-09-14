"""Command-line entry point: `serve` (default), `hash-password`, `totp-secret [username]`."""

import getpass
import sys
from collections.abc import Sequence

import pyotp
import uvicorn

from kodzu_thon.web.auth import hash_password, totp_provisioning_uri
from kodzu_thon.web.config import WebConfigError, WebSettings

USAGE = "usage: python -m kodzu_thon.web [serve | hash-password | totp-secret [username]]"
MIN_PASSWORD_LENGTH = 11


def serve() -> int:
    try:
        settings = WebSettings.from_env()
    except WebConfigError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1
    from kodzu_thon.web.app import create_app  # lazy: the other commands don't need FastAPI

    app = create_app(settings)
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        proxy_headers=settings.forwarded_allow_ips is not None,
        forwarded_allow_ips=settings.forwarded_allow_ips or "127.0.0.1",
        access_log=True,
    )
    return 0


def hash_password_command(read_password=getpass.getpass) -> int:
    password = read_password("Password: ")
    if len(password) < MIN_PASSWORD_LENGTH:
        print(f"Use at least {MIN_PASSWORD_LENGTH} characters", file=sys.stderr)
        return 1
    print(f"WEB_ADMIN_PASSWORD_HASH='{hash_password(password)}'")
    print(
        "# Keep the single quotes when pasting into .env: the hash contains '$', "
        "which docker-compose would otherwise try to expand.",
        file=sys.stderr,
    )
    return 0


def totp_secret_command(username: str) -> int:
    secret = pyotp.random_base32()
    print(f"WEB_TOTP_SECRET={secret}")
    print(totp_provisioning_uri(secret, username))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    command = args[0] if args else "serve"
    if command == "serve":
        return serve()
    if command == "hash-password":
        return hash_password_command()
    if command == "totp-secret":
        return totp_secret_command(args[1] if len(args) > 1 else "admin")
    print(USAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
