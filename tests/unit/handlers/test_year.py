from kodzu_thon.handlers.year import _year_logic


async def test_year_edits_with_progress(fake_event, fake_ctx, mocker):
    mocker.patch("kodzu_thon.handlers.year.get_year_progress", return_value="BAR")
    await _year_logic(fake_event, fake_ctx)
    out = fake_event.edit.await_args.args[0]
    assert "BAR" in out
