"""Graph of chats and the people they share."""

from fastapi import APIRouter, Request

from kodzu_thon.web.graph import shared_members_graph
from kodzu_thon.web.render import render
from kodzu_thon.web.routes.common import RepoDep
from kodzu_thon.web.security import SessionDep
from kodzu_thon.web.textfmt import display_name

router = APIRouter()


@router.get("/graph")
async def chats_graph(request: Request, session: SessionDep, repo: RepoDep):
    chats = {c["id"]: c["title"] for c in await repo.list_chats()}
    rows = [
        {
            "user_id": r["user_id"],
            "chat_id": r["chat_id"],
            "name": display_name(
                r["first_name"], r["last_name"], r["username"], fallback=f"user {r['user_id']}"
            ),
        }
        for r in await repo.shared_members()
        if r["chat_id"] in chats
    ]
    return render(request, "graph.html", session=session, graph=shared_members_graph(rows, chats))
