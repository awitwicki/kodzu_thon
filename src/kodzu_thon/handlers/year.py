import sys

from telethon import events

from kodzu_thon.services.year_progress import get_year_progress

HELP = [("year", "year info")]


async def _year_logic(event, ctx) -> None:
    try:
        text = "Year progress:\n" + get_year_progress(30)
        await event.edit(f"`{text}`")
    except Exception as e:
        print(e, file=sys.stderr)


def register(client, ctx) -> None:
    @client.on(events.NewMessage(pattern="^year$", outgoing=True))
    async def _on_year(event):
        await _year_logic(event, ctx)
