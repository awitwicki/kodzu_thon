import pytest

from kodzu_thon.db.migrate import apply_migrations

pytestmark = pytest.mark.integration


async def test_migrations_apply_and_are_idempotent(db):
    assert await apply_migrations(db) == [1]
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
    } <= tables


async def test_read_only_role_privileges(db):
    await apply_migrations(db)
    priv = "SELECT has_table_privilege('kodzuweb_ro', $1, $2)"
    assert await db.fetchval(priv, "messages", "SELECT") is True
    assert await db.fetchval(priv, "blobs", "SELECT") is True
    assert await db.fetchval(priv, "messages", "INSERT") is False
    assert await db.fetchval(priv, "web_sessions", "INSERT") is True
    assert await db.fetchval(priv, "web_login_attempts", "DELETE") is True
