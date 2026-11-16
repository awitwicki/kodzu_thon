"""Message permalink (with edit history and raw JSON) and the global feed of deleted and
edited messages."""

import json
from typing import Annotated, Literal
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Path, Query, Request
from fastapi.responses import RedirectResponse

from kodzu_thon.web.render import render
from kodzu_thon.web.routes.common import (
    FiltersDep,
    KeysetDep,
    LimitDep,
    RepoDep,
    next_page_url,
    paginate,
)
from kodzu_thon.web.security import SessionDep
from kodzu_thon.web.textfmt import group_albums

router = APIRouter()

# Dropped when switching between the deleted and edited tabs: the keyset belongs to one feed.
TAB_KEYS = ("show", "before_ts", "before_id")


@router.get("/chats/{chat_id}/messages/{message_id}")
async def message_permalink(
    request: Request,
    session: SessionDep,
    repo: RepoDep,
    chat_id: Annotated[int, Path()],
    message_id: Annotated[int, Path(ge=1)],
    view: Annotated[Literal["text", "diff"], Query()] = "text",
):
    message = await repo.get_message(chat_id, message_id)
    if message is None:
        raise HTTPException(status_code=404)
    edits = await repo.message_edits(chat_id, message_id)
    raw_json = json.dumps(
        message.get("raw"), indent=2, ensure_ascii=False, sort_keys=True, default=str
    )
    return render(
        request,
        "message.html",
        session=session,
        message=message,
        album=[message],
        edits=edits,
        view=view,
        raw_json=raw_json,
    )


@router.get("/changes")
async def changes_feed(
    request: Request,
    session: SessionDep,
    repo: RepoDep,
    filters: FiltersDep,
    limit: LimitDep,
    keyset: KeysetDep,
    show: Literal["deleted", "edited"] = "deleted",
):
    """Messages that were deleted or edited, across all chats, newest change first."""
    chat_options = await repo.list_chats()
    fetch, changed_at = {
        "deleted": (repo.deleted_messages, "deleted_at"),
        "edited": (repo.edited_messages, "edited_at"),
    }[show]
    rows = await fetch(before=keyset, limit=limit, filters=filters)
    page, last = paginate(rows, limit)
    next_url = (
        next_page_url(request, before_ts=last[changed_at].isoformat(), before_id=last["id"])
        if last
        else None
    )
    tab_query = [(k, v) for k, v in request.query_params.multi_items() if k not in TAB_KEYS]
    return render(
        request,
        "changes.html",
        session=session,
        albums=group_albums(page),
        next_url=next_url,
        filters=filters,
        compact=True,
        chat_options=chat_options,
        show_kind=True,
        show_hide_bots=True,
        show=show,
        tab_urls={
            tab: f"/changes?{urlencode([*tab_query, ('show', tab)])}"
            for tab in ("deleted", "edited")
        },
    )


@router.get("/deleted")
async def deleted_feed_moved(request: Request, session: SessionDep):
    """The deleted feed became one tab of /changes; keep old links working."""
    query = request.url.query
    return RedirectResponse("/changes" + (f"?{query}" if query else ""), status_code=308)
