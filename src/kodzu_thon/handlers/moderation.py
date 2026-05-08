import datetime
import sys

from telethon import events
from telethon.tl.functions.channels import EditBannedRequest
from telethon.tl.types import ChatBannedRights

HELP = [("!m {20} {m/h/d}", "mute someone for {20} {m} - minutes")]
_UNIT_TO_SECS = {"m": (60, "minuts"), "h": (3600, "ours"), "d": (86400, "deys")}


async def _mute_logic(event, client, ctx) -> None:
    reply = await event.get_reply_message()
    if not reply:
        await event.delete()
        return

    try:
        unit = event.message.text[-1]
        count = int(event.message.text.split()[1][:-1])
        seconds, label = _UNIT_TO_SECS[unit]
        until = datetime.datetime.utcnow() + datetime.timedelta(seconds=count * seconds)

        chat = await event.get_chat()
        rights = ChatBannedRights(until_date=until, send_messages=True)
        request = EditBannedRequest(chat.id, reply.sender_id, rights)
        await client(request)
        await event.edit(f"Muted for {count} {label}")
    except Exception as e:
        print(e, file=sys.stderr)


def register(client, ctx) -> None:
    @client.on(events.NewMessage(pattern=r"^!m", outgoing=True))
    async def _on_m(event):
        await _mute_logic(event, client, ctx)
