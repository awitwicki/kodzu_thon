import datetime
from unittest.mock import AsyncMock, MagicMock

from kodzu_thon.handlers.bg_voice import _bg_voice_logic


async def test_recent_voice_is_merged_and_resent(fake_event, fake_client, fake_ctx, mocker):
    now = datetime.datetime.now(datetime.UTC)
    fake_event.voice = True
    fake_event.message.file = MagicMock()
    fake_event.message.file.media.date = now - datetime.timedelta(seconds=10)
    fake_event.download_media = AsyncMock(return_value="/tmp/v.ogg")

    cm = MagicMock()
    cm.__aenter__ = AsyncMock()
    cm.__aexit__ = AsyncMock()
    fake_client.action.return_value = cm

    mocker.patch(
        "kodzu_thon.handlers.bg_voice.merge_with_background", return_value=("new_/tmp/v.ogg", 7)
    )
    mocker.patch("kodzu_thon.handlers.bg_voice.get_waveform", return_value=[0, 1])
    rm = mocker.patch("kodzu_thon.handlers.bg_voice.safe_remove")

    await _bg_voice_logic(fake_event, fake_client, fake_ctx)

    fake_event.delete.assert_awaited()
    fake_client.send_file.assert_awaited()
    rm.assert_called_with("new_/tmp/v.ogg")


async def test_old_voice_ignored(fake_event, fake_client, fake_ctx):
    now = datetime.datetime.now(datetime.UTC)
    fake_event.voice = True
    fake_event.message.file = MagicMock()
    fake_event.message.file.media.date = now - datetime.timedelta(minutes=5)

    await _bg_voice_logic(fake_event, fake_client, fake_ctx)

    fake_event.delete.assert_not_awaited()
    fake_client.send_file.assert_not_awaited()


async def test_non_voice_ignored(fake_event, fake_client, fake_ctx):
    fake_event.voice = False
    await _bg_voice_logic(fake_event, fake_client, fake_ctx)
    fake_event.delete.assert_not_awaited()
