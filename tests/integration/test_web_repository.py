import hashlib
from datetime import timedelta

import asyncpg
import pytest
from telethon.tl import types

from kodzu_thon.db import SCHEMA_VERSION
from kodzu_thon.db.migrate import apply_migrations
from kodzu_thon.services.message_extract import (
    BlobRecord,
    DeletionRecord,
    EditRecord,
    MessageTarget,
    extract_message,
)
from kodzu_thon.services.message_store import MessageStore
from kodzu_thon.web.app import STATEMENT_TIMEOUT_MS, check_schema
from kodzu_thon.web.repository import MessageFilters, Repository
from tests.factories import NOW, make_message, make_photo_media, make_supergroup, make_user

pytestmark = pytest.mark.integration
MAX = 5 * 1024 * 1024
GROUP = make_supergroup()
GROUP_ID = -1000000000124


def rec(msg_id, text="hi", sender=None, **kw):
    msg = make_message(id=msg_id, text=text, peer=types.PeerChannel(124), **kw)
    return extract_message(msg, GROUP, sender or make_user(), max_media_bytes=MAX)


async def write(dsn, *records):
    store = MessageStore(dsn, batch_size=2)
    await store.start()
    for r in records:
        store.enqueue(r)
    await store.stop()
    assert store.queued == 0


@pytest.fixture
async def repo(db, dsn):
    await apply_migrations(db)
    pool = await asyncpg.create_pool(
        dsn,
        min_size=1,
        max_size=2,
        server_settings={"statement_timeout": str(STATEMENT_TIMEOUT_MS)},
    )
    repository = Repository(pool)
    try:
        yield repository
    finally:
        await repository.close()


async def seed(dsn):
    data = b"jpegbytes"
    await write(
        dsn,
        rec(1, text="50% off"),
        rec(2, text="500 off"),
        rec(3, text="photo", media=make_photo_media(photo_id=1000)),
        rec(4, text="to be deleted"),
        rec(5, text="original", sender=make_user(id=8, first_name="Bob", username="bob")),
        EditRecord(
            message=rec(
                5, text="edited once", sender=make_user(id=8, first_name="Bob", username="bob")
            ),
            edited_at=NOW,
        ),
        DeletionRecord(chat_id=GROUP_ID, message_ids=(4,), observed_at=NOW + timedelta(minutes=1)),
        BlobRecord(
            MessageTarget(GROUP_ID, 3, 1000), hashlib.sha256(data).digest(), "image/jpeg", data
        ),
    )


async def test_meta_and_timeout(repo):
    assert await repo.ping() is True
    assert await repo.schema_version() == SCHEMA_VERSION
    assert await check_schema(repo) == SCHEMA_VERSION
    assert await repo._fetchval("SHOW statement_timeout") == "10s"


async def test_chats_and_timeline(repo, dsn):
    await seed(dsn)
    chats = await repo.list_chats()
    assert [c["id"] for c in chats] == [GROUP_ID]
    assert (await repo.get_chat(GROUP_ID))["type"] == "supergroup"
    assert await repo.get_chat(1) is None

    rows = await repo.chat_messages(GROUP_ID, limit=2)
    assert [r["id"] for r in rows] == [5, 4, 3]  # limit + 1, newest first
    assert rows[0]["sender_first_name"] == "Bob" and rows[0]["edit_count"] == 1
    assert rows[1]["deleted_at"] is not None
    assert [r["id"] for r in await repo.chat_messages(GROUP_ID, before_id=3)] == [2, 1]

    photo = (await repo.chat_messages(GROUP_ID, filters=MessageFilters(q="photo")))[0]
    assert photo["media_meta"]["media_id"] == 1000 and photo["media_blob_id"] is not None

    assert [
        r["id"] for r in await repo.chat_messages(GROUP_ID, filters=MessageFilters(q="50%"))
    ] == [1]
    assert [
        r["id"]
        for r in await repo.chat_messages(GROUP_ID, filters=MessageFilters(deleted_only=True))
    ] == [4]
    assert [
        r["id"]
        for r in await repo.chat_messages(GROUP_ID, filters=MessageFilters(edited_only=True))
    ] == [5]
    assert [
        r["id"] for r in await repo.chat_messages(GROUP_ID, filters=MessageFilters(sender_id=8))
    ] == [5]
    assert (
        await repo.chat_messages(GROUP_ID, filters=MessageFilters(since=NOW + timedelta(days=1)))
        == []
    )
    assert (
        len(
            await repo.chat_messages(
                GROUP_ID, filters=MessageFilters(until=NOW + timedelta(days=1))
            )
        )
        == 5
    )


