import datetime

from telethon import events, types, utils

from kodzu_thon.speech.merge import merge_with_background
from kodzu_thon.speech.waveform import get_waveform
from kodzu_thon.utils.files import safe_remove


async def _bg_voice_logic(event, client, ctx) -> None:
    if not event.voice:
        return
    media_date = event.message.file.media.date
    now = datetime.datetime.now(media_date.tzinfo)
    if (now - media_date).seconds >= 60:
        return

    chat = await event.get_chat()
    await event.delete()
    async with client.action(chat, "record-voice"):
        path = await event.download_media()
        merged, duration = merge_with_background(path)
        wf = get_waveform(0, 31, 100)
        await client.send_file(
            chat,
            merged,
            reply_to=event.message.reply_to_msg_id,
            attributes=[
                types.DocumentAttributeAudio(
                    duration=duration,
                    voice=True,
                    waveform=utils.encode_waveform(bytes(wf)),
                )
            ],
        )
        safe_remove(merged)


def register(client, ctx) -> None:
    @client.on(events.NewMessage(outgoing=True, forwards=False))
    async def _on_outgoing(event):
        await _bg_voice_logic(event, client, ctx)
