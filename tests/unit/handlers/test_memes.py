from unittest.mock import AsyncMock, MagicMock

from kodzu_thon.handlers.memes import _send_meme


async def test_send_meme_sends_video_note(fake_event, fake_client, fake_ctx):
    cm = MagicMock()
    cm.__aenter__ = AsyncMock()
    cm.__aexit__ = AsyncMock()
    fake_client.action.return_value = cm

    await _send_meme(fake_event, fake_client, "media/same.mp4")

    fake_event.delete.assert_awaited()
    args, kwargs = fake_client.send_file.await_args
    assert "media/same.mp4" in args
    assert kwargs.get("video_note") is True
