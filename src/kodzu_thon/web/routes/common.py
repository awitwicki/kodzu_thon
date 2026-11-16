"""Dependencies and helpers shared by the page routes."""

from datetime import date, datetime, time, timedelta
from typing import Annotated
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from fastapi import Depends, HTTPException, Query, Request

from kodzu_thon.web import auth
from kodzu_thon.web.repository import (
    CHAT_KINDS,
    MAX_PAGE_SIZE,
    PAGE_SIZE,
    MessageFilters,
    Repository,
)

KEYSET_KEYS = ("before", "before_ts", "before_id")


def get_repo(request: Request) -> Repository:
    return request.app.state.repo


RepoDep = Annotated[Repository, Depends(get_repo)]


def _parse_int(name: str, raw: str | None, *, ge: int | None = None) -> int | None:
    """Query(...) alone 422s a blank value (e.g. `from=`) instead of treating it as
    absent, but the filter form always submits every field, blank ones included."""
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"{name} must be an integer") from None
    if ge is not None and value < ge:
        raise HTTPException(status_code=422, detail=f"{name} must be >= {ge}") from None
    return value


def _parse_date(name: str, raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"{name} must be a date") from None


def _parse_chat_kind(raw: list[str]) -> str | None:
    """The form has one `kind` checkbox per CHAT_KINDS entry. Unchecked boxes aren't
    submitted, so none checked (a first visit) and all checked both mean no filter."""
    kinds = set(raw)
    if not kinds <= CHAT_KINDS.keys():
        raise HTTPException(status_code=422, detail="kind must be one of " + ", ".join(CHAT_KINDS))
    return kinds.pop() if len(kinds) == 1 else None


DEFAULT_SINCE_DAYS = 30


def default_since(request: Request) -> datetime:
    """Midnight (viewer timezone) DEFAULT_SINCE_DAYS ago: where "recent" pages start."""
    tz = ZoneInfo(request.app.state.settings.timezone)
    today = auth.utcnow().astimezone(tz).date()
    return datetime.combine(today - timedelta(days=DEFAULT_SINCE_DAYS), time.min, tz)


def filters_dependency(*, recent_by_default: bool = False, hide_bots_by_default: bool = False):
    """Builds the filter-parsing dependency for a page.

    `recent_by_default`: with no `since` in the URL, show the last DEFAULT_SINCE_DAYS days.
    A blank `since=` (the form submitted with the date cleared) means all time.
    `hide_bots_by_default`: with no `nobots` in the URL, hide bots. The form sends a hidden
    `nobots=0` ahead of the checkbox, so unchecking it is distinguishable from a first visit
    (the last value wins)."""

    def parse_filters(
        request: Request,
        q: Annotated[str | None, Query(max_length=200)] = None,
        chat: Annotated[str | None, Query()] = None,
        sender: Annotated[str | None, Query(alias="from")] = None,
        deleted: Annotated[int, Query(ge=0, le=1)] = 0,
        edited: Annotated[int, Query(ge=0, le=1)] = 0,
        since: Annotated[str | None, Query()] = None,
        until: Annotated[str | None, Query()] = None,
        kind: Annotated[list[str] | None, Query()] = None,
        nobots: Annotated[int | None, Query(ge=0, le=1)] = None,
        topic: Annotated[str | None, Query()] = None,
    ) -> MessageFilters:
        tz = ZoneInfo(request.app.state.settings.timezone)
        since_date = _parse_date("since", since)
        until_date = _parse_date("until", until)
        since_at = datetime.combine(since_date, time.min, tz) if since_date else None
        if since is None and recent_by_default:
            since_at = default_since(request)
        return MessageFilters(
            q=(q or "").replace("\x00", "").strip() or None,
            chat_id=_parse_int("chat", chat),
            sender_id=_parse_int("from", sender, ge=1),
            deleted_only=bool(deleted),
            edited_only=bool(edited),
            since=since_at,
            until=datetime.combine(until_date, time.min, tz) if until_date else None,
            chat_kind=_parse_chat_kind(kind or []),
            hide_bots=hide_bots_by_default if nobots is None else bool(nobots),
            topic_id=_parse_int("topic", topic, ge=1),
        )

    return parse_filters


# Feeds without date inputs (deleted / edited).
FiltersDep = Annotated[MessageFilters, Depends(filters_dependency())]
# Pages with a "since" input: search results and a user's messages.
RecentFiltersDep = Annotated[MessageFilters, Depends(filters_dependency(recent_by_default=True))]
# A chat's timeline.
ChatFiltersDep = Annotated[
    MessageFilters,
    Depends(filters_dependency(recent_by_default=True, hide_bots_by_default=True)),
]


def page_limit(limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = PAGE_SIZE) -> int:
    return limit


LimitDep = Annotated[int, Depends(page_limit)]


def parse_keyset(
    before_ts: Annotated[datetime | None, Query()] = None,
    before_id: Annotated[int | None, Query(ge=1)] = None,
) -> tuple[datetime, int] | None:
    if (before_ts is None) != (before_id is None):
        raise HTTPException(status_code=422, detail="before_ts and before_id go together")
    if before_ts is None:
        return None
    if before_ts.tzinfo is None:
        raise HTTPException(status_code=422, detail="before_ts must carry a timezone")
    return before_ts, before_id


KeysetDep = Annotated[tuple[datetime, int] | None, Depends(parse_keyset)]


def next_page_url(request: Request, **keyset: object) -> str:
    params = [(k, v) for k, v in request.query_params.multi_items() if k not in KEYSET_KEYS]
    params += [(k, str(v)) for k, v in keyset.items()]
    return f"{request.url.path}?{urlencode(params)}"


def paginate(rows: list[dict], limit: int) -> tuple[list[dict], dict | None]:
    """Split a limit+1 fetch into (page, last row of the page if there is a next page)."""
    if len(rows) > limit:
        return rows[:limit], rows[limit - 1]
    return rows, None
