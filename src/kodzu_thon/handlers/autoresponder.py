import sys

from telethon import events
from telethon.tl.types import Channel, Chat, User

_PRIVATE_VOICE_REPLY = (
    "Голосове повідомлення не доставлено, бо користувач заблокував цю опцію. "  # noqa: RUF001
    "Це повідомлення надіслано автоматично."
)


async def _autoresponder_logic(event, client, ctx) -> None:
    chat = event.chat if event.chat else (await event.get_chat())

    if event.is_private and event.voice:
        await client.send_message(chat, _PRIVATE_VOICE_REPLY, reply_to=event.message.id)

    if not event.is_group:
        return

    try:
        msg = event.message
        chat_title = chat.title
        chat_id = chat.id
        user_id = None
        user_name = None
        full_name = "unknown"

        if isinstance(msg.sender, User):
            user: User = msg.sender
            if user.username:
                user_name = "@" + user.username
            full_name = " ".join([user.first_name or "", user.last_name or ""]).strip()
            user_id = user.id
        elif isinstance(msg.sender, (Channel, Chat)):
            full_name = msg.sender.title
            user_id = msg.sender.id

        if (msg.is_channel or msg.is_group) and not user_id:
            user_id = chat_id
            user_name = chat_title

        user_name = user_name or full_name

        ctx.influx.write(
            tags={
                "botname": "kodzuthon",
                "chatname": chat_title,
                "chat_id": chat_id,
                "user_id": user_id,
                "user_name": user_name,
            },
            fields={"income_messages": 1.0},
        )

        if msg.text and isinstance(msg.sender, User) and not msg.sender.bot:
            ctx.message_cache.add(
                chat_id=chat_id,
                message_id=msg.id,
                sender_id=user_id,
                sender_name=user_name,
                chat_title=chat_title,
                text=msg.text,
            )
    except Exception as e:
        print(e, file=sys.stderr)


def register(client, ctx) -> None:
    @client.on(events.NewMessage(incoming=True))
    async def _on_incoming(event):
        await _autoresponder_logic(event, client, ctx)
