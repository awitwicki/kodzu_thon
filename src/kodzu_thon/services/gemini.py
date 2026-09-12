import asyncio

from google import genai
from google.genai import types


class GeminiError(Exception):
    pass


class GeminiClient:
    def __init__(self, api_key: str, model_name: str = "gemini-flash-latest"):
        self._client = genai.Client(api_key=api_key)
        self._model_name = model_name

    async def generate(self, prompt: str) -> str:
        try:
            resp = await asyncio.to_thread(
                self._client.models.generate_content,
                model=self._model_name,
                contents=prompt,
            )
            return resp.text
        except Exception as e:
            raise GeminiError(str(e)) from e

    async def transcribe(self, file_path: str, mime_type: str = "audio/ogg") -> str:
        try:
            return await asyncio.to_thread(self._transcribe_sync, file_path, mime_type)
        except Exception as e:
            raise GeminiError(str(e)) from e

    def _transcribe_sync(self, file_path: str, mime_type: str) -> str:
        with open(file_path, "rb") as f:
            data = f.read()
        resp = self._client.models.generate_content(
            model=self._model_name,
            contents=[
                "Transcribe the speech in this audio/video verbatim. "
                "Return only the transcript text, with no extra commentary.",
                types.Part.from_bytes(data=data, mime_type=mime_type),
            ],
        )
        return resp.text
