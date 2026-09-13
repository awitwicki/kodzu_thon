import sys

from telethon import events

HELP = [
    ("хня [optional reply]", "bredor video"),
    ("ніх [optional reply]", "damn video"),
]
COMMAND_PATTERNS = ["^хня$", "^ніх$"]


async def _send_meme(event, client, media_path: str) -> None:
    try:
        chat = await event.get_chat()
        await event.delete()
        async with client.action(chat, "record-round"):
            await client.send_file(
                chat, media_path, reply_to=event.message.reply_to_msg_id, video_note=True
            )
    except Exception as e:
        print(e, file=sys.stderr)


def register(client, ctx) -> None:
    @client.on(events.NewMessage(pattern="^хня$", outgoing=True))
    async def _on_hnya(event):
        await _send_meme(event, client, "media/same.mp4")

    @client.on(events.NewMessage(pattern="^ніх$", outgoing=True))
    async def _on_nih(event):
        await _send_meme(event, client, "media/nih.mp4")
