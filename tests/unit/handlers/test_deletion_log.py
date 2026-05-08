from unittest.mock import MagicMock

from kodzu_thon.handlers.deletion_log import _deletion_logic


async def test_deletion_writes_influx_when_cached(fake_ctx):
    cached = MagicMock(text="hi", sender_id=7, sender_name="@a", chat_title="G")
    fake_ctx.message_cache.get.return_value = cached

    event = MagicMock(_message_id=42)
    event.chat_id = -1001234567890
    event.deleted_ids = [42]

    await _deletion_logic(event, fake_ctx)

    fake_ctx.influx.write.assert_called_once()
    tags = fake_ctx.influx.write.call_args.kwargs["tags"]
    assert tags["message_type"] == "deleted_text_message"


async def test_deletion_no_cache_does_not_write(fake_ctx):
    fake_ctx.message_cache.get.return_value = None
    event = MagicMock(_message_id=99)
    event.chat_id = -1001234567890
    event.deleted_ids = [99]
    await _deletion_logic(event, fake_ctx)
    fake_ctx.influx.write.assert_not_called()
