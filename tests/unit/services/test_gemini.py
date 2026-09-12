import pytest

from kodzu_thon.services.gemini import GeminiClient, GeminiError


async def test_generate_returns_response_text(mocker):
    fake_resp = mocker.Mock(text="hello world")
    fake_client = mocker.Mock()
    fake_client.models.generate_content.return_value = fake_resp
    mocker.patch("kodzu_thon.services.gemini.genai.Client", return_value=fake_client)

    client = GeminiClient(api_key="fake")
    result = await client.generate("prompt")

    assert result == "hello world"
    fake_client.models.generate_content.assert_called_once_with(
        model="gemini-flash-latest", contents="prompt"
    )


async def test_generate_wraps_errors(mocker):
    fake_client = mocker.Mock()
    fake_client.models.generate_content.side_effect = RuntimeError("boom")
    mocker.patch("kodzu_thon.services.gemini.genai.Client", return_value=fake_client)

    with pytest.raises(GeminiError, match="boom"):
        await GeminiClient(api_key="fake").generate("x")


async def test_transcribe_returns_response_text(mocker, tmp_path):
    audio = tmp_path / "voice.ogg"
    audio.write_bytes(b"fake-audio-bytes")
    fake_resp = mocker.Mock(text="hello transcription")
    fake_client = mocker.Mock()
    fake_client.models.generate_content.return_value = fake_resp
    mocker.patch("kodzu_thon.services.gemini.genai.Client", return_value=fake_client)
    fake_part = mocker.Mock()
    from_bytes = mocker.patch(
        "kodzu_thon.services.gemini.types.Part.from_bytes", return_value=fake_part
    )

    client = GeminiClient(api_key="fake")
    result = await client.transcribe(str(audio), mime_type="audio/ogg")

    assert result == "hello transcription"
    from_bytes.assert_called_once_with(data=b"fake-audio-bytes", mime_type="audio/ogg")
    _, kwargs = fake_client.models.generate_content.call_args
    assert kwargs["model"] == "gemini-flash-latest"
    assert kwargs["contents"][-1] is fake_part


async def test_transcribe_wraps_errors(mocker, tmp_path):
    audio = tmp_path / "voice.ogg"
    audio.write_bytes(b"data")
    fake_client = mocker.Mock()
    fake_client.models.generate_content.side_effect = RuntimeError("boom")
    mocker.patch("kodzu_thon.services.gemini.genai.Client", return_value=fake_client)
    mocker.patch("kodzu_thon.services.gemini.types.Part.from_bytes")

    with pytest.raises(GeminiError, match="boom"):
        await GeminiClient(api_key="fake").transcribe(str(audio))
