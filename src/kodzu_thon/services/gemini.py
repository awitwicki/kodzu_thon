import asyncio

import google.generativeai as genai


class GeminiError(Exception):
    pass


class GeminiClient:
    def __init__(self, api_key: str, model_name: str = "gemini-flash-latest"):
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model_name)

    async def generate(self, prompt: str) -> str:
        try:
            resp = await asyncio.to_thread(self._model.generate_content, prompt)
            return resp.text
        except Exception as e:
            raise GeminiError(str(e)) from e
