import asyncio
import hashlib
from unittest.mock import AsyncMock, MagicMock

import pytest

from kodzu_thon.services.media_fetcher import MAX_PENDING_TASKS, MediaFetcher
from kodzu_thon.services.message_extract import (
    BlobRecord,
    ChatPhotoTarget,
    ChatSnapshot,
    MediaSkipped,
    MessageRecord,
    MessageTarget,
    UserPhotoTarget,
    UserSnapshot,
)
from tests.factories import NOW, make_supergroup, make_user

CHAT = ChatSnapshot(id=-1000000000124, type="supergroup", title="Grp", username=None, photo_id=555)
USER = UserSnapshot(
    id=7,
    first_name="Ann",
    last_name="Lee",
    username="ann",
    is_bot=False,
    is_self=False,
    photo_id=777,
)
MAX = 5 * 1024 * 1024


def make_record(
    msg_id=1,
    media_type="photo",
    media_id=1000,
    skipped=None,
    mime="image/jpeg",
    chat=CHAT,
    sender_user=USER,
    sender_chat=None,
    media_size=100,
):
    meta = None
    if media_type is not None:
        meta = {
            "media_id": media_id,
            "mime": mime,
            "filename": None,
            "width": None,
            "height": None,
            "duration": None,
            "skipped": skipped,
        }
    return MessageRecord(
        chat=chat,
        sender_user=sender_user,
        sender_chat=sender_chat,
        id=msg_id,
        is_outgoing=False,
        sent_at=NOW,
        text=None,
        reply_to_msg_id=None,
        grouped_id=None,
        fwd_from_user_id=None,
        fwd_from_chat_id=None,
        fwd_from_name=None,
        fwd_date=None,
        media_type=media_type,
        media_size=media_size,
        media_meta=meta,
        raw={},
    )


@pytest.fixture
def store():
    s = MagicMock()
    s.connected = True
    s.enqueue = MagicMock()
    s.message_media_is_current = AsyncMock(return_value=False)
    s.photo_is_current = AsyncMock(return_value=False)
    return s


@pytest.fixture
def client():
    c = MagicMock()
    c.download_profile_photo = AsyncMock(return_value=b"jpegbytes")
    return c


def make_message(data=b"abc"):
    m = MagicMock()
    m.download_media = AsyncMock(return_value=data)
    return m


async def test_downloads_and_enqueues_blob(store, client):
    fetcher = MediaFetcher(client, store, MAX)
    msg = make_message(b"abc")
    fetcher.schedule_for_message(msg, make_record())
    assert fetcher.pending == 1
    await fetcher.drain()

    msg.download_media.assert_awaited_once_with(file=bytes)
    blob = store.enqueue.call_args.args[0]
    assert isinstance(blob, BlobRecord)
    assert blob.target == MessageTarget(CHAT.id, 1, 1000)
    assert blob.sha256 == hashlib.sha256(b"abc").digest()
    assert blob.mime_type == "image/jpeg" and blob.data == b"abc"


async def test_same_message_is_not_downloaded_twice(store, client):
    fetcher = MediaFetcher(client, store, MAX)
    msg = make_message()
    fetcher.schedule_for_message(msg, make_record())
    await fetcher.drain()
    fetcher.schedule_for_message(msg, make_record())
    await fetcher.drain()
    assert msg.download_media.await_count == 1


async def test_replaced_media_on_same_message_is_downloaded(store, client):
    fetcher = MediaFetcher(client, store, MAX)
    msg = make_message()
    fetcher.schedule_for_message(msg, make_record(media_id=1000))
    await fetcher.drain()
    fetcher.schedule_for_message(msg, make_record(media_id=2000))
    await fetcher.drain()
    assert msg.download_media.await_count == 2


async def test_skips_when_store_disconnected(store, client):
    store.connected = False
    fetcher = MediaFetcher(client, store, MAX)
    fetcher.schedule_for_message(make_message(), make_record())
    fetcher.schedule_profile_photos(make_supergroup(), make_user(), make_record())
    assert fetcher.pending == 0


async def test_skips_non_downloadable_and_already_skipped(store, client):
    fetcher = MediaFetcher(client, store, MAX)
    fetcher.schedule_for_message(make_message(), make_record(media_type="webpage", media_id=None))
    fetcher.schedule_for_message(make_message(), make_record(media_type=None))
    fetcher.schedule_for_message(make_message(), make_record(skipped="too_large"))
    assert fetcher.pending == 0


async def test_store_already_has_blob_short_circuits(store, client):
    store.message_media_is_current = AsyncMock(return_value=True)
    fetcher = MediaFetcher(client, store, MAX)
    msg = make_message()
    fetcher.schedule_for_message(msg, make_record())
    await fetcher.drain()
    msg.download_media.assert_not_awaited()
    store.enqueue.assert_not_called()
    fetcher.schedule_for_message(msg, make_record())
    assert fetcher.pending == 0  # remembered in the LRU


