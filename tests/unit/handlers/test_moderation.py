import datetime
from unittest.mock import AsyncMock, MagicMock

from kodzu_thon.handlers.moderation import _mute_logic


async def test_mute_stale_message_ignored(fake_event, fake_client, fake_ctx):
    fake_event.message.date = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=5)
    fake_event.message.text = "!m 10m"
    reply = MagicMock(sender_id=42)
    fake_event.get_reply_message = AsyncMock(return_value=reply)

    await _mute_logic(fake_event, fake_client, fake_ctx)

    fake_event.get_reply_message.assert_not_awaited()
    fake_event.delete.assert_not_awaited()
    fake_event.edit.assert_not_awaited()


async def test_mute_no_reply_deletes(fake_event, fake_client, fake_ctx):
    fake_event.message.text = "!m 5m"
    fake_event.get_reply_message = AsyncMock(return_value=None)
    await _mute_logic(fake_event, fake_client, fake_ctx)
    fake_event.delete.assert_awaited()


async def test_mute_minutes_calls_ban_request(fake_event, fake_client, fake_ctx, mocker):
    fake_event.message.text = "!m 10m"
    reply = MagicMock(sender_id=42)
    fake_event.get_reply_message = AsyncMock(return_value=reply)
    fake_event.get_chat = AsyncMock(return_value=MagicMock(id=999))

    await _mute_logic(fake_event, fake_client, fake_ctx)

    fake_event.edit.assert_awaited()
    msg = fake_event.edit.await_args.args[0]
    assert "10" in msg
