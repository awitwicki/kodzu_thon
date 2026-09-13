from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from kodzu_thon.web.repository import MessageFilters
from tests.unit.web.fake_repo import NOW

WARSAW = ZoneInfo("Europe/Warsaw")


def seed(fake_repo):
    fake_repo.add_chat(
        id=-100, title="Group <One>", type="supergroup", username="grp", photo_blob_id=42
    )
    fake_repo.add_chat(
        id=-200, title="Old chat", type="group", last_message_at=NOW - timedelta(days=1)
    )
    fake_repo.add_chat(id=-300, title="Empty", type="channel", last_message_at=None)
    fake_repo.add_user(id=7, first_name="Ann", last_name="Lee", username="ann", photo_blob_id=43)
    return fake_repo


async def test_requires_login(client):
    for path in ("/", "/chats/-100"):
        r = await client.get(path)
        assert r.status_code == 303 and r.headers["location"] == "/login"


async def test_chat_list(authed_client, fake_repo):
    seed(fake_repo)
    r = await authed_client.get("/")
    assert r.status_code == 200
    body = r.text
    assert "Group &lt;One&gt;" in body and "<script" not in body
    assert body.index("Group &lt;One&gt;") < body.index("Old chat") < body.index("Empty")
    assert 'href="/chats/-100"' in body and "/media/42" in body and "@grp" in body
    assert "no messages yet" in body
    assert 'name="csrf_token"' in body  # logout form in the layout


async def test_unknown_chat_is_404(authed_client, fake_repo):
    seed(fake_repo)
    assert (await authed_client.get("/chats/-999")).status_code == 404


async def test_timeline_renders_messages(authed_client, fake_repo):
    seed(fake_repo)
    fake_repo.add_message(
        chat_id=-100, id=1, text="hello <script>alert(1)</script> https://example.com/x"
    )
    fake_repo.add_message(
        chat_id=-100,
        id=2,
        text="gone",
        deleted_at=NOW,
        edit_count=2,
        is_outgoing=True,
        sender_user_id=None,
        sender_first_name=None,
        sender_last_name=None,
        sender_username=None,
    )
    fake_repo.add_message(
        chat_id=-100,
        id=3,
        text="re",
        reply_to_msg_id=1,
        reply_text="hello " * 40,
        reply_first_name="Ann",
        fwd_from_user_id=9,
        fwd_first_name="Bob",
        fwd_date=NOW,
    )
    r = await authed_client.get("/chats/-100")
    assert r.status_code == 200
    body = r.text
    assert body.index('id="m3"') < body.index('id="m2"') < body.index('id="m1"')  # newest first
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in body and "<script>" not in body
    assert '<a href="https://example.com/x" rel="noopener noreferrer">' in body
    assert 'href="/users/7">Ann Lee</a>' in body and "/media/43" in body
    assert 'class="msg deleted"' in body and "deleted at 2026-09-13 14:00" in body
    assert 'href="/chats/-100/messages/2"' in body and "edited (2)" in body
    assert 'class="badge">me</span>' in body
    assert "reply to Ann" in body and ("hello " * 40)[:120] in body and ("hello " * 40) not in body
    assert "forwarded from" in body and 'href="/users/9">Bob</a>' in body


async def test_timeline_media_rendering(authed_client, fake_repo):
    seed(fake_repo)
    fake_repo.add_message(
        chat_id=-100, id=1, media_type="photo", media_blob_id=5, media_meta={"media_id": 1}
    )
    fake_repo.add_message(
        chat_id=-100, id=2, media_type="video", media_blob_id=6, media_meta={"media_id": 2}
    )
    fake_repo.add_message(
        chat_id=-100, id=3, media_type="voice", media_blob_id=7, media_meta={"media_id": 3}
    )
    fake_repo.add_message(
        chat_id=-100,
        id=4,
        media_type="document",
        media_blob_id=8,
        media_size=2048,
        media_meta={"media_id": 4, "filename": "report final.pdf"},
    )
    fake_repo.add_message(
        chat_id=-100,
        id=5,
        media_type="video",
        media_size=9_000_000,
        media_meta={"media_id": 5, "skipped": "too_large"},
    )
    fake_repo.add_message(chat_id=-100, id=6, media_type="webpage", media_meta={"media_id": None})
    body = (await authed_client.get("/chats/-100")).text
    assert '<img src="/media/5"' in body
    assert '<video controls preload="metadata" src="/media/6">' in body
    assert '<audio controls preload="none" src="/media/7">' in body
    assert (
        'href="/media/8?filename=report%20final.pdf"' in body
        and "report final.pdf" in body
        and "2.0 KB" in body
    )
    assert "video: too_large (8.6 MB)" in body
    # photo renders two links (anchor + img), video/voice/document one each = 5,
    # plus every message shows sender 7's avatar (blob 43) = 6 more
    assert body.count("/media/") == 11


