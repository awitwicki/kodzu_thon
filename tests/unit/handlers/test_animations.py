import datetime
from unittest.mock import AsyncMock

from kodzu_thon.handlers.animations import _hedgehog_logic, _loading_logic


async def test_hedgehog_stale_message_ignored(fake_event, fake_ctx, mocker):
    fake_event.message.date = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=5)
    sleep = mocker.patch("kodzu_thon.handlers.animations.asyncio.sleep", new_callable=AsyncMock)

    await _hedgehog_logic(fake_event, fake_ctx)

    fake_event.edit.assert_not_awaited()
    sleep.assert_not_awaited()


async def test_loading_stale_message_ignored(fake_event, fake_ctx, mocker):
    fake_event.message.date = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=5)
    sleep = mocker.patch("kodzu_thon.handlers.animations.asyncio.sleep", new_callable=AsyncMock)
    time_sleep = mocker.patch("kodzu_thon.handlers.animations.time.sleep")

    await _loading_logic(fake_event, fake_ctx)

    fake_event.edit.assert_not_awaited()
    fake_event.delete.assert_not_awaited()
    sleep.assert_not_awaited()
    time_sleep.assert_not_called()


async def test_hedgehog_calls_edit_19_times(fake_event, fake_ctx, mocker):
    mocker.patch("kodzu_thon.handlers.animations.asyncio.sleep", new_callable=AsyncMock)
    await _hedgehog_logic(fake_event, fake_ctx)
    assert fake_event.edit.await_count == 19


async def test_loading_completes_and_deletes(fake_event, fake_ctx, mocker):
    mocker.patch("kodzu_thon.handlers.animations.asyncio.sleep", new_callable=AsyncMock)
    mocker.patch("kodzu_thon.handlers.animations.time.sleep")
    await _loading_logic(fake_event, fake_ctx)
    fake_event.delete.assert_awaited()
