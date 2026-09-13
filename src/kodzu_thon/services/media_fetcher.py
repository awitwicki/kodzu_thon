"""Downloads message media and profile photos through the Telethon client and
hands the bytes to the MessageStore as BlobRecords. Bounded by a semaphore and
two LRU caches so nothing is fetched twice per process lifetime."""

import asyncio
import hashlib
import sys
from collections.abc import Coroutine
from typing import Any

from cachetools import LRUCache

from kodzu_thon.services.message_extract import (
    DOWNLOADABLE_MEDIA_TYPES,
    BlobRecord,
    ChatPhotoTarget,
    MediaSkipped,
    MessageRecord,
    MessageTarget,
    UserPhotoTarget,
)


def _log(msg: str) -> None:
    print(f"media_fetcher: {msg}", file=sys.stderr)


# Caps the number of in-flight (queued + downloading) tasks. The semaphore already
# bounds concurrent downloads; this bounds how many can be pending behind it, so a
# large catch_up backlog after an outage cannot spawn one task per media message at
# once. An item skipped at the cap is simply not fetched this run (same "not retried
# until restart" semantics as a failed download).
MAX_PENDING_TASKS = 200


class MediaFetcher:
    def __init__(
        self, client, store, max_bytes: int, *, concurrency: int = 3, cache_size: int = 10_000
    ) -> None:
        self._client = client
        self._store = store
        self._max_bytes = max_bytes
        self._sem = asyncio.Semaphore(concurrency)
        self._media_seen: LRUCache = LRUCache(maxsize=cache_size)  # (chat_id, msg_id) -> media_id
        self._photo_seen: LRUCache = LRUCache(maxsize=cache_size)  # (kind, entity_id) -> photo_id
        self._tasks: set[asyncio.Task] = set()

    @property
    def pending(self) -> int:
        return len(self._tasks)

    def schedule_for_message(self, message: Any, record: MessageRecord) -> None:
        if not self._store.connected:
            return
        if record.media_type not in DOWNLOADABLE_MEDIA_TYPES:
            return
        meta = record.media_meta or {}
        media_id = meta.get("media_id")
        if meta.get("skipped") is not None or media_id is None:
            return
        if (record.media_size or 0) > self._max_bytes:
            return
        key = (record.chat.id, record.id)
        if self._media_seen.get(key) == media_id:
            return
        if len(self._tasks) >= MAX_PENDING_TASKS:
            _log(f"pending task cap ({MAX_PENDING_TASKS}) reached, skipping media for {key}")
            return
        self._spawn(
            self._fetch_message_media(
                message, record.chat.id, record.id, media_id, meta.get("mime")
            )
        )

    def schedule_profile_photos(
        self, chat_entity: Any, sender_entity: Any, record: MessageRecord
    ) -> None:
        if not self._store.connected:
            return
        targets: dict[tuple[str, int], tuple[Any, int]] = {}
        self._add_photo_target(targets, "chat", chat_entity, record.chat)
        if record.sender_user is not None:
            self._add_photo_target(targets, "user", sender_entity, record.sender_user)
        elif record.sender_chat is not None:
            self._add_photo_target(targets, "chat", sender_entity, record.sender_chat)
        for (kind, entity_id), (entity, photo_id) in targets.items():
            if len(self._tasks) >= MAX_PENDING_TASKS:
                _log(
                    f"pending task cap ({MAX_PENDING_TASKS}) reached, "
                    f"skipping photo for {kind} {entity_id}"
                )
                continue
            self._spawn(self._fetch_profile_photo(kind, entity, entity_id, photo_id))

    async def drain(self) -> None:
        while self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)

    async def stop(self) -> None:
        for task in list(self._tasks):
            task.cancel()
        await self.drain()

    # ---- internals --------------------------------------------------------

    def _add_photo_target(self, targets: dict, kind: str, entity: Any, snap: Any) -> None:
        if snap.photo_id is None or entity is None:
            return
        key = (kind, snap.id)
        if self._photo_seen.get(key) == snap.photo_id:
            return
        targets[key] = (entity, snap.photo_id)

    def _spawn(self, coro: Coroutine) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _fetch_message_media(
        self, message: Any, chat_id: int, message_id: int, media_id: int, mime: str | None
    ) -> None:
        key = (chat_id, message_id)
        if await self._store.message_media_is_current(chat_id, message_id, media_id):
            self._media_seen[key] = media_id
            return
        try:
            async with self._sem:
                data = await message.download_media(file=bytes)
            if not data:
                raise RuntimeError("empty download")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            _log(f"download failed for message {chat_id}/{message_id}: {e}")
            self._store.enqueue(MediaSkipped(chat_id, message_id, media_id, "download_failed"))
            self._media_seen[key] = media_id
            return
        self._store.enqueue(
            BlobRecord(
                target=MessageTarget(chat_id, message_id, media_id),
                sha256=hashlib.sha256(data).digest(),
                mime_type=mime or "application/octet-stream",
                data=data,
            )
        )
        self._media_seen[key] = media_id

    async def _fetch_profile_photo(
        self, kind: str, entity: Any, entity_id: int, photo_id: int
    ) -> None:
        key = (kind, entity_id)
        if await self._store.photo_is_current(kind, entity_id, photo_id):
            self._photo_seen[key] = photo_id
            return
        try:
            async with self._sem:
                data = await self._client.download_profile_photo(entity, file=bytes)
            if not data:
                raise RuntimeError("empty download")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            _log(f"profile photo download failed for {kind} {entity_id}: {e}")
            self._photo_seen[key] = photo_id
            return
        target = (
            UserPhotoTarget(entity_id, photo_id)
            if kind == "user"
            else ChatPhotoTarget(entity_id, photo_id)
        )
        self._store.enqueue(
            BlobRecord(
                target=target,
                sha256=hashlib.sha256(data).digest(),
                mime_type="image/jpeg",
                data=data,
            )
        )
        self._photo_seen[key] = photo_id
