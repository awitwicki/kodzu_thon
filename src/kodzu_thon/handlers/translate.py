import re

from telethon import events

from kodzu_thon.services.whisper import WhisperError
from kodzu_thon.utils.files import safe_remove

HELP = [("tr [reply]", "translate message, OR transcrybe voice or video note")]


async def _tr_logic(event, ctx) -> None:
    if not event.message.is_reply:
        return
    msg = await event.message.get_reply_message()

    if msg.voice or msg.video_note:
        await event.edit("Transcrybing...")
        path = await msg.download_media()
        try:
            text = await ctx.whisper.transcribe(path)
            await event.edit(text)
        except WhisperError as e:
            await event.edit(f"Transcrybing error: {e}")
        finally:
            safe_remove(path)
        return

    if msg.text:
        await event.edit("Translating...")
        result = await ctx.translator.translate(msg.text, dest="uk")
        await event.edit(result)


def register(client, ctx) -> None:
    @client.on(events.NewMessage(pattern=re.compile(r"^tr$", re.IGNORECASE), outgoing=True))
    async def _on_tr(event):
        await _tr_logic(event, ctx)
