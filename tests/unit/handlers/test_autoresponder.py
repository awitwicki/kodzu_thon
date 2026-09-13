from unittest.mock import MagicMock

from telethon.tl.types import Channel, User

from kodzu_thon.handlers.autoresponder import _autoresponder_logic


def _group(fake_event):
    fake_event.is_private = False
    fake_event.is_group = True
    fake_event.voice = False
    fake_event.chat = MagicMock(id=10, title="Group")
    return fake_event


async def test_private_message_is_ignored(fake_event, fake_client, fake_ctx):
    fake_event.is_group = False
    fake_event.chat = MagicMock(id=42)
    await _autoresponder_logic(fake_event, fake_client, fake_ctx)
    fake_ctx.influx.write.assert_not_called()


async def test_group_message_writes_influx(fake_event, fake_client, fake_ctx):
    _group(fake_event)
    sender = MagicMock(spec=User)
    sender.id, sender.username, sender.first_name, sender.last_name, sender.bot = (
        7,
        "a",
        "A",
        "B",
        False,
    )
    fake_event.message = MagicMock(text="hi", sender=sender, id=99, is_channel=False, is_group=True)

    await _autoresponder_logic(fake_event, fake_client, fake_ctx)

    tags = fake_ctx.influx.write.call_args.kwargs["tags"]
    assert tags["user_id"] == 7 and tags["user_name"] == "@a" and tags["chatname"] == "Group"


async def test_group_message_with_none_sender_does_not_crash(
    fake_event, fake_client, fake_ctx, capsys
):
    _group(fake_event)
    fake_event.message = MagicMock(text="hi", sender=None, id=99, is_channel=True, is_group=True)
    await _autoresponder_logic(fake_event, fake_client, fake_ctx)
    fake_ctx.influx.write.assert_called()
    assert "has no attribute 'bot'" not in capsys.readouterr().err


async def test_group_message_with_channel_sender_does_not_crash(
    fake_event, fake_client, fake_ctx, capsys
):
    _group(fake_event)
    sender = MagicMock(spec=Channel)
    sender.id, sender.title = 555, "Some Channel"
    fake_event.message = MagicMock(text="hi", sender=sender, id=99, is_channel=True, is_group=True)
    await _autoresponder_logic(fake_event, fake_client, fake_ctx)
    tags = fake_ctx.influx.write.call_args.kwargs["tags"]
    assert tags["user_id"] == 555 and tags["user_name"] == "Some Channel"
