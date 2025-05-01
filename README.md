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

* `TELETHON_API_HASH` (from step 1)

* `TELETHON_API_ID` (from step 1)

in system environment for simple run, or in `.env` file for docker-compose using.

### 3. Docker compose

The first run requires authorization in the console:

`docker-compose run -it --rm  kodzuthon`

Provide your credentials to log in in telegram

After authorization push `Ctrl + C` for stop and type next command for restart container in normal mode:

```
docker-compose up -d
```


## (optional) adding telethon .session file to docker volume manually (to run containers without initial authorization)

1. CD to folder with .session file
2. Create docker volume `docker volume create kodzu_thon_kodzuthon-session`
3. Copy session to volume `docker run --rm -v "${PWD}:/from" -v kodzu_thon_kodzuthon-session:/to alpine cp /from/session_name.session /to/`

Done. Now You can start docker compose project.
