import re

import pytest
from telethon.tl import types

from kodzu_thon.services.message_extract import (
    DOWNLOADABLE_MEDIA_TYPES,
    ChatSnapshot,
    UserSnapshot,
    chat_snapshot,
    classify_media,
    extract_message,
    matches_command,
    user_snapshot,
)
from tests.factories import (
    NOW,
    make_channel,
    make_chat,
    make_document_media,
    make_message,
    make_photo_media,
    make_supergroup,
    make_user,
)

MAX = 5 * 1024 * 1024


def test_chat_snapshot_basic_group_uses_negative_id():
    snap = chat_snapshot(make_chat(id=99, title="Small"))
    assert snap == ChatSnapshot(id=-99, type="group", title="Small", username=None, photo_id=None)


def test_chat_snapshot_channel_and_supergroup():
    ch = chat_snapshot(make_channel(id=123, username="news", photo_id=555))
    assert ch.id == -1000000000123 and ch.type == "channel"
    assert ch.username == "news" and ch.photo_id == 555
    assert chat_snapshot(make_supergroup(id=124)).type == "supergroup"


def test_chat_snapshot_rejects_user():
    with pytest.raises(TypeError):
        chat_snapshot(make_user())


def test_user_snapshot():
    snap = user_snapshot(make_user(id=7, bot=True, photo_id=None), is_self=True)
    assert snap == UserSnapshot(
        id=7, first_name="Ann", last_name="Lee", username="ann", is_bot=True, is_self=True,
        photo_id=None,
    )


def test_extract_text_message_from_user_in_supergroup():
    msg = make_message(id=10, text="hello", reply_to=3, grouped_id=42)
    rec = extract_message(msg, make_supergroup(), make_user(), max_media_bytes=MAX)

    assert rec.chat.id == -1000000000124 and rec.chat.type == "supergroup"
    assert rec.sender_user.id == 7 and rec.sender_user.is_self is False
    assert rec.sender_chat is None
    assert rec.id == 10 and rec.text == "hello" and rec.sent_at == NOW
    assert rec.is_outgoing is False
    assert rec.reply_to_msg_id == 3 and rec.grouped_id == 42
    assert rec.media_type is None and rec.media_size is None and rec.media_meta is None
    assert rec.raw["_"] == "Message" and rec.raw["id"] == 10


def test_outgoing_message_marks_sender_as_self():
    rec = extract_message(make_message(out=True), make_supergroup(), make_user(), max_media_bytes=MAX)
    assert rec.is_outgoing is True and rec.sender_user.is_self is True


def test_channel_sender_becomes_sender_chat():
    chan = make_channel()
    rec = extract_message(make_message(), chan, chan, max_media_bytes=MAX)
    assert rec.sender_user is None
    assert rec.sender_chat.id == -1000000000123 and rec.sender_chat.type == "channel"


def test_unknown_sender_leaves_both_none():
    rec = extract_message(make_message(), make_supergroup(), None, max_media_bytes=MAX)
    assert rec.sender_user is None and rec.sender_chat is None


def test_empty_text_becomes_none():
    rec = extract_message(make_message(text=""), make_supergroup(), make_user(), max_media_bytes=MAX)
    assert rec.text is None


def test_forward_from_user_and_from_channel():
    fwd_user = types.MessageFwdHeader(date=NOW, from_id=types.PeerUser(5), from_name=None)
    rec = extract_message(make_message(fwd_from=fwd_user), make_supergroup(), make_user(), max_media_bytes=MAX)
    assert (rec.fwd_from_user_id, rec.fwd_from_chat_id, rec.fwd_date) == (5, None, NOW)

    fwd_chan = types.MessageFwdHeader(date=NOW, from_id=types.PeerChannel(77), from_name="hidden")
    rec = extract_message(make_message(fwd_from=fwd_chan), make_supergroup(), make_user(), max_media_bytes=MAX)
    assert (rec.fwd_from_user_id, rec.fwd_from_chat_id) == (None, -1000000000077)
    assert rec.fwd_from_name == "hidden"


def test_photo_media_meta():
    msg = make_message(media=make_photo_media(photo_id=1000, size=4000, w=100, h=80))
    rec = extract_message(msg, make_supergroup(), make_user(), max_media_bytes=MAX)
    assert rec.media_type == "photo" and rec.media_size == 4000
    assert rec.media_meta == {
        "media_id": 1000, "mime": "image/jpeg", "filename": None, "width": 100, "height": 80,
        "duration": None, "skipped": None,
    }


def test_media_over_limit_is_marked_too_large():
    msg = make_message(media=make_photo_media(size=MAX + 1))
    rec = extract_message(msg, make_supergroup(), make_user(), max_media_bytes=MAX)
    assert rec.media_meta["skipped"] == "too_large" and rec.media_size == MAX + 1


def test_media_without_size_is_marked_no_size():
    msg = make_message(media=make_document_media(size=None))
    rec = extract_message(msg, make_supergroup(), make_user(), max_media_bytes=MAX)
    assert rec.media_type == "document" and rec.media_size is None
    assert rec.media_meta["skipped"] == "no_size" and rec.media_meta["filename"] == "a.pdf"


def test_classify_media_covers_every_kind():
    def doc(mime, *attrs):
        return make_document_media(mime=mime, attributes=list(attrs))

    video = types.DocumentAttributeVideo(duration=3.0, w=10, h=10)
    cases = {
        "sticker": doc("image/webp", types.DocumentAttributeSticker(alt="x", stickerset=types.InputStickerSetEmpty())),
        "gif": doc("video/mp4", types.DocumentAttributeAnimated(), video),
        "video_note": doc("video/mp4", types.DocumentAttributeVideo(duration=3.0, w=10, h=10, round_message=True)),
        "voice": doc("audio/ogg", types.DocumentAttributeAudio(duration=2, voice=True)),
        "audio": doc("audio/mpeg", types.DocumentAttributeAudio(duration=2)),
        "video": doc("video/mp4", video),
        "photo": make_photo_media(),
        "document": doc("application/pdf", types.DocumentAttributeFilename(file_name="a.pdf")),
        "webpage": types.MessageMediaWebPage(webpage=types.WebPageEmpty(id=1)),
        "other": types.MessageMediaPoll(
            poll=types.Poll(id=1, question=types.TextWithEntities(text="q", entities=[]), answers=[]),
            results=types.PollResults(),
        ),
    }
    for expected, media in cases.items():
        assert classify_media(make_message(media=media)) == expected, expected
    assert classify_media(make_message()) is None
    assert {
        "photo", "video", "document", "voice", "audio", "sticker", "gif", "video_note"
    } == DOWNLOADABLE_MEDIA_TYPES


def test_non_downloadable_media_has_meta_without_file_fields():
    msg = make_message(media=types.MessageMediaWebPage(webpage=types.WebPageEmpty(id=1)))
    rec = extract_message(msg, make_supergroup(), make_user(), max_media_bytes=MAX)
    assert rec.media_type == "webpage" and rec.media_size is None
    assert rec.media_meta["media_id"] is None and rec.media_meta["skipped"] is None


def test_matches_command():
    patterns = [re.compile("^ppo$"), re.compile(r"^tr$", re.IGNORECASE)]
    assert matches_command("ppo", patterns)
    assert matches_command("TR", patterns)
    assert not matches_command("ppo now", patterns)
    assert not matches_command("", patterns)
