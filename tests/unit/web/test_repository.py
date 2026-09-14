from datetime import UTC, datetime

import pytest

from kodzu_thon.web import repository as repo_mod
from kodzu_thon.web.repository import MessageFilters, Repository
from tests.fakes import FakeConn, FakePool

NOW = datetime(2026, 9, 13, 12, 0, tzinfo=UTC)


def make_repo(conn: FakeConn) -> Repository:
    return Repository(FakePool(conn))


async def test_chat_messages_default_query_fetches_limit_plus_one():
    conn = FakeConn(fetch_results=[[]])
    await make_repo(conn).chat_messages(-100, limit=100)
    sql, args = conn.calls[-1]
    assert sql.startswith(repo_mod.MESSAGE_SELECT)
    assert "WHERE m.chat_id = $1" in sql and "ORDER BY m.id DESC LIMIT $2" in sql
    assert args == (-100, 101)


async def test_chat_messages_applies_keyset_and_every_filter():
    conn = FakeConn(fetch_results=[[]])
    filters = MessageFilters(
        q="50%",
        chat_id=-200,
        sender_id=7,
        deleted_only=True,
        edited_only=True,
        since=NOW,
        until=NOW,
    )
    await make_repo(conn).chat_messages(-100, before_id=500, limit=10, filters=filters)
    sql, args = conn.calls[-1]
    assert "m.id < $2" in sql
    assert "m.chat_id = $3" in sql
    assert "m.deleted_at IS NOT NULL" in sql and "m.edit_count > 0" in sql
    assert "m.sender_user_id = $4" in sql
    assert "m.text ILIKE '%' || $5 || '%' ESCAPE '\\'" in sql
    assert "m.sent_at >= $6" in sql and "m.sent_at < $7" in sql
    assert args == (-100, 500, -200, 7, "50\\%", NOW, NOW, 11)


async def test_deleted_messages_filters_by_chat_id():
    conn = FakeConn(fetch_results=[[]])
    await make_repo(conn).deleted_messages(filters=MessageFilters(chat_id=-200))
    sql, args = conn.calls[-1]
    assert "m.chat_id = $1" in sql
    assert args == (-200, 101)


async def test_message_rows_parse_jsonb_columns():
    row = {"id": 1, "chat_id": -1, "media_meta": '{"media_id": 5}', "grouped_id": None}
    conn = FakeConn(fetch_results=[[row]])
    rows = await make_repo(conn).chat_messages(-1)
    assert rows[0]["media_meta"] == {"media_id": 5}


async def test_get_message_includes_raw_and_parses_it():
    conn = FakeConn(
        fetchrow_results=[{"id": 1, "chat_id": -1, "media_meta": None, "raw": '{"_": "Message"}'}]
    )
    msg = await make_repo(conn).get_message(-1, 1)
    sql, args = conn.calls[-1]
    assert "m.raw" in sql and args == (-1, 1)
    assert msg["raw"] == {"_": "Message"}


async def test_get_message_missing_returns_none():
    conn = FakeConn(fetchrow_results=[None])
    assert await make_repo(conn).get_message(-1, 1) is None


async def test_deleted_messages_keyset_on_deleted_at():
    conn = FakeConn(fetch_results=[[]])
    await make_repo(conn).deleted_messages(before=(NOW, 9), limit=5)
    sql, args = conn.calls[-1]
    assert "m.deleted_at IS NOT NULL" in sql
    assert "(m.deleted_at, m.id) < ($1, $2)" in sql
    assert "ORDER BY m.deleted_at DESC, m.id DESC LIMIT $3" in sql
    assert args == (NOW, 9, 6)


def test_feed_query_falls_back_to_true_when_no_clauses_apply():
    """No caller hits this today (search_messages requires filters.q, and the other feed
    callers always pass a non-empty base_clauses), but _feed_query must not degrade to the
    syntax error `WHERE  ORDER BY ...` if a future caller ever does."""
    sql, params = repo_mod._feed_query(
        [],
        [],
        keyset_columns=("m.sent_at", "m.id"),
        before=None,
        limit=10,
        filters=MessageFilters(),
    )
    assert "WHERE true ORDER" in sql
    assert "WHERE  ORDER" not in sql
    assert params == [11]


async def test_search_messages_requires_q_and_keysets_on_sent_at():
    conn = FakeConn(fetch_results=[[]])
    repo = make_repo(conn)
    with pytest.raises(ValueError, match=r"filters\.q"):
        await repo.search_messages(filters=MessageFilters())
    await repo.search_messages(before=(NOW, 3), limit=2, filters=MessageFilters(q="hi"))
    sql, args = conn.calls[-1]
    assert "(m.sent_at, m.id) < ($1, $2)" in sql
    assert "m.text ILIKE '%' || $3 || '%' ESCAPE '\\'" in sql
    assert "ORDER BY m.sent_at DESC, m.id DESC LIMIT $4" in sql
    assert args == (NOW, 3, "hi", 3)


