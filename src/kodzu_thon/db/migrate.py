import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import asyncpg

from kodzu_thon.db import MIGRATIONS_DIR

_LOCK_KEY = 7_420_001  # arbitrary constant shared by every process that migrates
_NAME_RE = re.compile(r"^(\d{4})_[a-z0-9_]+\.sql$")
_SELECT_DATABASE_EXISTS = "SELECT 1 FROM pg_database WHERE datname = $1"

CREATE_SCHEMA_MIGRATIONS = (
    "CREATE TABLE IF NOT EXISTS schema_migrations ("
    "version INTEGER PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
)
SELECT_APPLIED = "SELECT version FROM schema_migrations"
INSERT_APPLIED = "INSERT INTO schema_migrations (version) VALUES ($1)"


def list_migrations(migrations_dir: Path = MIGRATIONS_DIR) -> list[tuple[int, Path]]:
    found: list[tuple[int, Path]] = []
    for path in sorted(migrations_dir.glob("*.sql")):
        m = _NAME_RE.match(path.name)
        if m is None:
            raise ValueError(f"bad migration filename: {path.name}")
        found.append((int(m.group(1)), path))
    return found


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _admin_dsn(dsn: str, admin_database: str) -> tuple[str, str]:
    """Split `dsn` into (target database name, a DSN for the same server but pointed at
    `admin_database` instead) so a database that doesn't exist yet can be created."""
    parts = urlsplit(dsn)
    target_db = parts.path.lstrip("/")
    if not target_db:
        raise ValueError("connection string must include a database name")
    admin_dsn = urlunsplit(parts._replace(path="/" + admin_database))
    return target_db, admin_dsn


async def ensure_database_exists(
    dsn: str, *, connect=asyncpg.connect, admin_database: str = "postgres"
) -> bool:
    """Create the database named in `dsn` if it doesn't exist yet, by connecting instead
    to `admin_database` (present on every standard PostgreSQL server) with the same host,
    port, and credentials. Returns True if the database was just created, False if it was
    already there. Only requires CREATEDB privilege on the connecting role when the
    database is actually missing — a pre-existing database needs no extra privilege.
    Safe to call concurrently from multiple instances: a `CREATE DATABASE` race is treated
    the same as "already exists"."""
    target_db, admin_dsn = _admin_dsn(dsn, admin_database)
    conn = await connect(admin_dsn)
    try:
        if await conn.fetchval(_SELECT_DATABASE_EXISTS, target_db):
            return False
        try:
            await conn.execute(f"CREATE DATABASE {_quote_ident(target_db)}")
        except asyncpg.exceptions.DuplicateDatabaseError:
            return False
        return True
    finally:
        await conn.close()


async def apply_migrations(conn, migrations_dir: Path = MIGRATIONS_DIR) -> list[int]:
    """Apply every migration newer than what `schema_migrations` records.
    Returns the versions applied by this call. Safe to run concurrently."""
    await conn.execute("SELECT pg_advisory_lock($1)", _LOCK_KEY)
    try:
        await conn.execute(CREATE_SCHEMA_MIGRATIONS)
        applied = {row["version"] for row in await conn.fetch(SELECT_APPLIED)}
        done: list[int] = []
        for version, path in list_migrations(migrations_dir):
            if version in applied:
                continue
            async with conn.transaction():
                await conn.execute(path.read_text(encoding="utf-8"))
                await conn.execute(INSERT_APPLIED, version)
            done.append(version)
        return done
    finally:
        await conn.execute("SELECT pg_advisory_unlock($1)", _LOCK_KEY)
