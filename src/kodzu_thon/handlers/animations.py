import asyncio
import datetime
import random
import sys
import time

from telethon import events

HELP = [("🦔", "nice cartoon"), ("loading", "loading animation")]
COMMAND_PATTERNS = ["^🦔$", "^loading$"]


async def _hedgehog_logic(event, ctx) -> None:
    now = datetime.datetime.now(event.message.date.tzinfo)
    if (now - event.message.date).seconds >= 60:
        return
    for i in range(19):
        await event.edit("🍎" * (18 - i) + "🦔")
        await asyncio.sleep(0.5)


async def _loading_logic(event, ctx) -> None:
    try:
        now = datetime.datetime.now(event.message.date.tzinfo)
        if (now - event.message.date).seconds >= 60:
            return

        percentage = 0
        while percentage < 100:
            temp = max(100 - percentage, 5)
            percentage += temp / random.randint(5, 10)
            percentage = round(percentage, 2)
            progress = int(percentage // 5)
            await event.edit(f"`|{'█' * progress}{'-' * (20 - progress)}| {percentage}%`")
            await asyncio.sleep(0.5)
        time.sleep(5)
        await event.delete()
    except Exception as e:
        print(e, file=sys.stderr)


def register(client, ctx) -> None:
    @client.on(events.NewMessage(pattern="^🦔$", outgoing=True))
    async def _on_hh(event):
        await _hedgehog_logic(event, ctx)

    @client.on(events.NewMessage(pattern="^loading$", outgoing=True))
    async def _on_loading(event):
        await _loading_logic(event, ctx)
