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
- `WHISPER_API_URL`: Whisper transcription endpoint (default: `http://whisper:4999/transcribe`)
- `INFLUX_HOST`: InfluxDB hostname (default: `monitoring_influxdb`)
- `INFLUX_PORT`: InfluxDB port (default: `8086`)
- `SESSION_PATH`: Path to Telethon session file (default: `session_data/session_name`)

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

## Tests

```bash
pip install -e ".[dev]"
pytest
ruff check src tests
ruff format src tests
```
