from dataclasses import dataclass


@dataclass(frozen=True)
class CachedMessage:
    chat_id: int
    message_id: int
    sender_id: int
    sender_name: str
    chat_title: str
    text: str


class MessageCache:
    def __init__(self) -> None:
        self._chats: dict[int, dict[int, CachedMessage]] = {}

    def add(
        self,
        chat_id: int,
        message_id: int,
        sender_id: int,
        sender_name: str,
        chat_title: str,
        text: str,
    ) -> None:
        chat = self._chats.setdefault(chat_id, {})
        chat[message_id] = CachedMessage(
            chat_id=chat_id,
            message_id=message_id,
            sender_id=sender_id,
            sender_name=sender_name,
            chat_title=chat_title,
            text=text,
        )

    def get(self, chat_id: int, message_id: int) -> CachedMessage | None:
        chat = self._chats.get(chat_id)
        if chat is None:
            return None
        return chat.get(message_id)
