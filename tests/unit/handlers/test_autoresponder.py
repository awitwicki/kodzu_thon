from unittest.mock import MagicMock

from kodzu_thon.handlers.autoresponder import _autoresponder_logic


async def test_private_voice_triggers_canned_reply(fake_event, fake_client, fake_ctx):
    fake_event.is_private = True
    fake_event.is_group = False
    fake_event.voice = True
    fake_event.chat = MagicMock(id=42)
    await _autoresponder_logic(fake_event, fake_client, fake_ctx)
    fake_client.send_message.assert_awaited()


async def test_group_message_writes_influx_and_caches(fake_event, fake_client, fake_ctx):
    fake_event.is_private = False
    fake_event.is_group = True
    fake_event.voice = False
    chat = MagicMock(id=10, title="Group")
    fake_event.chat = chat

    sender = MagicMock(spec=["id", "username", "first_name", "last_name", "bot"])
    sender.id = 7
    sender.username = "a"
    sender.first_name = "A"
    sender.last_name = "B"
    sender.bot = False
    msg = MagicMock(text="hi", sender=sender, id=99, is_channel=False, is_group=True)
    fake_event.message = msg

    await _autoresponder_logic(fake_event, fake_client, fake_ctx)

    fake_ctx.influx.write.assert_called()
    fake_ctx.message_cache.add.assert_called()
