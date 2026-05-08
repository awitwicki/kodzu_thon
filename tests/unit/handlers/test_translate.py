from unittest.mock import AsyncMock, MagicMock

from kodzu_thon.handlers.translate import _tr_logic
from kodzu_thon.services.whisper import WhisperError


async def test_tr_text_calls_translator(fake_event, fake_ctx):
    fake_event.message.is_reply = True
    fake_event.message.get_reply_message = AsyncMock(
        return_value=MagicMock(text="hi", voice=None, video_note=None)
    )
    fake_ctx.translator.translate.return_value = "привіт"

    await _tr_logic(fake_event, fake_ctx)

    fake_ctx.translator.translate.assert_awaited_once_with("hi", dest="uk")
    assert fake_event.edit.await_args.args == ("привіт",)


async def test_tr_voice_calls_whisper(fake_event, fake_ctx, mocker):
    fake_event.message.is_reply = True
    reply = MagicMock(text=None, voice=True, video_note=None)
    reply.download_media = AsyncMock(return_value="/tmp/v.ogg")
    fake_event.message.get_reply_message = AsyncMock(return_value=reply)
    fake_ctx.whisper.transcribe.return_value = "transcribed"
    rm = mocker.patch("kodzu_thon.handlers.translate.safe_remove")

    await _tr_logic(fake_event, fake_ctx)

    fake_ctx.whisper.transcribe.assert_awaited_once_with("/tmp/v.ogg")
    rm.assert_called_with("/tmp/v.ogg")
    assert fake_event.edit.await_args.args == ("transcribed",)


async def test_tr_voice_whisper_error(fake_event, fake_ctx, mocker):
    fake_event.message.is_reply = True
    reply = MagicMock(text=None, voice=True, video_note=None)
    reply.download_media = AsyncMock(return_value="/tmp/v.ogg")
    fake_event.message.get_reply_message = AsyncMock(return_value=reply)
    fake_ctx.whisper.transcribe.side_effect = WhisperError("500")
    mocker.patch("kodzu_thon.handlers.translate.safe_remove")

    await _tr_logic(fake_event, fake_ctx)

    assert "error" in fake_event.edit.await_args.args[0].lower()
