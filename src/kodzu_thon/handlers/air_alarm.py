import asyncio
import sys

from telethon import events

from kodzu_thon.utils.files import safe_remove

HELP = [("ppo [optional reply]", "PPO map")]


def _build_caption(alarms: dict[str, bool]) -> str:
    text = "Повітряна тривога в областях:\n\n"
    for name, on in alarms.items():
        if on:
            text += f"{name} ⚠️\n"
    text += "\nair-save.ops.ajax.systems"
    return text


async def _ppo_logic(event, client, ctx) -> None:
    await event.edit("Loading...")
    try:
        alarms = await asyncio.to_thread(ctx.air_alarm.fetch_alarms)
        path = await asyncio.to_thread(ctx.air_alarm.render, alarms)
    except Exception as e:
        print(e, file=sys.stderr)
        await event.edit("Fail")
        return

    chat = await event.get_chat()
    await event.delete()
    await client.send_file(
        chat, path, caption=_build_caption(alarms), reply_to=event.message.reply_to_msg_id
    )
    safe_remove(path)


def register(client, ctx) -> None:
    @client.on(events.NewMessage(pattern="^ppo$", outgoing=True))
    async def _on_ppo(event):
        await _ppo_logic(event, client, ctx)
