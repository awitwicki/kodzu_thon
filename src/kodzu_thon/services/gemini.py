import asyncio

from google import genai


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
