import asyncio

import requests


class WhisperError(Exception):
    pass


class WhisperClient:
    def __init__(self, url: str):
        self._url = url

    async def transcribe(self, file_path: str) -> str:
        return await asyncio.to_thread(self._transcribe_sync, file_path)

    def _transcribe_sync(self, file_path: str) -> str:
        with open(file_path, "rb") as f:
            resp = requests.post(self._url, files={"file": f})
        if resp.status_code != 200:
            raise WhisperError(f"status {resp.status_code}: {resp.json()}")
        return resp.json().get("text", "")