async def test_permalink_edits_and_feeds(repo, dsn):
    await seed(dsn)
    msg = await repo.get_message(GROUP_ID, 5)
    assert msg["text"] == "edited once" and msg["raw"]["_"] == "Message"
    assert await repo.get_message(GROUP_ID, 999) is None
    edits = await repo.message_edits(GROUP_ID, 5)
    assert len(edits) == 1 and edits[0]["old_text"] == "original" and edits[0]["old_raw"]["id"] == 5

    deleted = await repo.deleted_messages()
    assert [r["id"] for r in deleted] == [4]
    assert await repo.deleted_messages(before=(deleted[0]["deleted_at"], 4)) == []

    found = await repo.search_messages(filters=MessageFilters(q="off"))
    assert [r["id"] for r in found] == [2, 1]
    page = await repo.search_messages(
        before=(found[0]["sent_at"], 2), filters=MessageFilters(q="off")
    )
    assert [r["id"] for r in page] == [1]


async def test_users_and_blobs(repo, dsn):
    await seed(dsn)
    user = await repo.get_user(8)
    assert user["username"] == "bob" and user["is_bot"] is False
    assert await repo.get_user(404) is None
    history = await repo.user_name_history(8)
    assert history and history[0]["first_name"] == "Bob"
    assert await repo.user_chats(8) == [
        {"id": GROUP_ID, "title": "Grp", "type": "supergroup", "message_count": 1}
    ]
    assert [r["id"] for r in await repo.user_messages(7)] == [4, 3, 2, 1]
    blob_id = (await repo.get_message(GROUP_ID, 3))["media_blob_id"]
    blob = await repo.get_blob(blob_id)
    assert blob["mime_type"] == "image/jpeg" and blob["data"] == b"jpegbytes" and blob["size"] == 9


async def test_session_and_attempt_tables(repo):
    now = NOW
    await repo.create_session(
        b"h" * 32, "anon", None, "csrf", now, now + timedelta(hours=1), "10.0.0.1", "ua"
    )
    session = await repo.get_session(b"h" * 32)
    assert (
        session["state"] == "anon"
        and session["last_seen_at"] == now
        and session["csrf_token"] == "csrf"
    )
    await repo.touch_session(b"h" * 32, now + timedelta(minutes=5), now + timedelta(hours=13))
    await repo.set_session_state(b"h" * 32, "authed")
    session = await repo.get_session(b"h" * 32)
    assert session["state"] == "authed" and session["expires_at"] == now + timedelta(hours=13)
    assert await repo.delete_expired_sessions(now + timedelta(days=1)) == 1
    assert await repo.get_session(b"h" * 32) is None

    await repo.record_login_attempt("10.0.0.1", "admin", False)
    await repo.record_login_attempt("10.0.0.1", "admin", True)
    await repo.record_login_attempt("10.0.0.2", "root", False)
    since = now - timedelta(days=1)
    assert await repo.failed_attempts_by_ip("10.0.0.1", since) == 1
    assert await repo.failed_attempts_by_username("admin", since) == 1
    assert await repo.failed_attempts_by_ip("10.0.0.9", since) == 0

    assert await repo.get_totp_counter() is None
    await repo.set_totp_counter(7)
    await repo.set_totp_counter(9)
    assert await repo.get_totp_counter() == 9


async def test_statement_timeout_setting_is_honoured(dsn):
    # Same mechanism app.py uses (server_settings on the pool), with a 100 ms limit so the
    # test proves the server actually cancels long statements without waiting 10 s.
    pool = await asyncpg.create_pool(
        dsn, min_size=1, max_size=1, server_settings={"statement_timeout": "100"}
    )
    try:
        repo = Repository(pool)
        with pytest.raises(asyncpg.QueryCanceledError):
            await repo._fetchval("SELECT pg_sleep(1)")
        assert await repo.ping() is True  # the connection survives a cancelled statement
    finally:
        await pool.close()