async def test_download_failure_enqueues_media_skipped(store, client, capsys):
    fetcher = MediaFetcher(client, store, MAX)
    msg = make_message()
    msg.download_media = AsyncMock(side_effect=RuntimeError("file reference expired"))
    fetcher.schedule_for_message(msg, make_record())
    await fetcher.drain()
    assert store.enqueue.call_args.args[0] == MediaSkipped(CHAT.id, 1, 1000, "download_failed")
    assert "file reference expired" in capsys.readouterr().err
    fetcher.schedule_for_message(msg, make_record())
    assert fetcher.pending == 0  # not retried until restart


async def test_empty_download_counts_as_failure(store, client):
    fetcher = MediaFetcher(client, store, MAX)
    fetcher.schedule_for_message(make_message(b""), make_record())
    await fetcher.drain()
    assert isinstance(store.enqueue.call_args.args[0], MediaSkipped)


async def test_profile_photos_for_chat_and_user(store, client):
    fetcher = MediaFetcher(client, store, MAX)
    chat, user = make_supergroup(), make_user()
    fetcher.schedule_profile_photos(chat, user, make_record())
    assert fetcher.pending == 2
    await fetcher.drain()

    targets = {call.args[0].target for call in store.enqueue.call_args_list}
    assert targets == {ChatPhotoTarget(CHAT.id, 555), UserPhotoTarget(7, 777)}
    for call in store.enqueue.call_args_list:
        assert call.args[0].mime_type == "image/jpeg"
    entities = [c.args[0] for c in client.download_profile_photo.await_args_list]
    assert chat in entities and user in entities


async def test_profile_photo_skipped_when_none_or_seen(store, client):
    fetcher = MediaFetcher(client, store, MAX)
    chat_no_photo = ChatSnapshot(
        id=CHAT.id, type="supergroup", title="G", username=None, photo_id=None
    )
    fetcher.schedule_profile_photos(make_supergroup(), make_user(), make_record(chat=chat_no_photo))
    assert fetcher.pending == 1  # only the user
    await fetcher.drain()
    fetcher.schedule_profile_photos(make_supergroup(), make_user(), make_record(chat=chat_no_photo))
    assert fetcher.pending == 0


async def test_channel_post_dedupes_chat_and_sender_chat(store, client):
    fetcher = MediaFetcher(client, store, MAX)
    chan = make_supergroup()
    fetcher.schedule_profile_photos(chan, chan, make_record(sender_user=None, sender_chat=CHAT))
    assert fetcher.pending == 1


async def test_stop_cancels_pending(store, client):
    fetcher = MediaFetcher(client, store, MAX)
    msg = make_message()

    async def never(**_):
        await asyncio.sleep(3600)

    msg.download_media = never
    fetcher.schedule_for_message(msg, make_record())
    await fetcher.stop()
    assert fetcher.pending == 0


async def test_oversized_media_is_not_scheduled(store, client):
    fetcher = MediaFetcher(client, store, MAX)
    # skipped=None means the existing "already skipped" check does not catch this;
    # only the max_bytes defense-in-depth check should.
    record = make_record(media_size=MAX + 1, skipped=None)
    fetcher.schedule_for_message(make_message(), record)
    assert fetcher.pending == 0


async def _fill_pending_tasks(fetcher: MediaFetcher, count: int) -> list[asyncio.Task]:
    async def never() -> None:
        await asyncio.sleep(3600)

    fillers = [asyncio.create_task(never()) for _ in range(count)]
    fetcher._tasks.update(fillers)
    return fillers


async def _cleanup_fillers(fillers: list[asyncio.Task]) -> None:
    for t in fillers:
        t.cancel()
    await asyncio.gather(*fillers, return_exceptions=True)


async def test_pending_task_cap_blocks_message_media_spawn(store, client):
    fetcher = MediaFetcher(client, store, MAX)
    fillers = await _fill_pending_tasks(fetcher, MAX_PENDING_TASKS)
    assert fetcher.pending == MAX_PENDING_TASKS

    msg = make_message()
    fetcher.schedule_for_message(msg, make_record())
    assert fetcher.pending == MAX_PENDING_TASKS  # capped: nothing new spawned
    msg.download_media.assert_not_awaited()

    await _cleanup_fillers(fillers)


async def test_pending_task_cap_blocks_profile_photo_spawn(store, client):
    fetcher = MediaFetcher(client, store, MAX)
    fillers = await _fill_pending_tasks(fetcher, MAX_PENDING_TASKS)

    fetcher.schedule_profile_photos(make_supergroup(), make_user(), make_record())
    assert fetcher.pending == MAX_PENDING_TASKS  # capped: nothing new spawned
    client.download_profile_photo.assert_not_awaited()

    await _cleanup_fillers(fillers)
