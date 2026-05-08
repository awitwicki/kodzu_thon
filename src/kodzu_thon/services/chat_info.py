import sys
from time import sleep

from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import (
    ChannelParticipantCreator,
    ChannelParticipantsAdmins,
    ChannelParticipantsSearch,
    ChatParticipantCreator,
)


def _is_channel(chat) -> bool:
    return type(chat).__name__ == "Channel"


async def build_message_chat_info(event, client) -> str:
    try:
        reply_msg = await event.message.get_reply_message()

        if reply_msg:
            sender = reply_msg.sender
            user_name = "@" + sender.username if sender.username else sender.username
            first_name = sender.first_name or ""
            last_name = sender.last_name or ""
            full_name = f"{first_name} {last_name}".strip()

            return (
                "┌ Scan info:\n"
                f"├ Username: {user_name}\n"
                f"├ User id: {sender.id}\n"
                f"├ Full name: {full_name}\n"
                f"├ Chat id: {event.chat_id}\n"
                f"└ Message id: {event._message_id}"
            )

        chat = await event.get_chat()
        if not _is_channel(chat):
            return "Scan only chats"

        chat_user_name = "@" + chat.username if chat.username else chat.username
        owner_id = owner_user_name = owner_full_name = ""

        try:
            admins = await client.get_participants(chat, filter=ChannelParticipantsAdmins)
            creator = next(
                (
                    a
                    for a in admins
                    if isinstance(
                        a.participant, (ChatParticipantCreator, ChannelParticipantCreator)
                    )
                ),
                None,
            )
            if creator is not None:
                owner_id = creator.id
                owner_user_name = "@" + creator.username if creator.username else creator.username
                owner_full_name = f"{creator.first_name or ''} {creator.last_name or ''}".strip()
        except Exception as e:
            print(e, file=sys.stderr)

        return (
            "┌ Scan info:\n"
            f"├ Chat username: {chat_user_name}\n"
            f"├ Chat title: {chat.title}\n"
            f"├ Chat id: {chat.id}\n"
            f"├ Creation date: {chat.date}\n"
            f"├ Owner id: {owner_id}\n"
            f"├ Owner Username: {owner_user_name}\n"
            f"└ Owner Full name: {owner_full_name}\n"
        )

    except Exception as e:
        print(e, file=sys.stderr)
        return f"ERROR!\n\n{e}"


async def scrap_chat_users(event, client) -> tuple[bool, str]:
    try:
        chat = await event.get_chat()
        path = f"{chat.title}_{chat.id}_members.csv"

        offset, limit = 0, 100
        all_users = []
        while True:
            participants = await client(
                GetParticipantsRequest(chat, ChannelParticipantsSearch(""), offset, limit, hash=0)
            )
            if not participants.users:
                break
            all_users.extend(participants.users)
            offset += len(participants.users)
            sleep(1)

        with open(path, "w", encoding="utf8") as f:
            f.write("user_id,user_name")
            for p in all_users:
                try:
                    line = f"{p.id},{p.title}"
                except AttributeError:
                    line = f"{p.id},{p.first_name} {p.last_name}"
                f.write(f"{line}\n")

        return True, path
    except Exception as e:
        print(e, file=sys.stderr)
        return False, f"ERROR!\n\n{e}"
