from unittest.mock import AsyncMock, MagicMock

from telethon import types

from kodzu_thon.handlers.sticker import _sticker_logic


def _reply(**kw):
    msg = MagicMock(id=42, photo=None, document=None, sticker=None, forward=None, raw_text="hello")
    for k, v in kw.items():
        setattr(msg, k, v)
    return msg


async def test_requires_reply(fake_event, fake_client):
    await _sticker_logic(fake_event, fake_client)

    assert "reply" in fake_event.edit.await_args.args[0].lower()
    fake_client.send_file.assert_not_awaited()


async def test_text_message_sends_quote_sticker(fake_event, fake_client, mocker):
    sender = types.User(id=7, first_name="Ann", last_name="B")
    msg = _reply()
    msg.get_sender = AsyncMock(return_value=sender)
    fake_event.message.is_reply = True
    fake_event.message.get_reply_message = AsyncMock(return_value=msg)
    fake_client.download_profile_photo = AsyncMock(return_value=None)
    render = mocker.patch("kodzu_thon.handlers.sticker.render_quote", return_value=b"WEBP")

    await _sticker_logic(fake_event, fake_client)

    quote = render.call_args.args[0]
    assert (quote.name, quote.text, quote.color_seed) == ("Ann B", "hello", 7)
    fake_event.delete.assert_awaited_once()
    call = fake_client.send_file.await_args
    assert call.args[1].getvalue() == b"WEBP"
    assert call.kwargs["reply_to"] == 42
    assert call.kwargs["mime_type"] == "image/webp"
    assert isinstance(call.kwargs["attributes"][0], types.DocumentAttributeSticker)


async def test_forward_uses_original_author_name(fake_event, fake_client, mocker):
    msg = _reply(forward=MagicMock(sender=None, chat=None, from_name="Hidden Person"))
    fake_event.message.is_reply = True
    fake_event.message.get_reply_message = AsyncMock(return_value=msg)
    render = mocker.patch("kodzu_thon.handlers.sticker.render_quote", return_value=b"W")

    await _sticker_logic(fake_event, fake_client)

    assert render.call_args.args[0].name == "Hidden Person"
    assert render.call_args.args[0].avatar is None


async def test_photo_message_sends_image_sticker(fake_event, fake_client, mocker):
    msg = _reply(photo=MagicMock())
    msg.download_media = AsyncMock(return_value=b"jpegbytes")
    fake_event.message.is_reply = True
    fake_event.message.get_reply_message = AsyncMock(return_value=msg)
    render = mocker.patch("kodzu_thon.handlers.sticker.render_image", return_value=b"W")

    await _sticker_logic(fake_event, fake_client)

    render.assert_called_once_with(b"jpegbytes")
    fake_client.send_file.assert_awaited_once()


async def test_nothing_to_render(fake_event, fake_client):
    msg = _reply(raw_text="")
    fake_event.message.is_reply = True
    fake_event.message.get_reply_message = AsyncMock(return_value=msg)

    await _sticker_logic(fake_event, fake_client)

    assert "nothing" in fake_event.edit.await_args.args[0].lower()
    fake_client.send_file.assert_not_awaited()
