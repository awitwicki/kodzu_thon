from unittest.mock import AsyncMock

from kodzu_thon.handlers.animations import _hedgehog_logic, _loading_logic


async def test_hedgehog_calls_edit_19_times(fake_event, fake_ctx, mocker):
    mocker.patch("kodzu_thon.handlers.animations.asyncio.sleep", new_callable=AsyncMock)
    await _hedgehog_logic(fake_event, fake_ctx)
    assert fake_event.edit.await_count == 19


async def test_loading_completes_and_deletes(fake_event, fake_ctx, mocker):
    mocker.patch("kodzu_thon.handlers.animations.asyncio.sleep", new_callable=AsyncMock)
    mocker.patch("kodzu_thon.handlers.animations.time.sleep")
    await _loading_logic(fake_event, fake_ctx)
    fake_event.delete.assert_awaited()