async def test_user_messages_and_aggregates():
    conn = FakeConn(fetch_results=[[], [], []], fetchrow_results=[{"id": 7}])
    repo = make_repo(conn)
    assert await repo.get_user(7) == {"id": 7}
    await repo.user_name_history(7)
    await repo.user_chats(7)
    await repo.user_messages(7, before=(NOW, 1), limit=1)
    sqls = conn.sqls()
    assert "FROM users WHERE id = $1" in sqls[0]
    assert "FROM user_name_history WHERE user_id = $1 ORDER BY seen_at DESC, id DESC" in sqls[1]
    assert "GROUP BY c.id, c.title, c.type ORDER BY message_count DESC" in sqls[2]
    assert "m.sender_user_id = $1" in sqls[3] and "(m.sent_at, m.id) < ($2, $3)" in sqls[3]
    assert conn.calls[-1][1] == (7, NOW, 1, 2)


async def test_chats_and_blob_queries():
    conn = FakeConn(
        fetch_results=[[{"id": -1}]], fetchrow_results=[{"id": -1}, {"id": 3, "data": b"x"}]
    )
    repo = make_repo(conn)
    assert await repo.list_chats() == [{"id": -1}]
    assert "ORDER BY last_message_at DESC NULLS LAST" in conn.sqls()[0]
    assert await repo.get_chat(-1) == {"id": -1}
    assert await repo.get_blob(3) == {"id": 3, "data": b"x"}
    assert conn.calls[-1][1] == (3,)


async def test_meta_queries():
    conn = FakeConn(fetchval_results=[1, 1])
    repo = make_repo(conn)
    assert await repo.ping() is True
    assert await repo.schema_version() == 1
    assert conn.sqls() == ["SELECT 1", "SELECT max(version) FROM schema_migrations"]


async def test_ping_returns_false_on_error():
    conn = FakeConn(fail_on=lambda sql, args: OSError("down") if sql == "SELECT 1" else None)
    assert await make_repo(conn).ping() is False


async def test_session_statements():
    conn = FakeConn(fetchrow_results=[{"token_hash": b"h"}])
    repo = make_repo(conn)
    assert await repo.get_session(b"h") == {"token_hash": b"h"}
    await repo.create_session(b"h", "anon", None, "csrf", NOW, NOW, "127.0.0.1", "ua")
    await repo.touch_session(b"h", NOW, NOW)
    await repo.set_session_state(b"h", "authed")
    await repo.delete_session(b"h")
    sqls = conn.sqls()
    assert "FROM web_sessions WHERE token_hash = $1" in sqls[0]
    assert sqls[1].startswith("INSERT INTO web_sessions")
    assert conn.calls[1][1] == (b"h", "anon", None, "csrf", NOW, NOW, NOW, "127.0.0.1", "ua")
    assert "SET last_seen_at = $2, expires_at = $3" in sqls[2]
    assert "SET state = $2" in sqls[3]
    assert sqls[4] == "DELETE FROM web_sessions WHERE token_hash = $1"


async def test_delete_expired_sessions_parses_count():
    conn = FakeConn()
    conn.execute = _execute_returning(conn, "DELETE 3")
    assert await make_repo(conn).delete_expired_sessions(NOW) == 3
    assert conn.calls[-1] == ("DELETE FROM web_sessions WHERE expires_at <= $1", (NOW,))


def _execute_returning(conn, status):
    async def execute(sql, *args):
        conn.calls.append((sql, args))
        return status

    return execute


async def test_login_attempt_statements():
    conn = FakeConn(fetchval_results=[2, 5])
    repo = make_repo(conn)
    await repo.record_login_attempt("10.0.0.1", "admin", False)
    assert await repo.failed_attempts_by_ip("10.0.0.1", NOW) == 2
    assert await repo.failed_attempts_by_username("admin", NOW) == 5
    sqls = conn.sqls()
    assert sqls[0].startswith("INSERT INTO web_login_attempts")
    assert "WHERE ip = $1 AND success = false AND attempted_at >= $2" in sqls[1]
    assert "WHERE username = $1 AND success = false AND attempted_at >= $2" in sqls[2]


async def test_totp_counter_statements():
    conn = FakeConn(fetchval_results=[None])
    repo = make_repo(conn)
    assert await repo.get_totp_counter() is None
    await repo.set_totp_counter(42)
    assert "ON CONFLICT (id) DO UPDATE SET last_counter = EXCLUDED.last_counter" in conn.sqls()[1]
    assert conn.calls[-1][1] == (42,)


async def test_close_closes_pool():
    conn = FakeConn()
    pool = FakePool(conn)
    await Repository(pool).close()
    assert pool.closed is True
