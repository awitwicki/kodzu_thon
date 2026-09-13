"""Pure conversions from Telethon objects to the records the message store writes.
No I/O here; everything is unit-testable with plain TL objects."""

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from telethon import utils
from telethon.tl import types

DOWNLOADABLE_MEDIA_TYPES = frozenset(
    {"photo", "video", "document", "voice", "audio", "sticker", "gif", "video_note"}
)


@dataclass(frozen=True)
class ChatSnapshot:
    id: int
    type: str  # 'group' | 'supergroup' | 'channel'
    title: str | None
    username: str | None
    photo_id: int | None


@dataclass(frozen=True)
class UserSnapshot:
    id: int
    first_name: str | None
    last_name: str | None
    username: str | None
    is_bot: bool
    is_self: bool
    photo_id: int | None


@dataclass(frozen=True)
class MessageRecord:
    chat: ChatSnapshot
    sender_user: UserSnapshot | None
    sender_chat: ChatSnapshot | None
    id: int
    is_outgoing: bool
    sent_at: datetime
    text: str | None
    reply_to_msg_id: int | None
    grouped_id: int | None
    fwd_from_user_id: int | None
    fwd_from_chat_id: int | None
    fwd_from_name: str | None
    fwd_date: datetime | None
    media_type: str | None
    media_size: int | None
    media_meta: dict[str, Any] | None
    raw: dict[str, Any]


@dataclass(frozen=True)
class EditRecord:
    message: MessageRecord
    edited_at: datetime


@dataclass(frozen=True)
class DeletionRecord:
    chat_id: int | None  # None for basic groups: Telegram does not say which chat
    message_ids: tuple[int, ...]
    observed_at: datetime


@dataclass(frozen=True)
class MediaSkipped:
    chat_id: int
    message_id: int
    media_id: int
    reason: str


@dataclass(frozen=True)
class MessageTarget:
    chat_id: int
    message_id: int
    media_id: int


@dataclass(frozen=True)
class UserPhotoTarget:
    user_id: int
    photo_id: int


@dataclass(frozen=True)
class ChatPhotoTarget:
    chat_id: int
    photo_id: int


@dataclass(frozen=True)
class BlobRecord:
    target: MessageTarget | UserPhotoTarget | ChatPhotoTarget
    sha256: bytes
    mime_type: str
    data: bytes


def _photo_id(photo: Any) -> int | None:
    return getattr(photo, "photo_id", None)


def chat_snapshot(entity: Any) -> ChatSnapshot:
    if isinstance(entity, types.Chat):
        chat_type = "group"
    elif isinstance(entity, types.Channel):
        chat_type = "channel" if entity.broadcast else "supergroup"
    else:
        raise TypeError(f"not a chat entity: {type(entity).__name__}")
    return ChatSnapshot(
        id=utils.get_peer_id(entity),
        type=chat_type,
        title=entity.title,
        username=getattr(entity, "username", None),
        photo_id=_photo_id(entity.photo),
    )


def user_snapshot(user: types.User, *, is_self: bool) -> UserSnapshot:
    return UserSnapshot(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        is_bot=bool(user.bot),
        is_self=is_self,
        photo_id=_photo_id(user.photo),
    )


def classify_media(message: Any) -> str | None:
    media = message.media
    if media is None:
        return None
    # Web previews first: their photo/document would otherwise match below.
    if isinstance(media, types.MessageMediaWebPage):
        return "webpage"
    if message.sticker:
        return "sticker"
    if message.gif:
        return "gif"
    if message.video_note:
        return "video_note"
    if message.voice:
        return "voice"
    if message.audio:
        return "audio"
    if message.video:
        return "video"
    if message.photo:
        return "photo"
    if message.document:
        return "document"
    return "other"


def _media_fields(
    message: Any, media_type: str | None, max_media_bytes: int
) -> tuple[int | None, dict[str, Any] | None]:
    if media_type is None:
        return None, None
    meta: dict[str, Any] = {
        "media_id": None, "mime": None, "filename": None, "width": None, "height": None,
        "duration": None, "skipped": None,
    }
    if media_type not in DOWNLOADABLE_MEDIA_TYPES:
        return None, meta
    f = message.file
    size = f.size
    if size is None:
        meta["skipped"] = "no_size"
    elif size > max_media_bytes:
        meta["skipped"] = "too_large"
    meta.update(
        media_id=getattr(f.media, "id", None), mime=f.mime_type, filename=f.name,
        width=f.width, height=f.height, duration=f.duration,
    )
    return size, meta


def _forward_fields(
    fwd: types.MessageFwdHeader | None,
) -> tuple[int | None, int | None, str | None, datetime | None]:
    if fwd is None:
        return None, None, None, None
    user_id = chat_id = None
    if isinstance(fwd.from_id, types.PeerUser):
        user_id = fwd.from_id.user_id
    elif isinstance(fwd.from_id, types.PeerChannel | types.PeerChat):
        chat_id = utils.get_peer_id(fwd.from_id)
    return user_id, chat_id, fwd.from_name, fwd.date


def extract_message(message: Any, chat: Any, sender: Any, *, max_media_bytes: int) -> MessageRecord:
    sender_user = sender_chat = None
    if isinstance(sender, types.User):
        sender_user = user_snapshot(sender, is_self=bool(message.out))
    elif isinstance(sender, types.Channel | types.Chat):
        sender_chat = chat_snapshot(sender)

    media_type = classify_media(message)
    media_size, media_meta = _media_fields(message, media_type, max_media_bytes)
    fwd_user_id, fwd_chat_id, fwd_name, fwd_date = _forward_fields(message.fwd_from)

    return MessageRecord(
        chat=chat_snapshot(chat),
        sender_user=sender_user,
        sender_chat=sender_chat,
        id=message.id,
        is_outgoing=bool(message.out),
        sent_at=message.date,
        text=message.message or None,
        reply_to_msg_id=message.reply_to_msg_id,
        grouped_id=message.grouped_id,
        fwd_from_user_id=fwd_user_id,
        fwd_from_chat_id=fwd_chat_id,
        fwd_from_name=fwd_name,
        fwd_date=fwd_date,
        media_type=media_type,
        media_size=media_size,
        media_meta=media_meta,
        raw=json.loads(message.to_json()),
    )


def matches_command(text: str, patterns: list[re.Pattern]) -> bool:
    return any(p.match(text) for p in patterns)
