import os
from collections.abc import Mapping
from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class WebConfigError(Exception):
    pass


def _as_bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class WebSettings:
    database_url: str
    admin_user: str
    admin_password_hash: str
    totp_secret: str | None = None
    cookie_secure: bool = False
    timezone: str = "Europe/Warsaw"
    forwarded_allow_ips: str | None = None
    host: str = "0.0.0.0"
    port: int = 8080

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "WebSettings":
        env = os.environ if env is None else env

        def required(name: str) -> str:
            value = env.get(name)
            if not value:
                raise WebConfigError(f"Missing required env var: {name}")
            return value

        database_url = env.get("WEB_DATABASE_URL") or env.get("DATABASE_URL")
        if not database_url:
            raise WebConfigError("Set WEB_DATABASE_URL (or DATABASE_URL) to the archive database")
        password_hash = required("WEB_ADMIN_PASSWORD_HASH")
        if not password_hash.startswith("$argon2"):
            raise WebConfigError(
                "WEB_ADMIN_PASSWORD_HASH must be an argon2 hash; "
                "generate one with: python -m kodzu_thon.web hash-password"
            )
        timezone = env.get("WEB_TIMEZONE") or cls.timezone
        try:
            ZoneInfo(timezone)
        except ZoneInfoNotFoundError as e:
            raise WebConfigError(f"Unknown WEB_TIMEZONE: {timezone}") from e
        return cls(
            database_url=database_url,
            admin_user=required("WEB_ADMIN_USER"),
            admin_password_hash=password_hash,
            totp_secret=env.get("WEB_TOTP_SECRET") or None,
            cookie_secure=_as_bool(env.get("WEB_COOKIE_SECURE")),
            timezone=timezone,
            forwarded_allow_ips=env.get("WEB_FORWARDED_ALLOW_IPS") or None,
        )
