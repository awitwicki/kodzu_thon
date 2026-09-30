"""Keeps the archive's forum topic titles current. The first message seen from a forum
chat in this process triggers a fetch of all its topics; afterwards only topics not yet
seen (new ones) and topics whose edit service message arrives are fetched. Like the
media fetcher, failures are logged and not retried until restart."""

import asyncio
import sys
from collections.abc import Coroutine
from typing import Any

from telethon.tl import functions

from kodzu_thon.services.message_extract import MessageRecord, TopicRecord, topic_record

PAGE_SIZE = 100
MAX_PAGES = 50  # 5000 topics; guards against a server that never stops paginating


def _log(msg: str) -> None:
    print(f"forum_topics: {msg}", file=sys.stderr)


class TopicTracker:
    def __init__(self, client, store) -> None:
        self._client = client
        self._store = store
        self._known: dict[int, set[int]] = {}  # chat_id -> topic ids recorded this process
        self._syncing: set[int] = set()
        self._tasks: set[asyncio.Task] = set()

    @property
    def pending(self) -> int:
        return len(self._tasks)

    def observe(self, chat_entity: Any, record: MessageRecord) -> None:
        """Called for every recorded message; fetches titles of topics not seen yet."""
        if record.topic_id is None or not self._store.enabled:
            return
        chat_id = record.chat.id
        known = self._known.get(chat_id)
        if known is None:
            self._known[chat_id] = set()
            self._syncing.add(chat_id)
            self._spawn(self._sync_all(chat_entity, chat_id))
        elif chat_id not in self._syncing and record.topic_id not in known:
            known.add(record.topic_id)
            self._spawn(self._fetch_by_id(chat_entity, chat_id, record.topic_id))

    def topic_created(self, chat_id: int, topic_id: int, title: str, icon_emoji_id: int | None):
        if not self._store.enabled:
            return
        self._known.setdefault(chat_id, set()).add(topic_id)
        self._store.enqueue(TopicRecord(chat_id, topic_id, title, icon_emoji_id, closed=False))

    def topic_edited(self, chat_entity: Any, chat_id: int, topic_id: int) -> None:
        """Edit service messages carry only the changed fields, so refetch the topic."""
        if not self._store.enabled:
            return
        self._known.setdefault(chat_id, set()).add(topic_id)
        self._spawn(self._fetch_by_id(chat_entity, chat_id, topic_id))

    async def drain(self) -> None:
        while self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)

    async def stop(self) -> None:
        for task in list(self._tasks):
            task.cancel()
        await self.drain()

    # ---- internals --------------------------------------------------------

    def _spawn(self, coro: Coroutine) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def _record(self, chat_id: int, topics: list[Any]) -> None:
        known = self._known.setdefault(chat_id, set())
        for topic in topics:
            rec = topic_record(chat_id, topic)
            known.add(topic.id)
            if rec is not None:
                self._store.enqueue(rec)

    async def _sync_all(self, chat_entity: Any, chat_id: int) -> None:
        offset_date, offset_id, offset_topic = None, 0, 0
        try:
            for _ in range(MAX_PAGES):
                result = await self._client(
                    functions.channels.GetForumTopicsRequest(
                        channel=chat_entity,
                        offset_date=offset_date,
                        offset_id=offset_id,
                        offset_topic=offset_topic,
                        limit=PAGE_SIZE,
                    )
                )
                self._record(chat_id, result.topics)
                if len(result.topics) < PAGE_SIZE:
                    break
                last = result.topics[-1]
                if last.id == offset_topic:
                    break
                dates = {m.id: m.date for m in result.messages if hasattr(m, "date")}
                offset_topic = last.id
                offset_id = getattr(last, "top_message", 0)
                offset_date = dates.get(offset_id, getattr(last, "date", None))
        except Exception as e:
            _log(f"sync of {chat_id} failed: {e}")
        finally:
            self._syncing.discard(chat_id)

    async def _fetch_by_id(self, chat_entity: Any, chat_id: int, topic_id: int) -> None:
        try:
            result = await self._client(
                functions.channels.GetForumTopicsByIDRequest(
                    channel=chat_entity, topics=[topic_id]
                )
            )
            self._record(chat_id, result.topics)
        except Exception as e:
            _log(f"fetch of topic {topic_id} in {chat_id} failed: {e}")
