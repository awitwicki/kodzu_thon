import asyncio
import io
import sys
import zlib

from telethon import events, types
from telethon.utils import get_display_name

from kodzu_thon.services.quote_sticker import (
    MAX_IMAGE_BYTES,
    ImageTooLarge,
    QuoteInput,
    render_image,
    render_quote,
)

HELP = [("!st [reply]", "make a webp sticker from the message (text quote or image)")]
COMMAND_PATTERNS = ["^!st$"]


def _is_image(msg) -> bool:
    if msg.photo:
        return True
    doc = msg.document
    return bool(doc and not msg.sticker and (doc.mime_type or "").startswith("image/"))


async def _author(msg):
    """The person shown on the quote: the original author for forwards."""
    fwd = msg.forward
    if fwd is not None:
        sender = fwd.sender or fwd.chat
        if sender is not None:
            return get_display_name(sender), sender
        if fwd.from_name:
            return fwd.from_name, None
    sender = await msg.get_sender()
    return (get_display_name(sender) if sender else ""), sender


async def _quote_sticker(client, msg) -> bytes | None:
    if _is_image(msg):
        size = msg.file.size if msg.file else None
        if size is None or size > MAX_IMAGE_BYTES:
            raise ImageTooLarge("image is too large")
        data = await msg.download_media(file=bytes)
        return await asyncio.to_thread(render_image, data) if data else None

    if not msg.raw_text:
        return None

    name, sender = await _author(msg)
    avatar = None
    if sender is not None:
        try:
            avatar = await client.download_profile_photo(sender, file=bytes)
        except Exception as e:  # no avatar is fine, initials are drawn
            print(f"sticker: avatar download failed: {e}", file=sys.stderr)
    seed = getattr(sender, "id", None) or zlib.crc32(name.encode())
    quote = QuoteInput(name=name, text=msg.raw_text, color_seed=seed, avatar=avatar)
    return await asyncio.to_thread(render_quote, quote)


async def _sticker_logic(event, client) -> None:
    if not event.message.is_reply:
        await event.edit("Reply to a message to make a sticker")
        return
    msg = await event.message.get_reply_message()
    if msg is None:
        await event.edit("Can't load the replied message")
        return

    try:
        webp = await _quote_sticker(client, msg)
    except Exception as e:
        print(f"sticker: render failed: {e}", file=sys.stderr)
        await event.edit(f"Sticker error: {e}")
        return
    if webp is None:
        await event.edit("Nothing to make a sticker from")
        return

    file = io.BytesIO(webp)
    file.name = "sticker.webp"
    chat = await event.get_chat()
    await event.delete()
    await client.send_file(
        chat,
        file,
        reply_to=msg.id,
        mime_type="image/webp",
        attributes=[
            types.DocumentAttributeSticker(alt="💬", stickerset=types.InputStickerSetEmpty())
        ],
    )


def register(client, ctx) -> None:
    @client.on(events.NewMessage(pattern="^!st$", outgoing=True))
    async def _on_sticker(event):
        await _sticker_logic(event, client)
