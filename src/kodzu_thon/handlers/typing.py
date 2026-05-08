import asyncio
import sys

from telethon import events

HELP = [("!t", "imitation typing for 5 minutes")]


async def _typing_logic(event, client, ctx) -> None:
    try:
        chat = await event.get_chat()
        await event.delete()
        async with client.action(chat, "typing"):
            await asyncio.sleep(300)
    except Exception as e:
        print(e, file=sys.stderr)


def register(client, ctx) -> None:
    @client.on(events.NewMessage(pattern="^!t$", outgoing=True))
    async def _on_t(event):
        await _typing_logic(event, client, ctx)
