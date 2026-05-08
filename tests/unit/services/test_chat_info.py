from unittest.mock import AsyncMock, MagicMock

from kodzu_thon.services.chat_info import build_message_chat_info


async def test_build_with_reply_returns_user_card(fake_event, fake_client):
    sender = MagicMock(username="alice", first_name="Alice", last_name="Last", id=7)
    reply_msg = MagicMock(sender=sender)
    fake_event.message.get_reply_message = AsyncMock(return_value=reply_msg)

    out = await build_message_chat_info(fake_event, fake_client)
    assert "@alice" in out
    assert "Alice Last" in out
    assert "7" in out


async def test_build_without_reply_rejects_non_channel(fake_event, fake_client):
    fake_event.message.get_reply_message = AsyncMock(return_value=None)
    fake_event.get_chat = AsyncMock(return_value=MagicMock(spec=[]))  # not Channel
    out = await build_message_chat_info(fake_event, fake_client)
    assert out == "Scan only chats"
