from kodzu_thon.handlers.help import _help_logic


async def test_help_emits_version_and_help_lines(fake_event, fake_ctx):
    fake_ctx.help_lines = [("ai {prompt}", "ask Gemini AI"), ("summ", "summarize")]
    await _help_logic(fake_event, fake_ctx)
    text = fake_event.edit.await_args.args[0]
    assert "v1.17.0" in text
    assert "ai {prompt}" in text
    assert "ask Gemini AI" in text
    assert "summ" in text
