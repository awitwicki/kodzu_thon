from kodzu_thon.handlers.air_alarm import _ppo_logic


async def test_ppo_sends_image_with_caption(fake_event, fake_client, fake_ctx, mocker):
    fake_ctx.air_alarm.fetch_alarms.return_value = {
        "Київська область": True,
        "Львівська область": False,
    }
    fake_ctx.air_alarm.render.return_value = "img/x.png"
    rm = mocker.patch("kodzu_thon.handlers.air_alarm.safe_remove")

    await _ppo_logic(fake_event, fake_client, fake_ctx)

    fake_event.delete.assert_awaited()
    fake_client.send_file.assert_awaited()
    _, kwargs = fake_client.send_file.await_args
    assert kwargs["caption"].startswith("Повітряна тривога")
    assert "Київська область" in kwargs["caption"]
    rm.assert_called_once_with("img/x.png")


async def test_ppo_failure_edits_fail(fake_event, fake_client, fake_ctx):
    fake_ctx.air_alarm.fetch_alarms.side_effect = RuntimeError("down")
    await _ppo_logic(fake_event, fake_client, fake_ctx)
    fake_event.edit.assert_awaited_with("Fail")
