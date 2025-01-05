# kodzu_thon


![License](https://img.shields.io/badge/License-MIT-blue)
![Tests](https://img.shields.io/github/languages/top/awitwicki/kodzu_thon)
![Tests](https://img.shields.io/badge/python%20version-3.7-blue)
![Tests](https://img.shields.io/github/forks/awitwicki/kodzu_thon)
![Tests](https://img.shields.io/github/stars/awitwicki/kodzu_thon)
![Tests](https://img.shields.io/github/last-commit/awitwicki/kodzu_thon)

## Telethon implementation userbot

## Installing

### 1. Get [api_hash and api_id](https://core.telegram.org/api/obtaining_api_id)

### 2. Environments

Set environment variables for API keys:

* `TELETHON_CITY` (name of your city)

* `TELETHON_API_HASH` (from step 1)

* `TELETHON_API_ID` (from step 1)

in system environment for simple run, or in `.env` file for docker-compose using.

### 3. Docker compose

The first run requires authorization in the console:

```
docker-compose run
```

After authorization push `Ctrl + C` for stop and type next command for restart container in normal mode:

```
docker-compose up -d
```

(optionally) OR before run app in docker You need to get `.session` file by authorize app manually on python3 machine.
