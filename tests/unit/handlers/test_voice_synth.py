from unittest.mock import AsyncMock, MagicMock

from kodzu_thon.handlers.voice_synth import _video_logic, _voice_logic


async def test_voice_logic_sends_voice_file(fake_event, fake_client, fake_ctx, mocker):
    fake_event.message.text = "!a hello"
    fake_event.message.is_reply = False
    mocker.patch("kodzu_thon.handlers.voice_synth.build_voice", return_value=("media/x.ogg", 7))
    mocker.patch("kodzu_thon.handlers.voice_synth.get_waveform", return_value=[0, 1, 2])
    rm = mocker.patch("kodzu_thon.handlers.voice_synth.safe_remove")

    cm = MagicMock()
    cm.__aenter__ = AsyncMock()
    cm.__aexit__ = AsyncMock()
    fake_client.action.return_value = cm

    await _voice_logic(fake_event, fake_client, fake_ctx)

    fake_event.delete.assert_awaited()
    fake_client.send_file.assert_awaited()
    rm.assert_called_with("media/x.ogg")


async def test_video_logic_sends_video_note(fake_event, fake_client, fake_ctx, mocker):
    fake_event.message.text = "!v hello"
    mocker.patch("kodzu_thon.handlers.voice_synth.build_voice", return_value=("media/x.ogg", 5))
    mocker.patch("kodzu_thon.handlers.voice_synth.mount_video", return_value="out.mp4")
    rm = mocker.patch("kodzu_thon.handlers.voice_synth.safe_remove")

    cm = MagicMock()
    cm.__aenter__ = AsyncMock()
    cm.__aexit__ = AsyncMock()
    fake_client.action.return_value = cm

    await _video_logic(fake_event, fake_client, fake_ctx)

    fake_event.delete.assert_awaited()
    fake_client.send_file.assert_awaited()
    assert rm.call_count >= 2
