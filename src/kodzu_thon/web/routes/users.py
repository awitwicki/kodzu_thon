"""User profile: identity, name history, chats and messages."""

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


@router.get("/users/{user_id}")
async def user_profile(
    request: Request,
    session: SessionDep,
    repo: RepoDep,
    user_id: Annotated[int, Path(ge=1)],
    filters: FiltersDep,
    limit: LimitDep,
    keyset: KeysetDep,
):
    user = await repo.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=404)
    history = await repo.user_name_history(user_id)
    chats = await repo.user_chats(user_id)
    rows = await repo.user_messages(user_id, before=keyset, limit=limit, filters=filters)
    page, last = paginate(rows, limit)
    next_url = (
        next_page_url(request, before_ts=last["sent_at"].isoformat(), before_id=last["id"])
        if last
        else None
    )
    return render(
        request,
        "user.html",
        session=session,
        user=user,
        history=history,
        chats=chats,
        albums=group_albums(page),
        next_url=next_url,
        filters=filters,
        q=filters.q,
    )
