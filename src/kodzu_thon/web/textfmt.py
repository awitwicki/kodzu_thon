"""Pure text/formatting helpers for templates. No I/O, no Jinja dependency."""

import difflib
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


_TOKEN_RE = re.compile(r"\n|[^\S\n]+|\w+|[^\w\s]", re.UNICODE)


def _marked_lines(tokens: list[tuple[str, bool]], tag: str) -> list[str]:
    """Join (token, changed) pairs into escaped lines, wrapping changed tokens in `tag`.
    Newlines are tokens of their own, so a tag never spans two lines."""
    lines = [""]
    for token, changed in tokens:
        if token == "\n":
            lines.append("")
        elif changed:
            lines[-1] += f"<{tag}>{escape(token)}</{tag}>"
        else:
            lines[-1] += str(escape(token))
    return lines


def _diff_row(sign: str, cls: str, line: str) -> str:
    return f'<div class="dl {cls}"><span class="sign">{sign}</span><span>{line}</span></div>'


def git_diff(old: str | None, new: str | None) -> Markup:
    """Line diff in git style: removed lines `-`, added lines `+`, unchanged lines as
    context; inside a changed block the words that differ are wrapped in <del>/<ins>.
    Every token is escaped before it is wrapped."""
    a = (old or "").split("\n") if old else []
    b = (new or "").split("\n") if new else []
    rows: list[str] = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == "equal":
            rows += [_diff_row("&nbsp;", "ctx", str(escape(line))) for line in a[i1:i2]]
            continue
        ta = _TOKEN_RE.findall("\n".join(a[i1:i2]))
        tb = _TOKEN_RE.findall("\n".join(b[j1:j2]))
        old_side: list[tuple[str, bool]] = []
        new_side: list[tuple[str, bool]] = []
        words = difflib.SequenceMatcher(None, ta, tb, autojunk=False).get_opcodes()
        for wop, k1, k2, l1, l2 in words:
            # A pure insert/delete block is highlighted by its row colour alone.
            changed = wop != "equal" and op == "replace"
            old_side += [(t, changed) for t in ta[k1:k2]]
            new_side += [(t, changed) for t in tb[l1:l2]]
        if i2 > i1:
            rows += [_diff_row("-", "del", ln) for ln in _marked_lines(old_side, "del")]
        if j2 > j1:
            rows += [_diff_row("+", "add", ln) for ln in _marked_lines(new_side, "ins")]
    return Markup(f'<div class="gitdiff">{"".join(rows)}</div>')


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


def topic_name(topic_id: int, title: str | None) -> str:
    """Title of a forum topic; General (id 1) has no creation message to take one from."""
    if title:
        return title
    return "General" if topic_id == 1 else f"topic #{topic_id}"


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
