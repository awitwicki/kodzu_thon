import pytest

from kodzu_thon.services.gemini import GeminiClient, GeminiError


async def test_generate_returns_response_text(mocker):
    fake_resp = mocker.Mock(text="hello world")
    fake_model = mocker.Mock()
    fake_model.generate_content.return_value = fake_resp
    mocker.patch("kodzu_thon.services.gemini.genai.configure")
    mocker.patch("kodzu_thon.services.gemini.genai.GenerativeModel", return_value=fake_model)

    client = GeminiClient(api_key="fake")
    result = await client.generate("prompt")

    assert result == "hello world"
    fake_model.generate_content.assert_called_once_with("prompt")


async def test_generate_wraps_errors(mocker):
    fake_model = mocker.Mock()
    fake_model.generate_content.side_effect = RuntimeError("boom")
    mocker.patch("kodzu_thon.services.gemini.genai.configure")
    mocker.patch("kodzu_thon.services.gemini.genai.GenerativeModel", return_value=fake_model)

    with pytest.raises(GeminiError, match="boom"):
        await GeminiClient(api_key="fake").generate("x")
