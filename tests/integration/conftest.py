import os

import asyncpg
import pytest

DSN = os.environ.get("TEST_DATABASE_URL")

# The integration suite DROPS the public schema. Refuse anything that does not look disposable.
if DSN and "test" not in DSN.rsplit("/", 1)[-1].split("?")[0]:
    raise RuntimeError("TEST_DATABASE_URL must point to a database whose name contains 'test'")

RESET_SQL = """
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'kodzuweb_ro') THEN
    CREATE ROLE kodzuweb_ro;
  END IF;
END $$;
"""


@pytest.fixture
def dsn() -> str:
    if not DSN:
        pytest.skip("TEST_DATABASE_URL not set")
    return DSN


@pytest.fixture
async def db(dsn):
    conn = await asyncpg.connect(dsn)
    await conn.execute(RESET_SQL)
    try:
        yield conn
    finally:
        await conn.close()
