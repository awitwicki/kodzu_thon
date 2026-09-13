"""Pure text/formatting helpers for templates. No I/O, no Jinja dependency."""

import re
from datetime import datetime
from zoneinfo import ZoneInfo

from markupsafe import Markup, escape

_URL_RE = re.compile(r"https?://[^\s<>\"']+")
_TRAILING_PUNCT = ".,;:!?)]}\"'"


def linkify(text: str) -> Markup:
    """Escape `text`, then wrap http(s) URLs in anchors. Runs on the escaped
    string, so an attacker-controlled URL can never break out of the href."""
    escaped = str(escape(text))

    def repl(match: re.Match) -> str:
        url = match.group(0)
        trail = ""
        while url and url[-1] in _TRAILING_PUNCT:
            trail = url[-1] + trail
            url = url[:-1]
        return f'<a href="{url}" rel="noopener noreferrer">{url}</a>{trail}'

    return Markup(_URL_RE.sub(repl, escaped))


def nl2br(markup: Markup | str) -> Markup:
    return Markup(str(markup).replace("\n", "<br>\n"))


def format_text(text: str | None) -> Markup:
    return nl2br(linkify(text or ""))


def escape_like(q: str) -> str:
    """Escape ILIKE metacharacters so user input matches literally (ESCAPE '\\')."""
    return q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def local_time(value: datetime | None, tz: str, fmt: str = "%Y-%m-%d %H:%M") -> str:
    if value is None:
        return ""
    return value.astimezone(ZoneInfo(tz)).strftime(fmt)


def human_size(n: int | None) -> str:
    if n is None:
        return ""
    if n < 1024:
        return f"{n} B"
    kb = n / 1024
    if kb < 1024:
        return f"{kb:.1f} KB"
    return f"{kb / 1024:.1f} MB"


def display_name(
    first: str | None, last: str | None, username: str | None, fallback: str = "unknown"
) -> str:
    name = " ".join(part for part in (first, last) if part).strip()
    if name:
        return name
    if username:
        return f"@{username}"
    return fallback


def group_albums(rows: list[dict]) -> list[list[dict]]:
    """Group consecutive rows sharing a non-null grouped_id (a Telegram album)."""
    albums: list[list[dict]] = []
    for row in rows:
        gid = row.get("grouped_id")
        if albums and gid is not None and albums[-1][-1].get("grouped_id") == gid:
            albums[-1].append(row)
        else:
            albums.append([row])
    return albums
