from telethon import events

from kodzu_thon.services.gemini import GeminiError

HELP = [("ai {prompt}", "ask Gemini AI")]
COMMAND_PATTERNS = ["^ai "]


async def _ai_logic(event, ctx) -> None:
    prompt = event.message.text.removeprefix("ai ").strip()
    if not prompt:
        await event.edit("Please provide a prompt")
        return
    await event.edit("Loading...")
    try:
        result = await ctx.gemini.generate(prompt)
    except GeminiError as e:
        await event.edit(f"Error: {e}")
        return
    await event.edit(result)


def register(client, ctx) -> None:
    @client.on(events.NewMessage(pattern="^ai ", outgoing=True))
    async def _on_ai(event):
        await _ai_logic(event, ctx)