async def test_albums_are_grouped(authed_client, fake_repo):
    seed(fake_repo)
    for i in (1, 2, 3):
        fake_repo.add_message(
            chat_id=-100,
            id=i,
            grouped_id=77,
            media_type="photo",
            media_blob_id=10 + i,
            media_meta={"media_id": i},
            text="caption" if i == 1 else None,
        )
    fake_repo.add_message(chat_id=-100, id=4, text="separate")
    body = (await authed_client.get("/chats/-100")).text
    assert body.count("<article") == 2
    assert body.count('class="album"') == 1
    assert "caption" in body


async def test_pagination_and_limits(authed_client, fake_repo):
    seed(fake_repo)
    for i in range(1, 102):
        fake_repo.add_message(chat_id=-100, id=i, text=f"m{i}")
    r = await authed_client.get("/chats/-100")
    assert r.text.count("<article") == 100
    assert 'href="/chats/-100?before=2"' in r.text
    r = await authed_client.get("/chats/-100?before=2")
    assert r.text.count("<article") == 1 and "Older messages" not in r.text
    assert (await authed_client.get("/chats/-100?limit=200")).text.count("<article") == 101
    assert (await authed_client.get("/chats/-100?limit=201")).status_code == 422
    assert (await authed_client.get("/chats/-100?limit=0")).status_code == 422
    assert (await authed_client.get("/chats/-100?before=abc")).status_code == 422


async def test_filters_are_passed_to_repository_and_kept_in_links(authed_client, fake_repo):
    seed(fake_repo)
    for i in range(1, 103):  # every row satisfies every filter below, so paging kicks in
        fake_repo.add_message(
            chat_id=-100,
            id=i,
            text="hi",
            sender_user_id=7,
            deleted_at=NOW,
            edit_count=1,
            sent_at=datetime(2026, 9, 5, 12, tzinfo=UTC),
        )
    r = await authed_client.get(
        "/chats/-100?q=hi&from=7&deleted=1&edited=1&since=2026-09-01&until=2026-09-13&before=200"
    )
    assert r.status_code == 200
    name, kwargs = fake_repo.calls[-1]
    assert name == "chat_messages" and kwargs["before_id"] == 200 and kwargs["limit"] == 100
    assert kwargs["filters"] == MessageFilters(
        q="hi",
        sender_id=7,
        deleted_only=True,
        edited_only=True,
        since=datetime(2026, 9, 1, tzinfo=WARSAW),
        until=datetime(2026, 9, 13, tzinfo=WARSAW),
    )
    # the form shows the current values and the next link carries them, minus the old keyset
    assert 'name="q" maxlength="200" value="hi"' in r.text
    assert 'name="since" value="2026-09-01"' in r.text and "checked" in r.text
    assert (
        "q=hi&amp;from=7&amp;deleted=1&amp;edited=1&amp;since=2026-09-01&amp;until=2026-09-13&amp;before="
        in r.text
    )
    assert "before=200" not in r.text.split("Older messages")[0].rsplit("href=", 1)[-1]


async def test_nul_byte_in_query_is_stripped_before_reaching_repository(authed_client, fake_repo):
    """str.strip() does not remove NUL bytes, and PostgreSQL text columns reject them outright
    (asyncpg raises ValueError). parse_filters must strip \\x00 explicitly before the query
    ever reaches the repository/database."""
    seed(fake_repo)
    r = await authed_client.get("/chats/-100?q=%00hello")
    assert r.status_code == 200
    name, kwargs = fake_repo.calls[-1]
    assert name == "chat_messages"
    assert kwargs["filters"].q == "hello"
    assert "\x00" not in kwargs["filters"].q


async def test_invalid_filters_are_422(authed_client, fake_repo):
    seed(fake_repo)
    assert (await authed_client.get("/chats/-100?since=yesterday")).status_code == 422
    assert (await authed_client.get("/chats/-100?q=" + "x" * 201)).status_code == 422
    assert (await authed_client.get("/chats/-100?from=0")).status_code == 422
    assert (await authed_client.get("/chats/-100?deleted=2")).status_code == 422
