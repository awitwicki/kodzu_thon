from kodzu_thon.handlers.ai import _ai_logic
from kodzu_thon.services.gemini import GeminiError


async def test_ai_empty_prompt_returns_message(fake_event, fake_ctx):
    fake_event.message.text = "ai "
    await _ai_logic(fake_event, fake_ctx)
    fake_event.edit.assert_awaited_with("Please provide a prompt")
    fake_ctx.gemini.generate.assert_not_called()


async def test_ai_happy_path(fake_event, fake_ctx):
    fake_event.message.text = "ai hello"
    fake_ctx.gemini.generate.return_value = "world"
    await _ai_logic(fake_event, fake_ctx)
    fake_ctx.gemini.generate.assert_awaited_once_with("hello")
    assert fake_event.edit.await_args.args == ("world",)


async def test_ai_wraps_gemini_error(fake_event, fake_ctx):
    fake_event.message.text = "ai x"
    fake_ctx.gemini.generate.side_effect = GeminiError("boom")
    await _ai_logic(fake_event, fake_ctx)
    assert "Error" in fake_event.edit.await_args.args[0]
