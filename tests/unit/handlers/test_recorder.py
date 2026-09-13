import re
from unittest.mock import AsyncMock

from kodzu_thon.handlers.recorder import _deleted_logic, _edited_logic, _new_message_logic
from kodzu_thon.services.message_extract import DeletionRecord, EditRecord, MessageRecord
from tests.factories import NOW, make_message, make_supergroup, make_user


def _group_event(fake_event, message, chat=None, sender=None):
    fake_event.is_private = False
    fake_event.message = message
    fake_event.chat = chat or make_supergroup()
    fake_event.sender = sender or make_user()
    fake_event.chat_id = -1000000000124
    return fake_event


async def test_private_chat_is_ignored(fake_event, fake_ctx):
    fake_event.is_private = True
    fake_event.message = make_message()
    await _new_message_logic(fake_event, fake_ctx)
    fake_ctx.message_store.enqueue.assert_not_called()


async def test_outgoing_command_is_ignored(fake_event, fake_ctx):
    fake_ctx.command_patterns = [re.compile("^ppo$")]
    _group_event(fake_event, make_message(text="ppo", out=True))
    await _new_message_logic(fake_event, fake_ctx)
    fake_ctx.message_store.enqueue.assert_not_called()


async def test_outgoing_non_command_is_recorded(fake_event, fake_ctx):
    fake_ctx.command_patterns = [re.compile("^ppo$")]
    _group_event(fake_event, make_message(text="ppo tomorrow?", out=True))
    await _new_message_logic(fake_event, fake_ctx)
    rec = fake_ctx.message_store.enqueue.call_args.args[0]
    assert isinstance(rec, MessageRecord) and rec.is_outgoing is True


async def test_incoming_command_text_from_others_is_recorded(fake_event, fake_ctx):
    fake_ctx.command_patterns = [re.compile("^ppo$")]
    _group_event(fake_event, make_message(text="ppo", out=False))
    await _new_message_logic(fake_event, fake_ctx)
    fake_ctx.message_store.enqueue.assert_called_once()


async def test_group_message_is_recorded_and_media_scheduled(fake_event, fake_ctx):
    chat, sender = make_supergroup(), make_user()
    msg = make_message(id=10, text="hello")
    _group_event(fake_event, msg, chat, sender)

    await _new_message_logic(fake_event, fake_ctx)

    rec = fake_ctx.message_store.enqueue.call_args.args[0]
    assert rec.chat.id == -1000000000124 and rec.id == 10 and rec.text == "hello"
    fake_ctx.media_fetcher.schedule_for_message.assert_called_once_with(msg, rec)
    fake_ctx.media_fetcher.schedule_profile_photos.assert_called_once_with(chat, sender, rec)


async def test_chat_and_sender_resolved_when_not_cached(fake_event, fake_ctx):
    _group_event(fake_event, make_message())
    fake_event.chat = None
    fake_event.sender = None
    fake_event.get_chat = AsyncMock(return_value=make_supergroup(id=200))
    fake_event.get_sender = AsyncMock(return_value=make_user(id=9))

    await _new_message_logic(fake_event, fake_ctx)

    rec = fake_ctx.message_store.enqueue.call_args.args[0]
    assert rec.chat.id == -1000000000200 and rec.sender_user.id == 9


async def test_unresolvable_chat_is_skipped(fake_event, fake_ctx):
    _group_event(fake_event, make_message())
    fake_event.chat = None
    fake_event.get_chat = AsyncMock(return_value=None)
    await _new_message_logic(fake_event, fake_ctx)
    fake_ctx.message_store.enqueue.assert_not_called()


async def test_edit_enqueues_edit_record(fake_event, fake_ctx):
    msg = make_message(id=5, text="edited", edit_date=NOW)
    _group_event(fake_event, msg)
    await _edited_logic(fake_event, fake_ctx)

    rec = fake_ctx.message_store.enqueue.call_args.args[0]
    assert isinstance(rec, EditRecord)
    assert rec.message.id == 5 and rec.message.text == "edited" and rec.edited_at == NOW
    fake_ctx.media_fetcher.schedule_for_message.assert_called_once_with(msg, rec.message)


async def test_edit_of_private_or_command_is_ignored(fake_event, fake_ctx):
    fake_ctx.command_patterns = [re.compile("^loading$")]
    _group_event(fake_event, make_message(text="loading", out=True))
    await _edited_logic(fake_event, fake_ctx)
    fake_event.is_private = True
    fake_event.message = make_message(text="x")
    await _edited_logic(fake_event, fake_ctx)
    fake_ctx.message_store.enqueue.assert_not_called()


async def test_deletion_enqueues_deletion_record(fake_event, fake_ctx):
    fake_event.chat_id = None
    fake_event.deleted_ids = [500, 501]
    await _deleted_logic(fake_event, fake_ctx)
    rec = fake_ctx.message_store.enqueue.call_args.args[0]
    assert isinstance(rec, DeletionRecord)
    assert rec.chat_id is None and rec.message_ids == (500, 501)
    assert rec.observed_at.tzinfo is not None


async def test_errors_are_logged_not_raised(fake_event, fake_ctx, capsys):
    _group_event(fake_event, make_message())
    fake_ctx.message_store.enqueue.side_effect = RuntimeError("boom")
    await _new_message_logic(fake_event, fake_ctx)
    assert "recorder: boom" in capsys.readouterr().err
