from unittest.mock import AsyncMock

from kodzu_thon.services.translator import Translator


async def test_translate_returns_text_with_source(mocker):
    fake_inner = mocker.Mock()
    fake_inner.translate = AsyncMock(return_value=mocker.Mock(text="hello", src="uk"))
    mocker.patch("kodzu_thon.services.translator._GoogleTranslator", return_value=fake_inner)

    out = await Translator().translate("привіт", dest="en")
    assert "hello" in out
    assert "uk" in out


async def test_translate_returns_fallback_on_error(mocker):
    fake_inner = mocker.Mock()
    fake_inner.translate = AsyncMock(side_effect=RuntimeError("down"))
    mocker.patch("kodzu_thon.services.translator._GoogleTranslator", return_value=fake_inner)

    out = await Translator().translate("x", dest="uk")
    assert out == "Can't translate"
