import datetime
import sys

from telethon import events, types
from telethon.tl.functions.messages import SendReactionRequest

HELP = [("!lk {emoji} {count} [reply]", "reaction messages attack")]
COMMAND_PATTERNS = ["^!lk"]
_AVAILABLE = "💩👍👎🔥🥰👏😁🤔🤯🤬😱😢🤩🤮🎉❤️"
_MAX_COUNT = 1000


async def _reactions_logic(event, client, ctx) -> None:
    try:
        now = datetime.datetime.now(event.message.date.tzinfo)
        if (now - event.message.date).seconds >= 60:
            return

        reply = await event.get_reply_message()
        if not reply:
            await event.delete()
            return

        parts = event.message.text.split()
        emoji = parts[1]
        count = int(parts[2])

        if emoji not in _AVAILABLE:
            await event.edit(_AVAILABLE)
            return
        if count > _MAX_COUNT:
            await event.edit("Too much messages")
            return

        chat = await event.get_chat()
        await event.edit("...")

        i = 0
        async for msg in client.iter_messages(chat, from_user=reply.sender):
            if i > count:
                break
            i += 1
            try:
                reactions = msg.reactions
                if reactions and any(x.reaction == emoji for x in reactions.results):
                    continue
                await client(
                    SendReactionRequest(
                        peer=chat,
                        msg_id=msg.id,
                        reaction=[types.ReactionEmoji(emoticon=emoji)],
                    )
                )
            except Exception as e:
                print(e, file=sys.stderr)

        await event.delete()
    except Exception as e:
        print(e, file=sys.stderr)
        await event.edit("Fail")


def register(client, ctx) -> None:
    @client.on(events.NewMessage(pattern="^!lk", outgoing=True))
    async def _on_lk(event):
        await _reactions_logic(event, client, ctx)
