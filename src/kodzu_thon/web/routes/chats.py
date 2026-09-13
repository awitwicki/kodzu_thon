"""Chat list and per-chat timeline."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, Request

from kodzu_thon.web.render import render
from kodzu_thon.web.routes.common import (
    FiltersDep,
    LimitDep,
    RepoDep,
    next_page_url,
    paginate,
)
from kodzu_thon.web.security import SessionDep
from kodzu_thon.web.textfmt import group_albums

router = APIRouter()


@router.get("/")
async def chat_list(request: Request, session: SessionDep, repo: RepoDep):
    chats = await repo.list_chats()
    return render(request, "chats.html", session=session, chats=chats)


@router.get("/chats/{chat_id}")
async def chat_timeline(
    request: Request,
    session: SessionDep,
    repo: RepoDep,
    chat_id: Annotated[int, Path()],
    filters: FiltersDep,
    limit: LimitDep,
    before: Annotated[int | None, Query(ge=1)] = None,
):
    chat = await repo.get_chat(chat_id)
    if chat is None:
        raise HTTPException(status_code=404)
    rows = await repo.chat_messages(chat_id, before_id=before, limit=limit, filters=filters)
    page, last = paginate(rows, limit)
    next_url = next_page_url(request, before=last["id"]) if last else None
    return render(
        request,
        "chat.html",
        session=session,
        chat=chat,
        albums=group_albums(page),
        next_url=next_url,
        filters=filters,
        q=filters.q,
    )
