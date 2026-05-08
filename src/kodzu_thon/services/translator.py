from googletrans import Translator as _GoogleTranslator


class Translator:
    def __init__(self) -> None:
        self._inner = _GoogleTranslator()

    async def translate(self, text: str, dest: str = "uk") -> str:
        try:
            result = await self._inner.translate(text, dest=dest)
            return f"Translated from: {result.src}\n\n{result.text}"
        except Exception:
            return "Can't translate"
