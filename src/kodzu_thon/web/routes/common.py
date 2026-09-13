"""Dependencies and helpers shared by the page routes."""

from datetime import date, datetime, time
from typing import Annotated
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from fastapi import Depends, HTTPException, Query, Request

from kodzu_thon.web.repository import MAX_PAGE_SIZE, PAGE_SIZE, MessageFilters, Repository

KEYSET_KEYS = ("before", "before_ts", "before_id")


def get_repo(request: Request) -> Repository:
    return request.app.state.repo


RepoDep = Annotated[Repository, Depends(get_repo)]


def parse_filters(
    request: Request,
    q: Annotated[str | None, Query(max_length=200)] = None,
    sender: Annotated[int | None, Query(alias="from", ge=1)] = None,
    deleted: Annotated[int, Query(ge=0, le=1)] = 0,
    edited: Annotated[int, Query(ge=0, le=1)] = 0,
    since: Annotated[date | None, Query()] = None,
    until: Annotated[date | None, Query()] = None,
) -> MessageFilters:
    tz = ZoneInfo(request.app.state.settings.timezone)
    return MessageFilters(
        q=(q or "").replace("\x00", "").strip() or None,
        sender_id=sender,
        deleted_only=bool(deleted),
        edited_only=bool(edited),
        since=datetime.combine(since, time.min, tz) if since else None,
        until=datetime.combine(until, time.min, tz) if until else None,
    )


FiltersDep = Annotated[MessageFilters, Depends(parse_filters)]


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
