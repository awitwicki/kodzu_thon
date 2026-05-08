from unittest.mock import AsyncMock, MagicMock

from kodzu_thon.handlers.reactions import _reactions_logic


async def test_invalid_emoji_returns_palette(fake_event, fake_client, fake_ctx):
    fake_event.message.text = "!lk x 5"
    fake_event.get_reply_message = AsyncMock(return_value=MagicMock(sender="u"))
    await _reactions_logic(fake_event, fake_client, fake_ctx)
    fake_event.edit.assert_awaited()


async def test_too_many_messages_rejected(fake_event, fake_client, fake_ctx):
    fake_event.message.text = "!lk 👍 9999"
    fake_event.get_reply_message = AsyncMock(return_value=MagicMock(sender="u"))
    await _reactions_logic(fake_event, fake_client, fake_ctx)
    fake_event.edit.assert_awaited_with("Too much messages")


async def test_no_reply_deletes(fake_event, fake_client, fake_ctx):
    fake_event.message.text = "!lk 👍 5"
    fake_event.get_reply_message = AsyncMock(return_value=None)
    await _reactions_logic(fake_event, fake_client, fake_ctx)
    fake_event.delete.assert_awaited()
