import sys

from telethon import events


def _normalize_chat_id(raw: int) -> int:
    s = str(raw)
    if s.startswith("-100"):
        return int(s[4:])
    return raw


async def _deletion_logic(event, ctx) -> None:
    try:
        chat_id = _normalize_chat_id(event.chat_id)
        for message_id in event.deleted_ids:
            cached = ctx.message_cache.get(chat_id=chat_id, message_id=message_id)
            if cached is None:
                continue
            ctx.influx.write(
                tags={
                    "botname": "kodzuthon",
                    "chatname": cached.chat_title,
                    "chat_id": chat_id,
                    "user_id": cached.sender_id,
                    "user_name": cached.sender_name,
                    "message_type": "deleted_text_message",
                },
                fields={"deleted_message_text": cached.text},
            )
    except Exception as e:
        print(e, file=sys.stderr)


def register(client, ctx) -> None:
    @client.on(events.MessageDeleted())
    async def _on_deleted(event):
        await _deletion_logic(event, ctx)
