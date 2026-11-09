"""Serves stored blobs. Only a short allow-list of image/video/audio types is sent
inline; everything else is a download, so a stored HTML/SVG file can never run
in the viewer's origin."""

import re
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Path, Query, Response

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
_RANGE = re.compile(r"bytes=(\d*)-(\d*)")
CACHE_CONTROL = "private, max-age=86400"


def safe_filename(name: str | None, blob_id: int) -> str:
    cleaned = _UNSAFE.sub("_", name or "").strip("._")[:100].strip("._")
    return cleaned or f"blob-{blob_id}"


def parse_range(header: str | None, size: int) -> tuple[int, int] | None:
    """Single `bytes=` range -> inclusive (start, end); None means serve the whole body.
    Raises 416 for a well-formed range that lies outside the blob."""
    match = _RANGE.fullmatch((header or "").strip())
    if match is None or match.groups() == ("", ""):
        return None
    first, last = match.groups()
    if first == "":  # suffix range: the last N bytes
        start, end = max(size - int(last), 0), size - 1
    else:
        start = int(first)
        end = min(int(last), size - 1) if last else size - 1
    if start >= size or start > end:
        raise HTTPException(status_code=416, headers={"Content-Range": f"bytes */{size}"})
    return start, end


@router.get("/media/{blob_id}")
async def media(
    session: SessionDep,
    repo: RepoDep,
    blob_id: Annotated[int, Path(ge=1)],
    filename: Annotated[str | None, Query(max_length=255)] = None,
    range_header: Annotated[str | None, Header(alias="Range")] = None,
) -> Response:
    blob = await repo.get_blob(blob_id)
    if blob is None:
        raise HTTPException(status_code=404)
    data = blob["data"]
    # Safari refuses to play <audio>/<video> from a server without byte ranges.
    headers = {"Cache-Control": CACHE_CONTROL, "Accept-Ranges": "bytes"}
    mime = blob["mime_type"]
    if mime not in INLINE_TYPES:
        headers["Content-Disposition"] = (
            f'attachment; filename="{safe_filename(filename, blob_id)}"'
        )
        mime = "application/octet-stream"
    byte_range = parse_range(range_header, len(data))
    if byte_range is None:
        return Response(content=data, media_type=mime, headers=headers)
    start, end = byte_range
    headers["Content-Range"] = f"bytes {start}-{end}/{len(data)}"
    return Response(
        content=data[start : end + 1], status_code=206, media_type=mime, headers=headers
    )
