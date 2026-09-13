import re

import asyncpg
import pytest

from kodzu_thon.db import MIGRATIONS_DIR, SCHEMA_VERSION
from kodzu_thon.db.migrate import apply_migrations, ensure_database_exists, list_migrations
from tests.fakes import FakeConn


def _write(tmp_path, name, sql):
    (tmp_path / name).write_text(sql, encoding="utf-8")


def test_list_migrations_orders_by_version(tmp_path):
    _write(tmp_path, "0002_two.sql", "SELECT 2")
    _write(tmp_path, "0001_one.sql", "SELECT 1")
    assert [(v, p.name) for v, p in list_migrations(tmp_path)] == [
        (1, "0001_one.sql"),
        (2, "0002_two.sql"),
    ]


def test_list_migrations_rejects_bad_filename(tmp_path):
    _write(tmp_path, "init.sql", "SELECT 1")
    with pytest.raises(ValueError, match=re.escape("init.sql")):
        list_migrations(tmp_path)


async def test_apply_migrations_runs_only_unapplied_in_order(tmp_path):
    _write(tmp_path, "0001_one.sql", "CREATE TABLE a (id int)")
    _write(tmp_path, "0002_two.sql", "CREATE TABLE b (id int)")
    conn = FakeConn(fetch_results=[[{"version": 1}]])

    applied = await apply_migrations(conn, tmp_path)

    assert applied == [2]
    sqls = conn.sqls()
    assert "CREATE TABLE a (id int)" not in sqls
    i_lock = sqls.index("SELECT pg_advisory_lock($1)")
    i_sql = sqls.index("CREATE TABLE b (id int)")
    i_ins = sqls.index("INSERT INTO schema_migrations (version) VALUES ($1)")
    i_unlock = sqls.index("SELECT pg_advisory_unlock($1)")
    assert i_lock < i_sql < i_ins < i_unlock
    assert conn.args_for("INSERT INTO schema_migrations (version) VALUES ($1)") == [(2,)]
    # the migration and its bookkeeping row share one transaction
    assert sqls[i_sql - 1] == "BEGIN" and sqls[i_ins + 1] == "COMMIT"


async def test_apply_migrations_noop_when_everything_applied(tmp_path):
    _write(tmp_path, "0001_one.sql", "CREATE TABLE a (id int)")
    conn = FakeConn(fetch_results=[[{"version": 1}]])
    assert await apply_migrations(conn, tmp_path) == []
    assert "CREATE TABLE a (id int)" not in conn.sqls()


async def test_apply_migrations_unlocks_on_failure(tmp_path):
    _write(tmp_path, "0001_one.sql", "BROKEN SQL")

    def fail(sql, args):
        return RuntimeError("syntax") if sql == "BROKEN SQL" else None

    conn = FakeConn(fail_on=fail)
    with pytest.raises(RuntimeError):
        await apply_migrations(conn, tmp_path)
    assert conn.sqls()[-1] == "SELECT pg_advisory_unlock($1)"


def test_bundled_migrations_match_schema_version():
    versions = [v for v, _ in list_migrations(MIGRATIONS_DIR)]
    assert versions == list(range(1, SCHEMA_VERSION + 1))
    sql = (MIGRATIONS_DIR / "0001_init.sql").read_text(encoding="utf-8")
    for table in (
        "blobs",
        "chats",
        "users",
        "user_name_history",
        "messages",
        "message_edits",
        "web_sessions",
        "web_login_attempts",
        "web_totp_state",
    ):
        assert f"CREATE TABLE {table} (" in sql
    assert "CREATE TABLE schema_migrations" not in sql  # owned by the runner
    assert "TO kodzuweb_ro" in sql


def _fake_connect(conn):
    calls = []

    async def connect(dsn):
        calls.append(dsn)
        return conn

    connect.calls = calls
    return connect


async def test_ensure_database_exists_noop_when_already_there():
    conn = FakeConn(fetchval_results=[1])
    connect = _fake_connect(conn)

    created = await ensure_database_exists(
        "postgresql://u:p@host:5432/kodzu_messages", connect=connect
    )

    assert created is False
    assert connect.calls == ["postgresql://u:p@host:5432/postgres"]
    assert conn.args_for("SELECT 1 FROM pg_database WHERE datname = $1") == [("kodzu_messages",)]
    assert not any("CREATE DATABASE" in sql for sql in conn.sqls())
    assert conn.closed is True


async def test_ensure_database_exists_creates_when_missing():
    conn = FakeConn(fetchval_results=[None])
    connect = _fake_connect(conn)

    created = await ensure_database_exists(
        "postgresql://u:p@host:5432/kodzu_messages", connect=connect
    )

    assert created is True
    assert conn.sqls()[-1] == 'CREATE DATABASE "kodzu_messages"'
    assert conn.closed is True


async def test_ensure_database_exists_quotes_identifier():
    conn = FakeConn(fetchval_results=[None])
    connect = _fake_connect(conn)

    await ensure_database_exists('postgresql://u:p@host:5432/weird"db', connect=connect)

    assert conn.sqls()[-1] == 'CREATE DATABASE "weird""db"'


async def test_ensure_database_exists_treats_race_as_already_there():
    def fail(sql, args):
        if "CREATE DATABASE" in sql:
            return asyncpg.exceptions.DuplicateDatabaseError("already exists")
        return None

    conn = FakeConn(fetchval_results=[None], fail_on=fail)
    connect = _fake_connect(conn)

    created = await ensure_database_exists(
        "postgresql://u:p@host:5432/kodzu_messages", connect=connect
    )

    assert created is False
    assert conn.closed is True


async def test_ensure_database_exists_preserves_query_string_and_credentials():
    conn = FakeConn(fetchval_results=[1])
    connect = _fake_connect(conn)

    await ensure_database_exists(
        "postgresql://u:p@host:5432/kodzu_messages?sslmode=require", connect=connect
    )

    assert connect.calls == ["postgresql://u:p@host:5432/postgres?sslmode=require"]


async def test_ensure_database_exists_requires_database_name():
    with pytest.raises(ValueError, match="database name"):
        await ensure_database_exists("postgresql://u:p@host:5432/", connect=_fake_connect(None))


async def test_ensure_database_exists_admin_database_is_configurable():
    conn = FakeConn(fetchval_results=[1])
    connect = _fake_connect(conn)

    await ensure_database_exists(
        "postgresql://u:p@host:5432/kodzu_messages", connect=connect, admin_database="template1"
    )

    assert connect.calls == ["postgresql://u:p@host:5432/template1"]
