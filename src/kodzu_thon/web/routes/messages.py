"""Message permalink (with edit history and raw JSON) and the global deleted feed."""

import json
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Request

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


@router.get("/chats/{chat_id}/messages/{message_id}")
async def message_permalink(
    request: Request,
    session: SessionDep,
    repo: RepoDep,
    chat_id: Annotated[int, Path()],
    message_id: Annotated[int, Path(ge=1)],
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
        raw_json=raw_json,
    )


@router.get("/deleted")
async def deleted_feed(
    request: Request,
    session: SessionDep,
    repo: RepoDep,
    filters: FiltersDep,
    limit: LimitDep,
    keyset: KeysetDep,
):
    chat_options = await repo.list_chats()
    rows = await repo.deleted_messages(before=keyset, limit=limit, filters=filters)
    page, last = paginate(rows, limit)
    next_url = (
        next_page_url(request, before_ts=last["deleted_at"].isoformat(), before_id=last["id"])
        if last
        else None
    )
    return render(
        request,
        "deleted.html",
        session=session,
        albums=group_albums(page),
        next_url=next_url,
        filters=filters,
        compact=True,
        chat_options=chat_options,
    )
