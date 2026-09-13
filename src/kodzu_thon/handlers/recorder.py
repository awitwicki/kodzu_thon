"""Records every group/supergroup/channel message, edit and deletion the account
sees. Private chats and the bot's own commands are skipped. All work is handed
to ctx.message_store / ctx.media_fetcher; nothing blocks the event loop here."""

import sys
from datetime import UTC, datetime

from telethon import events

from kodzu_thon.services.message_extract import (
    DeletionRecord,
    EditRecord,
    extract_message,
    matches_command,
)


def _is_own_command(event, ctx) -> bool:
    return bool(event.message.out) and matches_command(
        event.message.message or "", ctx.command_patterns
    )


async def _resolve(event):
    chat = event.chat or await event.get_chat()
    sender = event.sender or await event.get_sender()
    return chat, sender


async def _new_message_logic(event, ctx) -> None:
    try:
        if event.is_private or _is_own_command(event, ctx):
            return
        chat, sender = await _resolve(event)
        if chat is None:
            return
        rec = extract_message(
            event.message, chat, sender, max_media_bytes=ctx.settings.record_media_max_bytes
        )
        ctx.message_store.enqueue(rec)
        ctx.media_fetcher.schedule_for_message(event.message, rec)
        ctx.media_fetcher.schedule_profile_photos(chat, sender, rec)
    except Exception as e:
        print(f"recorder: {e}", file=sys.stderr)


async def _edited_logic(event, ctx) -> None:
    try:
        if event.is_private or _is_own_command(event, ctx):
            return
        chat, sender = await _resolve(event)
        if chat is None:
            return
        rec = extract_message(
            event.message, chat, sender, max_media_bytes=ctx.settings.record_media_max_bytes
        )
        edited_at = event.message.edit_date or datetime.now(UTC)
        ctx.message_store.enqueue(EditRecord(message=rec, edited_at=edited_at))
        ctx.media_fetcher.schedule_for_message(event.message, rec)
    except Exception as e:
        print(f"recorder: {e}", file=sys.stderr)


async def _deleted_logic(event, ctx) -> None:
    try:
        ctx.message_store.enqueue(
            DeletionRecord(
                chat_id=event.chat_id,
                message_ids=tuple(event.deleted_ids),
                observed_at=datetime.now(UTC),
            )
        )
    except Exception as e:
        print(f"recorder: {e}", file=sys.stderr)


def register(client, ctx) -> None:
    @client.on(events.NewMessage())
    async def _on_new_message(event):
        await _new_message_logic(event, ctx)

    @client.on(events.MessageEdited())
    async def _on_edited(event):
        await _edited_logic(event, ctx)

    @client.on(events.MessageDeleted())
    async def _on_deleted(event):
        await _deleted_logic(event, ctx)
