import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from kodzu_thon.services import message_store as ms
from kodzu_thon.services.message_extract import (
    BlobRecord,
    ChatPhotoTarget,
    ChatSnapshot,
    DeletionRecord,
    EditRecord,
    MediaSkipped,
    MessageRecord,
    MessageTarget,
    UserPhotoTarget,
    UserSnapshot,
)
from tests.factories import NOW
from tests.fakes import FakeConn, FakePool, fail_once

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


def make_record(msg_id=1, text="hi", media_meta=None, media_type=None, raw=None, chat=CHAT):
    return MessageRecord(
        chat=chat,
        sender_user=USER,
        sender_chat=None,
        id=msg_id,
        is_outgoing=False,
        sent_at=NOW,
        text=text,
        reply_to_msg_id=None,
        grouped_id=None,
        fwd_from_user_id=None,
        fwd_from_chat_id=None,
        fwd_from_name=None,
        fwd_date=None,
        media_type=media_type,
        media_size=None,
        media_meta=media_meta,
        raw=raw or {"_": "Message", "id": msg_id},
    )


def make_store(conn, **kw):
    async def create_pool(dsn, **_):
        return FakePool(conn)

    return ms.MessageStore("postgresql://x", create_pool=create_pool, **kw)


async def run_store(store, *records):
    await store.start()
    for r in records:
        store.enqueue(r)
    await store.stop()


@pytest.fixture(autouse=True)
def _no_migrations_no_sleep(mocker):
    mocker.patch("kodzu_thon.services.message_store.apply_migrations", AsyncMock(return_value=[]))
    mocker.patch(
        "kodzu_thon.services.message_store.ensure_database_exists", AsyncMock(return_value=False)
    )
    mocker.patch("kodzu_thon.services.message_store.asyncio.sleep", AsyncMock())


async def test_disabled_without_database_url(capsys):
    store = ms.MessageStore(None)
    store.enqueue(make_record())
    await store.start()
    await store.stop()
    assert store.connected is False and store.queued == 0
    assert "DATABASE_URL not set" in capsys.readouterr().err


async def test_message_is_written_with_parties_in_order():
    conn = FakeConn()
    rec = make_record(msg_id=10, text="hello")
    await run_store(make_store(conn), rec)

    sqls = conn.sqls()
    expected = [
        "BEGIN",
        ms.UPSERT_CHAT,
        ms.UPSERT_USER,
        ms.INSERT_NAME_HISTORY,
        ms.INSERT_MESSAGE,
        ms.UPDATE_CHAT_LAST_MESSAGE,
        "COMMIT",
    ]
    assert sqls == expected
    args = conn.args_for(ms.INSERT_MESSAGE)[0]
    assert args[0] == CHAT.id and args[1] == 10 and args[2] == USER.id and args[6] == "hello"
    assert json.loads(args[16]) == {"_": "Message", "id": 10}
    assert args[17] is None  # edited_at
    assert conn.args_for(ms.UPSERT_CHAT)[0] == (CHAT.id, "supergroup", "Grp", None, 555)
    assert conn.args_for(ms.UPSERT_USER)[0] == (7, "Ann", "Lee", "ann", False, False, 777)


async def test_sender_chat_is_upserted_too():
    conn = FakeConn()
    sender_chat = ChatSnapshot(
        id=-1000000000123, type="channel", title="C", username=None, photo_id=None
    )
    rec = MessageRecord(
        chat=CHAT,
        sender_user=None,
        sender_chat=sender_chat,
        id=1,
        is_outgoing=False,
        sent_at=NOW,
        text="x",
        reply_to_msg_id=None,
        grouped_id=None,
        fwd_from_user_id=None,
        fwd_from_chat_id=None,
        fwd_from_name=None,
        fwd_date=None,
        media_type=None,
        media_size=None,
        media_meta=None,
        raw={},
    )
    await run_store(make_store(conn), rec)
    assert [a[0] for a in conn.args_for(ms.UPSERT_CHAT)] == [CHAT.id, sender_chat.id]
    assert conn.args_for(ms.UPSERT_USER) == []


async def test_batch_shares_one_transaction():
    conn = FakeConn()
    await run_store(make_store(conn), make_record(1), make_record(2), make_record(3))
    sqls = conn.sqls()
    assert sqls.count("BEGIN") == 1 and sqls.count("COMMIT") == 1
    assert [a[1] for a in conn.args_for(ms.INSERT_MESSAGE)] == [1, 2, 3]


async def test_queue_full_drops_oldest(capsys):
    store = make_store(FakeConn(), queue_size=2)
    store.enqueue(make_record(1))
    store.enqueue(make_record(2))
    store.enqueue(make_record(3))
    assert store.queued == 2
    assert "queue full, dropped 1 event" in capsys.readouterr().err
    await run_store(store)  # drains 2 and 3


