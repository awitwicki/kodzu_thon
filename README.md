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
pip install -e ".[dev,web]"
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

### Optional: a read-only role for the web viewer

The web viewer (below) works with the same `DATABASE_URL`. If you want it to hold only a
read-only connection, create a role and point `WEB_DATABASE_URL` at it — run this once,
connected to `kodzu_messages`:

```sql
CREATE ROLE kodzuweb_ro LOGIN PASSWORD 'change-me';
GRANT CONNECT ON DATABASE kodzu_messages TO kodzuweb_ro;
GRANT USAGE ON SCHEMA public TO kodzuweb_ro;
GRANT SELECT ON chats, users, user_name_history, messages, message_edits, blobs, schema_migrations TO kodzuweb_ro;
GRANT SELECT, INSERT, UPDATE, DELETE ON web_sessions, web_login_attempts, web_totp_state TO kodzuweb_ro;
GRANT USAGE, SELECT ON SEQUENCE web_login_attempts_id_seq TO kodzuweb_ro;
```

Design: `docs/superpowers/specs/2026-09-13-message-archive-design.md`.

## Web viewer (`kodzuthon.web`)

A separate container that lets one admin browse the archive: chats, timelines with deleted
and edited markers and filters, message permalinks with edit history and raw JSON, user
profiles with name history, a global deleted feed, search, and stored media. Server-rendered,
no JavaScript, strict CSP; single admin with argon2id password, optional TOTP, server-side
sessions, CSRF tokens and login rate limiting.

### Setup

1. Generate the password hash:

   ```bash
   docker-compose run --rm --no-deps kodzuthon.web python -m kodzu_thon.web hash-password
   ```

2. Add to `.env`, **doubling every `$` to `$$`** (e.g. `$argon2id$v=19$...` becomes
   `$$argon2id$$v=19$$...`):

   ```
   WEB_ADMIN_USER=admin
   WEB_ADMIN_PASSWORD_HASH=$$argon2id$$v=19$$...   # from step 1, every $ doubled
   ```

   This is required because Docker Compose interpolates `$VAR`/`${VAR}` references in
   `.env` values (the same mechanism behind `${WEB_PORT:-8080}` in `docker-compose.yml`)
   — an unescaped `$argon2id` is read as a reference to an unset variable named `argon2id`
   and silently replaced with an empty string, corrupting the hash. This applies regardless
   of how the line gets into `.env` (manual edit, `echo`, a CI script) — `$$` is Compose's
   own escape sequence for a literal `$`, documented at
   https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/.
   Verify with: `docker-compose run --rm --no-deps kodzuthon.web python -c "import os; print(repr(os.environ.get('WEB_ADMIN_PASSWORD_HASH')))"`
   — it should print the hash with a single `$` in each place, not the doubled form and
   not a truncated one.

   `WEB_DATABASE_URL` is optional and defaults to `DATABASE_URL`.

3. `docker-compose up -d --build`, then open `http://<host>:8080` (change the host port with
   `WEB_PORT`). The web service checks that the recorder has already created the schema and
   refuses to start otherwise — start `kodzuthon` first.

**Troubleshooting: `Configuration error: WEB_ADMIN_PASSWORD_HASH must be an argon2 hash`**
at container startup, even though `.env` looks correct — almost always means the `$` in the
hash got eaten before the container ever saw it. Two independent places this happens, check
both:
- **Docker Compose itself** (see step 2 above) — the value in `.env` needs `$$`, not `$`.
  This is the usual cause and bites regardless of how the line got into `.env`.
- **A shell in the path that wrote `.env`** — `echo "KEY=$value" >> .env` (double quotes) in
  a manual terminal command, a CI "run script" build step, or any tool that shells out to
  write the file, expands `$argon2id`/`$v`/`$m`/etc. as (unset, so blank) shell variables
  *before* the text even reaches Compose. Fix: single-quote the whole value in the writing
  command (`echo 'KEY=$$...' >> .env`), or write the line with a text editor instead of a
  shell command.

Either way, the diagnostic in step 2 (`python -c "import os; print(repr(...))"`, run inside
the actual container) tells you definitively what value the app receives — trust that over
staring at `.env`, since two different layers can each independently mangle the same `$`.

Optional two-factor login: `docker-compose run --rm --no-deps kodzuthon.web python -m kodzu_thon.web totp-secret admin`
prints `WEB_TOTP_SECRET=...` for `.env` and an `otpauth://` URI to scan with an authenticator app.

Environment variables (all read by the web container only):

- `WEB_DATABASE_URL`: connection string (default: `DATABASE_URL`)
- `WEB_ADMIN_USER`, `WEB_ADMIN_PASSWORD_HASH`: required
- `WEB_TOTP_SECRET`: base32 secret; empty disables the second factor
- `WEB_COOKIE_SECURE`: `true` behind TLS (also enables HSTS); default `false` for plain LAN use
- `WEB_TIMEZONE`: display timezone (default `Europe/Warsaw`)
- `WEB_FORWARDED_ALLOW_IPS`: set to your reverse proxy's IP to trust `X-Forwarded-For` from it
- `WEB_PORT`: host port published by docker-compose (default `8080`)

Exposing it beyond the LAN: put a TLS-terminating reverse proxy in front, set
`WEB_COOKIE_SECURE=true` and `WEB_FORWARDED_ALLOW_IPS=<proxy ip>`, and enable TOTP.

## Tests

```bash
pip install -e ".[dev,web]"
pytest
ruff check src tests
ruff format src tests
```

Integration tests need a disposable PostgreSQL database whose name contains `test`
(the suite drops and recreates its `public` schema). The web repository has its own integration tests in `tests/integration/test_web_repository.py`, run by the same command.

```bash
docker run --rm -d --name kodzu-test-pg -e POSTGRES_PASSWORD=pw -e POSTGRES_DB=kodzu_test -p 55432:5432 timescale/timescaledb:latest-pg18
TEST_DATABASE_URL=postgresql://postgres:pw@localhost:55432/kodzu_test pytest tests/integration
docker stop kodzu-test-pg
```
