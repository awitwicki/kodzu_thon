import pytest

from kodzu_thon.services.whisper import WhisperClient, WhisperError


async def test_transcribe_returns_text(mocker, tmp_path):
    audio = tmp_path / "a.ogg"
    audio.write_bytes(b"fake")
    fake_resp = mocker.Mock(status_code=200)
    fake_resp.json.return_value = {"text": "transcribed"}
    mocker.patch("kodzu_thon.services.whisper.requests.post", return_value=fake_resp)

    result = await WhisperClient("http://w/transcribe").transcribe(str(audio))
    assert result == "transcribed"


async def test_transcribe_raises_on_non_200(mocker, tmp_path):
    audio = tmp_path / "a.ogg"
    audio.write_bytes(b"x")
    mocker.patch(
        "kodzu_thon.services.whisper.requests.post",
        return_value=mocker.Mock(status_code=500, json=lambda: {"err": "x"}),
    )

    with pytest.raises(WhisperError):
        await WhisperClient("http://w/transcribe").transcribe(str(audio))
