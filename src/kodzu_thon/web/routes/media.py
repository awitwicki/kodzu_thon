"""Serves stored blobs. Only a short allow-list of image/video/audio types is sent
inline; everything else is a download, so a stored HTML/SVG file can never run
in the viewer's origin."""

import re
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, Response

from kodzu_thon.web.routes.common import RepoDep
from kodzu_thon.web.security import SessionDep

router = APIRouter()

INLINE_TYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
        "video/mp4",
        "video/webm",
        "audio/ogg",
        "audio/mpeg",
        "audio/mp4",
    }
)
_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")
CACHE_CONTROL = "private, max-age=86400"


def safe_filename(name: str | None, blob_id: int) -> str:
    cleaned = _UNSAFE.sub("_", name or "").strip("._")[:100].strip("._")
    return cleaned or f"blob-{blob_id}"


@router.get("/media/{blob_id}")
async def media(
    session: SessionDep,
    repo: RepoDep,
    blob_id: Annotated[int, Path(ge=1)],
    filename: Annotated[str | None, Query(max_length=255)] = None,
) -> Response:
    blob = await repo.get_blob(blob_id)
    if blob is None:
        raise HTTPException(status_code=404)
    headers = {"Cache-Control": CACHE_CONTROL}
    mime = blob["mime_type"]
    if mime in INLINE_TYPES:
        return Response(content=blob["data"], media_type=mime, headers=headers)
    headers["Content-Disposition"] = f'attachment; filename="{safe_filename(filename, blob_id)}"'
    return Response(content=blob["data"], media_type="application/octet-stream", headers=headers)
