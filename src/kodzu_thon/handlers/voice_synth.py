import sys

from telethon import events, types, utils

from kodzu_thon.speech.video import mount_video
from kodzu_thon.speech.voice import build_voice
from kodzu_thon.speech.waveform import get_waveform
from kodzu_thon.utils.files import safe_remove

HELP = [
    ("!a {text or [reply]}", "generate speech"),
    ("!v {text or [reply]}", "video speech"),
]
COMMAND_PATTERNS = ["^!a", "^!v"]


async def _voice_logic(event, client, ctx) -> None:
    try:
        chat = await event.get_chat()
        await event.delete()
        async with client.action(chat, "record-voice"):
            text = event.message.text.removeprefix("!a").strip()
            if event.message.is_reply and not text:
                msg = await event.message.get_reply_message()
                text = msg.text

            voice_path, duration = build_voice(
                text, media_dir=ctx.settings.media_dir, background=True
            )
            wf = get_waveform(0, 31, 100)
            await client.send_file(
                chat,
                voice_path,
                reply_to=event.message.reply_to_msg_id,
                attributes=[
                    types.DocumentAttributeAudio(
                        duration=duration,
                        voice=True,
                        waveform=utils.encode_waveform(bytes(wf)),
                    )
                ],
            )
            safe_remove(voice_path)
    except Exception as e:
        print(e, file=sys.stderr)


async def _video_logic(event, client, ctx) -> None:
    try:
        chat = await event.get_chat()
        await event.delete()
        async with client.action(chat, "record-round"):
            text = event.message.text.replace("!v ", "", 1)
            voice_path, _ = build_voice(text, media_dir=ctx.settings.media_dir)
            video_path = mount_video(voice_path)
            await client.send_file(
                chat,
                video_path,
                reply_to=event.message.reply_to_msg_id,
                video_note=True,
            )
            safe_remove(voice_path)
            safe_remove(video_path)
    except Exception as e:
        print(e, file=sys.stderr)


def register(client, ctx) -> None:
    @client.on(events.NewMessage(pattern="^!a", outgoing=True))
    async def _on_a(event):
        await _voice_logic(event, client, ctx)

    @client.on(events.NewMessage(pattern="^!v", outgoing=True))
    async def _on_v(event):
        await _video_logic(event, client, ctx)
