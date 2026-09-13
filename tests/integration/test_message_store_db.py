import asyncio
import dataclasses
import hashlib
import json

import pytest
from telethon.tl import types

from kodzu_thon.db.migrate import apply_migrations
from kodzu_thon.services.message_extract import (
    BlobRecord,
    DeletionRecord,
    EditRecord,
    MediaSkipped,
    MessageTarget,
    UserPhotoTarget,
    extract_message,
)
from kodzu_thon.services.message_store import MessageStore
from tests.factories import (
    NOW,
    make_chat,
    make_message,
    make_photo_media,
    make_supergroup,
    make_user,
)

pytestmark = pytest.mark.integration
MAX = 5 * 1024 * 1024
GROUP = make_supergroup()  # marked id -1000000000124
GROUP_ID = -1000000000124


def rec(msg_id=1, text="hi", chat=GROUP, sender=None, **kw):
    msg = make_message(id=msg_id, text=text, peer=types.PeerChannel(124), **kw)
    return extract_message(msg, chat, sender or make_user(), max_media_bytes=MAX)


async def write(dsn, *records):
    """Run a fresh store over the records and wait until everything is flushed."""
    store = MessageStore(dsn, batch_size=2)
    await store.start()
    for r in records:
        store.enqueue(r)
    await store.stop()
    assert store.queued == 0


async def connected_store(dsn):
    """A started store that has already connected (the writer connects lazily)."""
    store = MessageStore(dsn)
    await store.start()
    store.enqueue(DeletionRecord(chat_id=GROUP_ID, message_ids=(), observed_at=NOW))
    for _ in range(200):
        if store.connected and store.queued == 0:
            return store
        await asyncio.sleep(0.05)
    raise AssertionError("store did not connect")


async def test_insert_edit_delete_flow(db, dsn):
    await write(
        dsn,
        rec(1, text="hi"),
        EditRecord(message=rec(1, text="hi, edited"), edited_at=NOW),
        DeletionRecord(chat_id=GROUP_ID, message_ids=(1,), observed_at=NOW),
    )
    row = await db.fetchrow("SELECT * FROM messages WHERE chat_id = $1 AND id = 1", GROUP_ID)
    assert row["text"] == "hi, edited" and row["edit_count"] == 1
    assert row["edited_at"] == NOW and row["deleted_at"] == NOW
    assert row["sender_user_id"] == 7 and row["is_outgoing"] is False
    edits = await db.fetch("SELECT * FROM message_edits WHERE chat_id = $1", GROUP_ID)
    assert len(edits) == 1 and edits[0]["old_text"] == "hi"
    assert json.loads(edits[0]["old_raw"])["id"] == 1
    chat = await db.fetchrow("SELECT * FROM chats WHERE id = $1", GROUP_ID)
    assert chat["type"] == "supergroup" and chat["last_message_at"] == NOW
    user = await db.fetchrow("SELECT * FROM users WHERE id = 7")
    assert user["username"] == "ann" and user["photo_id"] == 777


async def test_edit_of_unknown_message_inserts_it(db, dsn):
    await write(dsn, EditRecord(message=rec(9, text="late"), edited_at=NOW))
    row = await db.fetchrow("SELECT text, edit_count, edited_at FROM messages WHERE id = 9")
    assert row["text"] == "late" and row["edit_count"] == 0 and row["edited_at"] == NOW
    assert await db.fetchval("SELECT count(*) FROM message_edits") == 0


async def test_edit_without_change_only_refreshes_raw(db, dsn):
    base = rec(1, text="hi")
    same = dataclasses.replace(base, raw={**base.raw, "views": 5})
    await write(dsn, base, EditRecord(message=same, edited_at=NOW))
    row = await db.fetchrow("SELECT edit_count, raw FROM messages WHERE id = 1")
    assert row["edit_count"] == 0 and json.loads(row["raw"])["views"] == 5


async def test_duplicate_insert_is_ignored(db, dsn):
    await write(dsn, rec(1, text="first"), rec(1, text="second"))
    assert await db.fetchval("SELECT text FROM messages WHERE id = 1") == "first"


