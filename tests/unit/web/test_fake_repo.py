from datetime import UTC, datetime, timedelta

from kodzu_thon.db import SCHEMA_VERSION
from kodzu_thon.web.repository import MessageFilters
from tests.unit.web.fake_repo import FakeRepository, make_message_row

NOW = datetime(2026, 9, 13, 12, 0, tzinfo=UTC)


def seeded():
    repo = FakeRepository()
    repo.add_chat(id=-100, title="Grp", type="supergroup")
    repo.add_user(id=7, first_name="Ann", last_name="Lee", username="ann")
    for i in range(1, 6):
        repo.add_message(
            chat_id=-100,
            id=i,
            sender_user_id=7,
            text=f"msg {i}",
            sent_at=NOW + timedelta(minutes=i),
            deleted_at=NOW if i == 3 else None,
            edit_count=1 if i == 4 else 0,
            grouped_id=99 if i in (1, 2) else None,
        )
    return repo


def test_make_message_row_has_every_view_key():
    row = make_message_row()
    for key in (
        "chat_id",
        "id",
        "sent_at",
        "text",
        "media_meta",
        "media_blob_id",
        "deleted_at",
        "edit_count",
        "chat_title",
        "sender_first_name",
        "reply_text",
        "fwd_chat_title",
    ):
        assert key in row


async def test_chat_messages_newest_first_with_limit_plus_one_and_keyset():
    repo = seeded()
    rows = await repo.chat_messages(-100, limit=2)
    assert [r["id"] for r in rows] == [5, 4, 3]  # limit + 1
    rows = await repo.chat_messages(-100, before_id=4, limit=10)
    assert [r["id"] for r in rows] == [3, 2, 1]
    assert repo.calls[-1] == (
        "chat_messages",
        {"chat_id": -100, "before_id": 4, "limit": 10, "filters": MessageFilters()},
    )


async def test_filters_apply_in_fake():
    repo = seeded()
    assert [
        r["id"] for r in await repo.chat_messages(-100, filters=MessageFilters(deleted_only=True))
    ] == [3]
    assert [
        r["id"] for r in await repo.chat_messages(-100, filters=MessageFilters(edited_only=True))
    ] == [4]
    assert [r["id"] for r in await repo.chat_messages(-100, filters=MessageFilters(q="MSG 2"))] == [
        2
    ]
    assert [
        r["id"] for r in await repo.chat_messages(-100, filters=MessageFilters(sender_id=8))
    ] == []
    since = NOW + timedelta(minutes=4)
    assert [
        r["id"] for r in await repo.chat_messages(-100, filters=MessageFilters(since=since))
    ] == [5, 4]
    assert [
        r["id"] for r in await repo.chat_messages(-100, filters=MessageFilters(until=since))
    ] == [3, 2, 1]


async def test_chat_id_filter_narrows_to_one_chat():
    repo = seeded()
    repo.add_chat(id=-200, title="Other", type="group")
    repo.add_message(
        chat_id=-200, id=6, sender_user_id=7, text="msg 6", sent_at=NOW + timedelta(minutes=6)
    )
    found = await repo.search_messages(filters=MessageFilters(q="msg", chat_id=-100))
    assert [r["id"] for r in found] == [5, 4, 3, 2, 1]
    found = await repo.search_messages(filters=MessageFilters(q="msg", chat_id=-200))
    assert [r["id"] for r in found] == [6]


async def test_deleted_and_search_feeds():
    repo = seeded()
    deleted = await repo.deleted_messages()
    assert [r["id"] for r in deleted] == [3]
    found = await repo.search_messages(filters=MessageFilters(q="msg"))
    assert [r["id"] for r in found] == [5, 4, 3, 2, 1]
    page = await repo.search_messages(
        before=(NOW + timedelta(minutes=4), 4), limit=10, filters=MessageFilters(q="msg")
    )
    assert [r["id"] for r in page] == [3, 2, 1]


async def test_users_and_edits_and_blobs():
    repo = seeded()
    repo.add_edit(-100, 4, old_text="before", edited_at=NOW)
    repo.add_blob(id=9, mime_type="image/jpeg", data=b"jpg")
    repo.add_name_history(7, first_name="Anna", seen_at=NOW)
    assert (await repo.get_user(7))["username"] == "ann"
    assert await repo.get_user(404) is None
    assert (await repo.user_name_history(7))[0]["first_name"] == "Anna"
    assert await repo.user_chats(7) == [
        {"id": -100, "title": "Grp", "type": "supergroup", "message_count": 5}
    ]
    assert [r["id"] for r in await repo.user_messages(7, limit=2)] == [5, 4, 3]
    assert (await repo.message_edits(-100, 4))[0]["old_text"] == "before"
    assert (await repo.get_message(-100, 4))["raw"] == {}
    assert (await repo.get_blob(9))["data"] == b"jpg"
    assert await repo.get_blob(1) is None


async def test_session_and_attempt_state():
    repo = FakeRepository()
    await repo.create_session(
        b"h", "anon", None, "csrf", NOW, NOW + timedelta(hours=1), "127.0.0.1", "ua"
    )
    session = await repo.get_session(b"h")
    assert session["state"] == "anon" and session["last_seen_at"] == NOW
    await repo.touch_session(b"h", NOW + timedelta(minutes=5), NOW + timedelta(hours=13))
    await repo.set_session_state(b"h", "authed")
    session = await repo.get_session(b"h")
    assert session["state"] == "authed" and session["last_seen_at"] == NOW + timedelta(minutes=5)
    assert await repo.delete_expired_sessions(NOW + timedelta(days=8)) == 1
    assert await repo.get_session(b"h") is None
    await repo.record_login_attempt("1.1.1.1", "admin", False)
    await repo.record_login_attempt("1.1.1.1", "admin", True)
    assert await repo.failed_attempts_by_ip("1.1.1.1", NOW - timedelta(days=1)) == 1
    assert await repo.failed_attempts_by_username("admin", NOW - timedelta(days=1)) == 1
    assert await repo.get_totp_counter() is None
    await repo.set_totp_counter(5)
    assert await repo.get_totp_counter() == 5


async def test_meta_defaults():
    repo = FakeRepository()
    assert await repo.ping() is True
    assert await repo.schema_version() == SCHEMA_VERSION
    repo.ping_ok = False
    assert await repo.ping() is False
