from unittest.mock import AsyncMock, MagicMock

from kodzu_thon.handlers.summarize import _summarize_logic


def _async_iter(items):
    async def _gen():
        for x in items:
            yield x

    return _gen()


async def test_summarize_no_reply_warns(fake_event, fake_client, fake_ctx):
    fake_event.message.is_reply = False
    await _summarize_logic(fake_event, fake_client, fake_ctx)
    assert fake_event.edit.await_args_list[-1].args[0] == "Reply to a message to summarize from"


async def test_summarize_collects_and_calls_gemini(fake_event, fake_client, fake_ctx):
    fake_event.message.is_reply = True
    reply = MagicMock(id=10)
    fake_event.message.get_reply_message = AsyncMock(return_value=reply)
    fake_client.iter_messages.return_value = _async_iter(
        [MagicMock(text="hi"), MagicMock(text="there"), MagicMock(text=None)]
    )
    fake_ctx.gemini.generate.return_value = "short summary"

    await _summarize_logic(fake_event, fake_client, fake_ctx)

    fake_ctx.gemini.generate.assert_awaited_once()
    final = fake_event.edit.await_args.args[0]
    assert "Summary" in final
    assert "short summary" in final
