"""Global full-text search across all recorded messages."""

from fastapi import APIRouter, HTTPException, Request

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


@router.get("/search")
async def search(
    request: Request,
    session: SessionDep,
    repo: RepoDep,
    filters: FiltersDep,
    limit: LimitDep,
    keyset: KeysetDep,
):
    if not filters.q:
        raise HTTPException(status_code=422, detail="q is required")
    chat_options = await repo.list_chats()
    rows = await repo.search_messages(before=keyset, limit=limit, filters=filters)
    page, last = paginate(rows, limit)
    next_url = (
        next_page_url(request, before_ts=last["sent_at"].isoformat(), before_id=last["id"])
        if last
        else None
    )
    return render(
        request,
        "search.html",
        session=session,
        albums=group_albums(page),
        next_url=next_url,
        filters=filters,
        q=filters.q,
        chat_options=chat_options,
    )
