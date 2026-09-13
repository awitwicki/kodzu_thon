from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from kodzu_thon.web.routes.common import RepoDep

router = APIRouter()


@router.get("/healthz")
async def healthz(repo: RepoDep) -> PlainTextResponse:
    ok = await repo.ping()
    return PlainTextResponse("ok" if ok else "unavailable", status_code=200 if ok else 503)