async def test_blob_buffer_is_bounded_by_bytes(capsys):
    store = make_store(FakeConn(), max_blob_bytes=10)
    blob = BlobRecord(MessageTarget(CHAT.id, 1, 1000), b"h" * 32, "image/jpeg", b"12345678")
    store.enqueue(blob)
    store.enqueue(blob)
    assert store.queued == 1
    assert "blob buffer full" in capsys.readouterr().err


async def test_connection_error_retries_batch_after_backoff():
    conn = FakeConn(fail_on=fail_once(ms.INSERT_MESSAGE, OSError("gone")))
    store = make_store(conn)
    await run_store(store, make_record(1))

    sqls = conn.sqls()
    assert sqls.count("ROLLBACK") == 1
    assert sqls.count(ms.INSERT_MESSAGE) == 1  # the failed attempt is not recorded
    assert sqls.count("COMMIT") == 1
    assert store.connected is True
    ms.asyncio.sleep.assert_awaited()


async def test_poison_event_is_dropped_others_apply(capsys):
    def fail(sql, args):
        if sql == ms.INSERT_MESSAGE and args[1] == 1:
            return ValueError("bad row")
        return None

    conn = FakeConn(fail_on=fail)
    await run_store(make_store(conn), make_record(1), make_record(2))

    assert [a[1] for a in conn.args_for(ms.INSERT_MESSAGE)] == [2]
    err = capsys.readouterr().err
    assert "batch failed (attempt 1)" in err and "batch failed (attempt 2)" in err
    assert "dropped poison event MessageRecord" in err


async def test_edit_without_text_or_media_change_updates_raw_only():
    conn = FakeConn(
        fetchrow_results=[{"text": "hi", "media_meta": None, "media_blob_id": None, "raw": "{}"}]
    )
    rec = make_record(1, text="hi", raw={"views": 5})
    await run_store(make_store(conn), EditRecord(message=rec, edited_at=NOW))

    sqls = conn.sqls()
    assert ms.UPDATE_MESSAGE_RAW in sqls and ms.INSERT_EDIT not in sqls
    assert conn.args_for(ms.UPDATE_MESSAGE_RAW)[0] == (CHAT.id, 1, json.dumps({"views": 5}))


async def test_edit_with_new_text_records_previous_version():
    conn = FakeConn(
        fetchrow_results=[
            {"text": "old", "media_meta": None, "media_blob_id": None, "raw": '{"v":1}'}
        ]
    )
    rec = make_record(1, text="new")
    await run_store(make_store(conn), EditRecord(message=rec, edited_at=NOW))

    assert conn.args_for(ms.INSERT_EDIT)[0] == (CHAT.id, 1, NOW, "old", None, '{"v":1}')
    upd = conn.args_for(ms.UPDATE_MESSAGE_EDITED)[0]
    assert upd[2] == "new" and upd[7] is False and upd[8] == NOW


async def test_edit_with_replaced_media_flags_media_changed():
    old_meta = json.dumps({"media_id": 1000})
    conn = FakeConn(
        fetchrow_results=[{"text": "hi", "media_meta": old_meta, "media_blob_id": 3, "raw": "{}"}]
    )
    rec = make_record(1, text="hi", media_type="photo", media_meta={"media_id": 2000})
    await run_store(make_store(conn), EditRecord(message=rec, edited_at=NOW))
    assert conn.args_for(ms.INSERT_EDIT)[0][4] == 3  # old_media_blob_id
    assert conn.args_for(ms.UPDATE_MESSAGE_EDITED)[0][7] is True


async def test_edit_of_unknown_message_inserts_it():
    conn = FakeConn(fetchrow_results=[None])
    await run_store(make_store(conn), EditRecord(message=make_record(1), edited_at=NOW))
    assert ms.INSERT_MESSAGE in conn.sqls() and ms.INSERT_EDIT not in conn.sqls()
    assert conn.args_for(ms.INSERT_MESSAGE)[0][17] == NOW


async def test_deletion_in_channel_and_global():
    conn = FakeConn()
    await run_store(
        make_store(conn),
        DeletionRecord(chat_id=CHAT.id, message_ids=(1, 2), observed_at=NOW),
        DeletionRecord(chat_id=None, message_ids=(500,), observed_at=NOW),
    )
    assert conn.args_for(ms.DELETE_IN_CHAT) == [(CHAT.id, [1, 2], NOW)]
    assert conn.args_for(ms.DELETE_GLOBAL) == [([500], NOW)]


