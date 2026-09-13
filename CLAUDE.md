# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Working agreement

- **Do not create git commits until the user explicitly asks.** Stage/edit freely, but never run `git commit` (or `git commit --amend`) on your own initiative. Wait for an explicit instruction like "commit this" before committing. This rule overrides any default behavior to commit at the end of a task.
- **Bump `version` in `Settings` (`src/kodzu_thon/config.py`) whenever you make a code change.** It's a plain `vMAJOR.MINOR.PATCH` string with no other tooling behind it — increment the patch number for a normal change. It's surfaced by the `help` command (`handlers/help.py`), so it's the user's way of confirming a deploy picked up the latest code.

## Project overview

`kodzu_thon` is a Telethon-based Telegram **userbot** (runs as the user's own account, not a bot account). It listens for outgoing messages matching specific patterns and replaces them with command output — every handler uses `outgoing=True` and edits, deletes, or replies to the user's own message.

## Run / build

First-time login (interactive — prompts for phone, code, optionally 2FA, and writes a `.session` file into the `kodzuthon-session` volume):

```
docker-compose run -it --rm kodzuthon
```

Normal run:

```
docker-compose up -d
```

The compose file references an external network `kodzuverse_network`; create it once with `docker network create kodzuverse_network` if it doesn't exist.

Local (non-Docker) iteration is possible with system deps (`ffmpeg`, `libgeos`). InfluxDB connection errors at import are non-fatal and don't prevent bot startup.

## Architecture

The codebase is organized in three layers under `src/kodzu_thon/`:

1. **Handlers** (`handlers/*.py`) — Telethon event orchestration. Each handler registers patterns and edits/deletes/replies to messages. Handlers are stateless and purely delegate work.

2. **Services** (`services/*.py`) and **Speech** (`speech/*.py`) — Business logic and I/O operations. Services are injected via `AppContext` to enable testing. Speech synthesizes and merges audio/video via ffmpeg.

3. **Utils** (`utils/*.py`) — Shared utilities (file I/O, observability).

### Application context and configuration

`app.py` defines `AppContext`, which holds all mutable state and collaborators (InfluxDB client, message store, media fetcher, etc.). Configuration is loaded once at startup via `config.Settings.from_env()` and passed to the context.

### Entry point

`__main__.py` builds the app context and starts the Telethon client, registering all handlers.

### Observability sink (`services/observability.py`)

Writes to InfluxDB measurement `bots` in DB `bots`: one `income_messages: 1.0` point per
incoming group message (via `handlers/autoresponder.py`) with chat/user tags. Nothing else.

### Message recorder (`handlers/recorder.py`, `services/message_store.py`)

With `DATABASE_URL` set, every message, edit and deletion from groups, supergroups and
channels is written to PostgreSQL (private chats never are; the bot's own commands are
skipped via each handler module's `COMMAND_PATTERNS`). Flow:

- `handlers/recorder.py` → `services/message_extract.py` (pure Telethon → dataclass) →
  `MessageStore.enqueue` (bounded `asyncio.Queue`) → background writer task → asyncpg.
- `services/media_fetcher.py` downloads media ≤ `RECORD_MEDIA_MAX_BYTES` and profile
  photos and enqueues `BlobRecord`s; blobs are deduplicated by SHA-256 in table `blobs`.
- `db/migrate.py: ensure_database_exists` creates the target database itself if missing
  (connects to the `postgres` maintenance database with the same credentials; needs
  `CREATEDB` only when the database doesn't already exist). Schema lives in
  `db/migrations/*.sql` and is applied by the store on its first connection
  (`db/migrate.py: apply_migrations`). Bump `db/__init__.py: SCHEMA_VERSION` when adding
  a file. Both run automatically on every `MessageStore` connect — no manual SQL required
  for a plain `DATABASE_URL` pointed at a role with `CREATEDB` (e.g. `postgres`).
- Chat ids are Telethon marked ids. Deletions in basic groups arrive without a chat id and
  are matched by message id across chats of type `group`.
- If PostgreSQL is down the queue buffers (10 000 events, 256 MiB of blobs) and the bot
  keeps running; the oldest events are dropped with a stderr log when the buffer fills.

Design spec: `docs/superpowers/specs/2026-09-13-message-archive-design.md`.

### Speech pipeline (`speech/*.py`)

Modules shell out to `ffmpeg` and `ffprobe` to synthesize, merge, and compose audio/video. Filenames are generated internally (timestamps, UUIDs). User-controlled text is escaped before interpolation. Output files go to `media/` and are deleted after sending.

### Air-alarm map (`services/air_alarm_*.py`)

Loads Ukrainian oblast polygons from `media/ukraine-with-regions_1530.geojson` at import time, then on each `ppo` invocation fetches alarm state and renders an oblast-colored Basemap PNG.

### Session, secrets, network boundaries

- `session_data/session_name.session` is the Telegram auth state — kept in the `kodzuthon-session` Docker volume. Losing it means re-running interactive login.
- `.env` (gitignored) supplies `TELETHON_API_ID`, `TELETHON_API_HASH`, and `GEMINI_API_KEY`.

## Testing

Test stack: pytest + pytest-asyncio + pytest-mock + freezegun. All I/O is mocked at library boundaries.

```bash
pip install -e ".[dev]"
pytest -v
ruff check src tests
```

Integration tests (`tests/integration`, marker `integration`) run only when `TEST_DATABASE_URL`
points at a disposable database whose name contains `test`; see README.
