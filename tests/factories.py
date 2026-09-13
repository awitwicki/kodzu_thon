"""Real Telethon TL objects for tests (no network, no client needed)."""

import datetime as dt

from telethon.tl import types

NOW = dt.datetime(2026, 9, 13, 12, 0, tzinfo=dt.UTC)


def make_user(id=7, first_name="Ann", last_name="Lee", username="ann", bot=False, photo_id=777):
    photo = types.UserProfilePhoto(photo_id=photo_id, dc_id=2) if photo_id else None
    return types.User(
        id=id, first_name=first_name, last_name=last_name, username=username, bot=bot, photo=photo
    )


def make_channel(id=123, title="Chan", username=None, broadcast=True, megagroup=False, photo_id=555):
    photo = types.ChatPhoto(photo_id=photo_id, dc_id=2) if photo_id else types.ChatPhotoEmpty()
    return types.Channel(
        id=id, title=title, photo=photo, date=NOW, broadcast=broadcast, megagroup=megagroup,
        username=username,
    )


def make_supergroup(id=124, title="Grp", **kw):
    return make_channel(id=id, title=title, broadcast=False, megagroup=True, **kw)


def make_chat(id=99, title="Small", photo_id=None):
    photo = types.ChatPhoto(photo_id=photo_id, dc_id=2) if photo_id else types.ChatPhotoEmpty()
    return types.Chat(id=id, title=title, photo=photo, participants_count=3, date=NOW, version=1)


def make_photo_media(photo_id=1000, size=4000, w=100, h=80):
    return types.MessageMediaPhoto(
        photo=types.Photo(
            id=photo_id, access_hash=1, file_reference=b"\x01", date=NOW,
            sizes=[types.PhotoSize(type="x", w=w, h=h, size=size)], dc_id=2,
        )
    )


def make_document_media(doc_id=2000, mime="application/pdf", size=1234, attributes=None):
    return types.MessageMediaDocument(
        document=types.Document(
            id=doc_id, access_hash=1, file_reference=b"", date=NOW, mime_type=mime, size=size,
            dc_id=2, attributes=attributes or [types.DocumentAttributeFilename(file_name="a.pdf")],
        )
    )


def make_message(
    id=1, peer=None, text="hi", out=False, media=None, fwd_from=None, grouped_id=None,
    reply_to=None, edit_date=None, from_id=None,
):
    reply = types.MessageReplyHeader(reply_to_msg_id=reply_to) if reply_to else None
    return types.Message(
        id=id, peer_id=peer or types.PeerChannel(123), date=NOW, message=text, out=out,
        media=media, fwd_from=fwd_from, grouped_id=grouped_id, reply_to=reply,
        edit_date=edit_date, from_id=from_id,
    )
