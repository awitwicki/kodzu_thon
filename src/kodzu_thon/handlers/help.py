from telethon import events

HELP = [("!h", "show this help")]


async def _help_logic(event, ctx) -> None:
    lines = [f"**Kodzuthon help** `{ctx.settings.version}`", ""]
    for label, desc in ctx.help_lines:
        lines.append(f"`{label}` - {desc},")
    if lines and lines[-1].endswith(","):
        lines[-1] = lines[-1].rstrip(",") + "."
    lines.append("")
    lines.append("[github](https://github.com/awitwicki/kodzu_thon)")
    await event.edit("\n".join(lines))


def register(client, ctx) -> None:
    @client.on(events.NewMessage(pattern="^!h$", outgoing=True))
    async def _on_help(event):
        await _help_logic(event, ctx)