async def test_blob_is_inserted_and_attached():
    conn = FakeConn(fetchval_results=[5, 6, 7])
    digest = b"d" * 32
    await run_store(
        make_store(conn),
        BlobRecord(MessageTarget(CHAT.id, 1, 1000), digest, "image/jpeg", b"abc"),
        BlobRecord(UserPhotoTarget(7, 777), digest, "image/jpeg", b"abc"),
        BlobRecord(ChatPhotoTarget(CHAT.id, 555), digest, "image/jpeg", b"abc"),
    )
    assert conn.args_for(ms.INSERT_BLOB)[0] == (digest, "image/jpeg", 3, b"abc")
    assert conn.args_for(ms.ATTACH_MESSAGE_BLOB) == [(CHAT.id, 1, 5, 1000)]
    assert conn.args_for(ms.ATTACH_USER_PHOTO) == [(7, 6, 777)]
    assert conn.args_for(ms.ATTACH_CHAT_PHOTO) == [(CHAT.id, 7, 555)]


async def test_media_skipped_marks_meta():
    conn = FakeConn()
    await run_store(make_store(conn), MediaSkipped(CHAT.id, 1, 1000, "download_failed"))
    assert conn.args_for(ms.MARK_MEDIA_SKIPPED) == [(CHAT.id, 1, 1000, "download_failed")]


async def test_read_helpers():
    conn = FakeConn(fetchval_results=[1, None, 1])
    store = make_store(conn)
    assert await store.message_media_is_current(CHAT.id, 1, 1000) is False  # not connected yet
    await store.start()
    await store.stop()
    assert await store.message_media_is_current(CHAT.id, 1, 1000) is False  # pool closed


async def test_connect_terminates_pool_when_migrations_fail(mocker):
    conn = FakeConn()
    created_pools = []

    async def create_pool(dsn, **_):
        pool = FakePool(conn)
        created_pools.append(pool)
        return pool

    mocker.patch(
        "kodzu_thon.services.message_store.apply_migrations",
        AsyncMock(side_effect=RuntimeError("bad migration")),
    )
    store = ms.MessageStore("postgresql://x", create_pool=create_pool)

    ok = await store._connect()

    assert ok is False
    assert store._pool is None
    assert len(created_pools) == 1
    assert created_pools[0].terminated is True
    assert created_pools[0].closed is True


async def test_connect_happens_eagerly_before_first_enqueue():
    conn = FakeConn()
    connected = asyncio.Event()
    connect_calls = []

    async def create_pool(dsn, **_):
        connect_calls.append(dsn)
        connected.set()
        return FakePool(conn)

    store = ms.MessageStore("postgresql://x", create_pool=create_pool)
    await store.start()
    # Wait for the writer's eager connect to actually happen, rather than assuming
    # a specific number of event-loop ticks (which would be timing-fragile) —
    # nothing is enqueued at any point in this test.
    await asyncio.wait_for(connected.wait(), timeout=1)

    assert connect_calls == ["postgresql://x"]
    assert store._pool is not None
    assert store.connected is True

    await store.stop()


async def test_ensure_database_exists_is_called_before_create_pool(mocker):
    order = []
    ensure_mock = AsyncMock(return_value=False)

    async def track_ensure(dsn):
        order.append(("ensure", dsn))
        return await ensure_mock(dsn)

    mocker.patch("kodzu_thon.services.message_store.ensure_database_exists", track_ensure)

    conn = FakeConn()

    async def create_pool(dsn, **_):
        order.append(("create_pool", dsn))
        return FakePool(conn)

    store = ms.MessageStore("postgresql://x", create_pool=create_pool)
    await run_store(store)

    assert order[0] == ("ensure", "postgresql://x")
    assert order[1] == ("create_pool", "postgresql://x")


async def test_ensure_database_exists_only_called_once_across_retries(mocker):
    ensure_mock = AsyncMock(return_value=False)
    mocker.patch("kodzu_thon.services.message_store.ensure_database_exists", ensure_mock)

    conn = FakeConn(
        fail_on=lambda sql, args: RuntimeError("boom") if sql == ms.INSERT_MESSAGE else None
    )
    calls = {"n": 0}

    async def flaky_create_pool(dsn, **_):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("pool unreachable")
        return FakePool(conn)

    store = ms.MessageStore("postgresql://x", create_pool=flaky_create_pool)
    await run_store(store, make_record(1))

    # _connect() was retried (first create_pool call failed), but ensure_database_exists
    # must only run once — the second attempt already knows the database exists.
    assert ensure_mock.await_count == 1


async def test_database_created_message_is_logged_when_missing(mocker, capsys):
    mocker.patch(
        "kodzu_thon.services.message_store.ensure_database_exists",
        AsyncMock(return_value=True),
    )
    conn = FakeConn()
    await run_store(make_store(conn))

    assert "database did not exist, created it" in capsys.readouterr().err