async def test_blob_dedup_guards_and_read_helpers(db, dsn):
    data = b"jpegbytes"
    digest = hashlib.sha256(data).digest()
    await write(
        dsn,
        rec(2, text="", media=make_photo_media(photo_id=1000)),
        BlobRecord(MessageTarget(GROUP_ID, 2, 1000), digest, "image/jpeg", data),
        BlobRecord(UserPhotoTarget(7, 777), digest, "image/jpeg", data),
        BlobRecord(UserPhotoTarget(7, 12345), digest, "image/jpeg", data),  # stale photo id
    )
    assert await db.fetchval("SELECT count(*) FROM blobs") == 1
    blob_id = await db.fetchval("SELECT id FROM blobs")
    assert await db.fetchval("SELECT media_blob_id FROM messages WHERE id = 2") == blob_id
    assert await db.fetchval("SELECT photo_blob_id FROM users WHERE id = 7") == blob_id
    meta = json.loads(await db.fetchval("SELECT media_meta FROM messages WHERE id = 2"))
    assert meta["media_id"] == 1000 and meta["skipped"] is None

    store = await connected_store(dsn)
    try:
        assert await store.message_media_is_current(GROUP_ID, 2, 1000) is True
        assert await store.message_media_is_current(GROUP_ID, 2, 1001) is False
        assert await store.photo_is_current("user", 7, 777) is True
        assert await store.photo_is_current("user", 7, 12345) is False
        assert await store.photo_is_current("chat", GROUP_ID, 555) is False  # no chat blob
    finally:
        await store.stop()


async def test_photo_change_resets_blob(db, dsn):
    data = b"x"
    await write(
        dsn,
        rec(1, sender=make_user(photo_id=777)),
        BlobRecord(UserPhotoTarget(7, 777), hashlib.sha256(data).digest(), "image/jpeg", data),
    )
    assert await db.fetchval("SELECT photo_blob_id FROM users WHERE id = 7") is not None
    await write(dsn, rec(2, sender=make_user(photo_id=888)))
    row = await db.fetchrow("SELECT photo_id, photo_blob_id FROM users WHERE id = 7")
    assert row["photo_id"] == 888 and row["photo_blob_id"] is None


async def test_name_history_only_on_change(db, dsn):
    await write(
        dsn,
        rec(1, sender=make_user(first_name="Ann")),
        rec(2, sender=make_user(first_name="Ann")),
        rec(3, sender=make_user(first_name="Anna")),
        rec(4, sender=make_user(first_name="Anna")),
    )
    rows = await db.fetch("SELECT first_name FROM user_name_history WHERE user_id = 7 ORDER BY id")
    assert [r["first_name"] for r in rows] == ["Ann", "Anna"]


async def test_basic_group_deletion_by_global_id(db, dsn):
    small = make_chat(id=99)  # marked id -99, type 'group'
    in_small = extract_message(
        make_message(id=500, peer=types.PeerChat(99)), small, make_user(), max_media_bytes=MAX
    )
    in_super = rec(500, text="same id, other chat")
    await write(
        dsn, in_small, in_super, DeletionRecord(chat_id=None, message_ids=(500,), observed_at=NOW)
    )
    assert (
        await db.fetchval("SELECT deleted_at FROM messages WHERE chat_id = -99 AND id = 500") == NOW
    )
    assert (
        await db.fetchval(
            "SELECT deleted_at FROM messages WHERE chat_id = $1 AND id = 500", GROUP_ID
        )
        is None
    )


async def test_media_skipped_marks_meta(db, dsn):
    await write(
        dsn,
        rec(2, text="", media=make_photo_media(photo_id=1000)),
        MediaSkipped(GROUP_ID, 2, 1000, "download_failed"),
    )
    meta = json.loads(await db.fetchval("SELECT media_meta FROM messages WHERE id = 2"))
    assert meta["skipped"] == "download_failed" and meta["media_id"] == 1000


async def test_migrations_run_by_store_on_first_connect(db, dsn):
    # `db` reset the schema; the store must create it on its own.
    await write(dsn, rec(1))
    assert await db.fetchval("SELECT max(version) FROM schema_migrations") == 1
    assert await db.fetchval("SELECT count(*) FROM messages") == 1
    assert await apply_migrations(db) == []
