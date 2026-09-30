import shutil

import pytest

from kodzu_thon.db import MIGRATIONS_DIR
from kodzu_thon.db.migrate import apply_migrations

pytestmark = pytest.mark.integration


async def test_migrations_apply_and_are_idempotent(db):
    assert await apply_migrations(db) == [1, 2]
    assert await apply_migrations(db) == []
    tables = {
        r["table_name"]
        for r in await db.fetch(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )
    }
    assert {
        "schema_migrations",
        "messages",
        "message_edits",
        "blobs",
        "chats",
        "users",
        "user_name_history",
        "web_sessions",
        "web_login_attempts",
        "web_totp_state",
        "forum_topics",
    } <= tables


async def test_read_only_role_privileges(db):
    await apply_migrations(db)
    priv = "SELECT has_table_privilege('kodzuweb_ro', $1, $2)"
    assert await db.fetchval(priv, "messages", "SELECT") is True
    assert await db.fetchval(priv, "blobs", "SELECT") is True
    assert await db.fetchval(priv, "messages", "INSERT") is False
    assert await db.fetchval(priv, "web_sessions", "INSERT") is True
    assert await db.fetchval(priv, "web_login_attempts", "DELETE") is True
    assert await db.fetchval(priv, "forum_topics", "SELECT") is True
    assert await db.fetchval(priv, "forum_topics", "INSERT") is False


async def test_forum_topics_migration_backfills_from_raw(db, tmp_path):
    shutil.copy(MIGRATIONS_DIR / "0001_init.sql", tmp_path)
    assert await apply_migrations(db, tmp_path) == [1]
    await db.execute(
        "INSERT INTO chats (id, type, title) VALUES (-1, 'supergroup', 'Forum'), "
        "(-2, 'supergroup', 'Plain')"
    )
    rows = [
        (-1, 1, "{}"),  # General
        (-1, 2, '{"reply_to": {"forum_topic": true, "reply_to_msg_id": 5}}'),
        (-1, 3, '{"reply_to": {"forum_topic": true, "reply_to_msg_id": 2, "reply_to_top_id": 5}}'),
        (-1, 4, '{"reply_to": {"reply_to_msg_id": 1}}'),  # reply inside General
        (-2, 1, '{"reply_to": {"reply_to_msg_id": 9}}'),
    ]
    await db.executemany(
        "INSERT INTO messages (chat_id, id, sent_at, raw) VALUES ($1, $2, now(), $3::jsonb)", rows
    )
    assert await apply_migrations(db) == [2]
    topics = {
        (r["chat_id"], r["id"]): r["topic_id"]
        for r in await db.fetch("SELECT chat_id, id, topic_id FROM messages")
    }
    assert topics == {(-1, 1): 1, (-1, 2): 5, (-1, 3): 5, (-1, 4): 1, (-2, 1): None}
    forums = await db.fetch("SELECT id, is_forum FROM chats ORDER BY id")
    assert [(r["id"], r["is_forum"]) for r in forums] == [(-2, False), (-1, True)]
