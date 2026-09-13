# kodzu_thon

![License](https://img.shields.io/badge/License-MIT-blue)
![Tests](https://img.shields.io/github/languages/top/awitwicki/kodzu_thon)
![Python](https://img.shields.io/badge/python%20version-3.12+-blue)
![Forks](https://img.shields.io/github/forks/awitwicki/kodzu_thon)
![Stars](https://img.shields.io/github/stars/awitwicki/kodzu_thon)
![Last Commit](https://img.shields.io/github/last-commit/awitwicki/kodzu_thon)

## Telethon-based Telegram userbot

A userbot (runs as the user's own account, not a bot account) that listens for outgoing messages matching specific patterns and replaces them with command output.

## Installation

### Prerequisites

- **Python 3.12+**
- **ffmpeg** and **libgeos-dev** (system dependencies)
- **Telegram API credentials** (from https://core.telegram.org/api/obtaining_api_id)

### Setup

1. Get your `TELETHON_API_ID` and `TELETHON_API_HASH` from https://core.telegram.org/api/obtaining_api_id

2. Get a Gemini API key from https://aistudio.google.com/apikey

3. Install the package:

```bash
pip install -e ".[dev]"
```

4. Set environment variables (see below)

## Environment Variables

Required:
- `TELETHON_API_ID`: Your Telegram API ID
- `TELETHON_API_HASH`: Your Telegram API hash
- `GEMINI_API_KEY`: Your Gemini API key (for ai/summarize commands)

Optional:
- `INFLUX_HOST`: InfluxDB hostname (default: `monitoring_influxdb`)
- `INFLUX_PORT`: InfluxDB port (default: `8086`)
- `SESSION_PATH`: Path to Telethon session file (default: `session_data/session_name`)
- `DATABASE_URL`: PostgreSQL connection string for the message archive, e.g. `postgresql://kodzuthon:password@postgres:5432/kodzu_messages`. Unset = recording disabled.
- `RECORD_MEDIA_MAX_BYTES`: media at or below this size is stored in the database (default: `5242880`, 5 MiB)

Set these in the system environment, or in a `.env` file for docker-compose.

## Running

### Local (non-Docker)

```bash
python -m kodzu_thon
```

Note: Local iteration requires ffmpeg and libgeos installed. InfluxDB connection errors are expected and non-fatal.

### Docker Compose

First-time login (interactive — prompts for phone, code, optionally 2FA):

```bash
docker-compose run -it --rm kodzuthon
```

After authorization, press Ctrl+C and start normally:

```bash
docker-compose up -d
```

The compose file requires an external network:

```bash
docker network create kodzuverse_network
```

### Session management (optional)

To pre-populate the session without interactive login:

1. Place your `.session` file in the current directory
2. Create the volume: `docker volume create kodzu_thon_kodzuthon-session`
3. Copy to volume: `docker run --rm -v "${PWD}:/from" -v kodzu_thon_kodzuthon-session:/to alpine cp /from/session_name.session /to/`

Now you can run `docker-compose up -d` without interactive login.

## Message archive

With `DATABASE_URL` set, the bot records every message, edit and deletion it sees in groups,
supergroups and channels (private chats are never recorded) into PostgreSQL, together with
media up to `RECORD_MEDIA_MAX_BYTES` and user/chat profile photos.

### Setup

Just point `DATABASE_URL` at a PostgreSQL server (PostgreSQL 14+; the
`timescale/timescaledb:latest-pg18` image works) and start the bot — nothing else to run
by hand:

```
DATABASE_URL=postgresql://<user>:<password>@<host>:5432/kodzu_messages
```

Any role that can log in works, e.g. the server's `postgres` superuser. On first connect the
bot:
- creates the `kodzu_messages` database itself if it doesn't exist yet (needs `CREATEDB` on
  the connecting role — skipped entirely if the database is already there),
- creates and migrates its own schema (tables, indexes, the `pg_trgm` extension) automatically,
  safe to run on every restart — already-applied migrations are skipped.

No manual SQL, no roles to pre-create for this to work.

### Optional: a scoped-down role instead of a superuser

If you'd rather not hand the bot a superuser connection, `deploy/postgres-init.sql` (roles +
database) and `deploy/postgres-init-db.sql` (extension + grants) set up a least-privilege
`kodzuthon` role instead — run the first against the default database, the second against
`kodzu_messages` (as two separate files, not one script with `\connect`, so they also work
pasted into a GUI client like pgAdmin or DBeaver, not just `psql`). Then point `DATABASE_URL`
at that role instead of a superuser.

Design: `docs/superpowers/specs/2026-09-13-message-archive-design.md`.

## Tests

```bash
pip install -e ".[dev]"
pytest
ruff check src tests
ruff format src tests
```

Integration tests need a disposable PostgreSQL database whose name contains `test`
(the suite drops and recreates its `public` schema):

```bash
docker run --rm -d --name kodzu-test-pg -e POSTGRES_PASSWORD=pw -e POSTGRES_DB=kodzu_test -p 55432:5432 timescale/timescaledb:latest-pg18
TEST_DATABASE_URL=postgresql://postgres:pw@localhost:55432/kodzu_test pytest tests/integration
docker stop kodzu-test-pg
```
