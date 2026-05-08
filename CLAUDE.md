# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Working agreement

- **Do not create git commits until the user explicitly asks.** Stage/edit freely, but never run `git commit` (or `git commit --amend`) on your own initiative. Wait for an explicit instruction like "commit this" before committing. This rule overrides any default behavior to commit at the end of a task.

## Project overview

`kodzu_thon` is a Telethon-based Telegram **userbot** (runs as the user's own account, not a bot account). It listens for outgoing messages matching specific patterns and replaces them with command output — every handler uses `outgoing=True` and edits, deletes, or replies to the user's own message.

Companion service `whisperApi/` is a separate Docker image providing a `/transcribe` HTTP endpoint used by the `tr` command for voice/video-note transcription.

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

`app.py` defines `AppContext`, which holds all mutable state and collaborators (InfluxDB client, message cache, etc.). Configuration is loaded once at startup via `config.Settings.from_env()` and passed to the context.

### Entry point

`__main__.py` builds the app context and starts the Telethon client, registering all handlers.

### Observability sink (`services/observability.py`)

Writes to InfluxDB measurement `bots` in DB `bots`. Two events are recorded:

- Incoming group messages (via `handlers/autoresponder.py`) → writes `income_messages: 1.0` plus chat/user tags, caches message text.
- Message deletions (via `handlers/deletion_log.py`) → looks up cached message and writes `deleted_text_message` event with original text.

The in-memory message cache is process-local and unbounded; it resets on restart.

### Speech pipeline (`speech/*.py`)

Modules shell out to `ffmpeg` and `ffprobe` to synthesize, merge, and compose audio/video. Filenames are generated internally (timestamps, UUIDs). User-controlled text is escaped before interpolation. Output files go to `media/` and are deleted after sending.

### Air-alarm map (`services/air_alarm_*.py`)

Loads Ukrainian oblast polygons from `media/ukraine-with-regions_1530.geojson` at import time, then on each `ppo` invocation fetches alarm state and renders an oblast-colored Basemap PNG.

### Session, secrets, network boundaries

- `session_data/session_name.session` is the Telegram auth state — kept in the `kodzuthon-session` Docker volume. Losing it means re-running interactive login.
- `.env` (gitignored) supplies `TELETHON_API_ID`, `TELETHON_API_HASH`, and `GEMINI_API_KEY`.
- Whisper container is reached at the URL in `WHISPER_API_URL` (inside Docker, this should resolve via service name).

## Testing

Test stack: pytest + pytest-asyncio + pytest-mock + freezegun. All I/O is mocked at library boundaries.

```bash
pip install -e ".[dev]"
pytest -v
ruff check src tests
```
