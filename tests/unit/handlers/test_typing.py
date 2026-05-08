from unittest.mock import AsyncMock, MagicMock

from kodzu_thon.handlers.typing import _typing_logic


async def test_typing_uses_action_and_sleeps(fake_event, fake_client, fake_ctx, mocker):
    sleep = mocker.patch("kodzu_thon.handlers.typing.asyncio.sleep", new_callable=AsyncMock)
    action_cm = MagicMock()
    action_cm.__aenter__ = AsyncMock()
    action_cm.__aexit__ = AsyncMock()
    fake_client.action.return_value = action_cm

    await _typing_logic(fake_event, fake_client, fake_ctx)

    fake_event.delete.assert_awaited()
    fake_client.action.assert_called_once()
    sleep.assert_awaited_once_with(300)
