"""Chat list and per-chat timeline."""

from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Path, Query, Request

from kodzu_thon.web import auth
from kodzu_thon.web.chart import activity_chart
from kodzu_thon.web.render import render
from kodzu_thon.web.routes.common import (
    ChatFiltersDep,
    LimitDep,
    RepoDep,
    default_since,
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
    filters: ChatFiltersDep,
    limit: LimitDep,
    before: Annotated[int | None, Query(ge=1)] = None,
):
    chat = await repo.get_chat(chat_id)
    if chat is None:
        raise HTTPException(status_code=404)
    topics = await repo.chat_topics(chat_id) if chat["is_forum"] else []
    topic = next((t for t in topics if t["id"] == filters.topic_id), None)
    timezone = request.app.state.settings.timezone
    chart_since = default_since(request)
    activity = await repo.chat_activity(chat_id, chart_since, timezone)
    chart = activity_chart(
        activity,
        start=chart_since.date(),
        end=auth.utcnow().astimezone(ZoneInfo(timezone)).date(),
    )
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
        show_hide_bots=True,
        topics=topics,
        topic=topic,
        chart=chart,
    )
