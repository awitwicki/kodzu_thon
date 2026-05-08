from telethon import events

HELP = [("summ [reply]", "summarize messages from replied to newest")]
_MAX_MESSAGES = 1000
_PROMPT_TEMPLATE = (
    "Please provide a concise brief summary of the following messages "
    "in ukrainian language:\n\n{body}"
)


async def _summarize_logic(event, client, ctx) -> None:
    if not event.message.is_reply:
        await event.edit("Reply to a message to summarize from")
        return

    chat = await event.get_chat()
    reply = await event.message.get_reply_message()
    await event.edit("Collecting messages...")

    texts: list[str] = []
    async for msg in client.iter_messages(chat, min_id=reply.id - 1):
        if len(texts) >= _MAX_MESSAGES:
            break
        if msg.text:
            texts.append(msg.text)

    if not texts:
        await event.edit("No messages found to summarize")
        return

    await event.edit(f"Summarizing {len(texts)} messages...")
    texts.reverse()
    body = "\n---\n".join(texts)

    try:
        result = await ctx.gemini.generate(_PROMPT_TEMPLATE.format(body=body))
    except Exception as e:
        await event.edit(f"Error: {e}")
        return

    await event.edit(f"**Summary ({len(texts)} messages):**\n\n{result}")


def register(client, ctx) -> None:
    @client.on(events.NewMessage(pattern="^summ$", outgoing=True))
    async def _on_summ(event):
        await _summarize_logic(event, client, ctx)
