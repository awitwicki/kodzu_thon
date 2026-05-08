from telethon import events

from kodzu_thon.services.chat_info import build_message_chat_info, scrap_chat_users
from kodzu_thon.utils.files import safe_remove

HELP = [
    ("scan [optional reply]", "scan message or chat"),
    ("scans [optional reply]", "silently scan message or chat"),
    ("scraps (chat)", "silently scrap all members to .csv"),
]


async def _scan_logic(event, client, ctx) -> None:
    text = await build_message_chat_info(event, client)
    await event.edit(text)


async def _scans_logic(event, client, ctx) -> None:
    text = await build_message_chat_info(event, client)
    await event.delete()
    await client.send_message("me", text)


async def _scraps_logic(event, client, ctx) -> None:
    await event.delete()
    msg = await client.send_message("me", "Scrapping...")
    ok, csv_or_err = await scrap_chat_users(event, client)
    if ok:
        await msg.delete()
        await client.send_file("me", csv_or_err, caption=csv_or_err)
        safe_remove(csv_or_err)
    else:
        await msg.edit(csv_or_err)


def register(client, ctx) -> None:
    @client.on(events.NewMessage(pattern="^scan$", outgoing=True))
    async def _on_scan(event):
        await _scan_logic(event, client, ctx)

    @client.on(events.NewMessage(pattern="^scans$", outgoing=True))
    async def _on_scans(event):
        await _scans_logic(event, client, ctx)

    @client.on(events.NewMessage(pattern="^scraps$", outgoing=True))
    async def _on_scraps(event):
        await _scraps_logic(event, client, ctx)
