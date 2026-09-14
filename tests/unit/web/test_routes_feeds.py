from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from kodzu_thon.web.repository import MessageFilters
from tests.unit.web.fake_repo import NOW

WARSAW = ZoneInfo("Europe/Warsaw")


def seed(fake_repo):
    fake_repo.add_chat(id=-100, title="Grp", type="supergroup")
    fake_repo.add_chat(id=-200, title="Other", type="group")
    fake_repo.add_user(
        id=7, first_name="Ann", last_name="Lee", username="ann", is_bot=False, photo_blob_id=43
    )
    fake_repo.add_name_history(
        7, first_name="Anna", username="anna_old", seen_at=NOW - timedelta(days=3)
    )
    fake_repo.add_name_history(7, first_name="Ann", username="ann", seen_at=NOW - timedelta(days=1))
    fake_repo.add_message(
        chat_id=-100,
        id=1,
        text="first <b>",
        sent_at=NOW - timedelta(hours=3),
        edit_count=1,
        edited_at=NOW,
    )
    fake_repo.add_message(
        chat_id=-100,
        id=2,
        text="second",
        sent_at=NOW - timedelta(hours=2),
        deleted_at=NOW - timedelta(hours=1),
    )
    fake_repo.add_message(
        chat_id=-200, id=5, text="third", sent_at=NOW - timedelta(hours=1), deleted_at=NOW
    )
    fake_repo.add_edit(-100, 1, old_text="draft <i>", edited_at=NOW - timedelta(minutes=30))
    return fake_repo


async def test_requires_login(client):
    for path in ("/chats/-100/messages/1", "/users/7", "/deleted", "/search?q=x"):
        r = await client.get(path)
        assert r.status_code == 303 and r.headers["location"] == "/login"


async def test_permalink_shows_history_and_raw(authed_client, fake_repo):
    seed(fake_repo)
    assert (await authed_client.get("/chats/-100/messages/99")).status_code == 404
    r = await authed_client.get("/chats/-100/messages/1")
    assert r.status_code == 200
    body = r.text
    assert 'id="m1"' in body and "first &lt;b&gt;" in body
    assert "Edit history (1 previous version)" in body and "draft &lt;i&gt;" in body
    assert "until 2026-09-13 13:30" in body
    assert "Raw message JSON" in body and "<pre>{}</pre>" in body
    assert 'href="/chats/-100">Grp</a>' in body


async def test_user_profile(authed_client, fake_repo):
    seed(fake_repo)
    assert (await authed_client.get("/users/404")).status_code == 404
    r = await authed_client.get("/users/7")
    assert r.status_code == 200
    body = r.text
    assert "<h1>Ann Lee" in body and "@ann" in body and "/media/43" in body
    assert "Name history" in body and "Anna" in body and "@anna_old" in body
    assert body.index("2026-09-12 14:00") < body.index("2026-09-10 14:00")  # history newest first
    assert 'href="/chats/-100">Grp</a>' in body and "2 messages" in body
    assert 'href="/chats/-200">Other</a>' in body and "1 messages" in body
    # messages newest first, each labelled with its chat
    assert body.index('id="m5"') < body.index('id="m2"') < body.index('id="m1"')
    assert 'in <a href="/chats/-200">Other</a>' in body
    assert '<option value="-100">Grp</option>' in body and '<option value="-200">Other</option>' in body
    name, kwargs = fake_repo.calls[-1]
    assert name == "user_messages" and kwargs["user_id"] == 7 and kwargs["before"] is None


async def test_user_profile_filters_by_chat_id(authed_client, fake_repo):
    seed(fake_repo)
    r = await authed_client.get("/users/7?chat=-200")
    assert r.status_code == 200
    body = r.text
    assert body.count("<article") == 1 and 'id="m5"' in body
    assert '<option value="-200" selected>Other</option>' in body
    kwargs = fake_repo.calls[-1][1]
    assert kwargs["filters"] == MessageFilters(chat_id=-200)


async def test_user_messages_keyset_links(authed_client, fake_repo):
    seed(fake_repo)
    for i in range(10, 112):
        fake_repo.add_message(chat_id=-100, id=i, text="x", sent_at=NOW + timedelta(seconds=i))
    r = await authed_client.get("/users/7?limit=100")
    assert r.text.count("<article") == 100
    last_ts = (NOW + timedelta(seconds=12)).isoformat()
    assert f"before_ts={last_ts.replace('+', '%2B').replace(':', '%3A')}&amp;before_id=12" in r.text
    r2 = await authed_client.get(
        "/users/7", params={"limit": 100, "before_ts": last_ts, "before_id": 12}
    )
    assert r2.status_code == 200
    assert fake_repo.calls[-1][1]["before"] == (NOW + timedelta(seconds=12), 12)


async def test_deleted_feed(authed_client, fake_repo):
    seed(fake_repo)
    r = await authed_client.get("/deleted")
    assert r.status_code == 200
    body = r.text
    assert body.count("<article") == 2
    assert body.index('id="m5"') < body.index('id="m2"')  # by deleted_at desc
    assert (
        'in <a href="/chats/-100">Grp</a>' in body and 'in <a href="/chats/-200">Other</a>' in body
    )
    assert 'name="since"' not in body  # compact hides since/until/checkboxes
    assert '<option value="-100">Grp</option>' in body and '<option value="-200">Other</option>' in body
    assert fake_repo.calls[-1] == (
        "deleted_messages",
        {"before": None, "limit": 100, "filters": MessageFilters()},
    )


async def test_deleted_feed_keyset_and_filters(authed_client, fake_repo):
    seed(fake_repo)
    for i in range(10, 112):
        fake_repo.add_message(
            chat_id=-100, id=i, text="gone", deleted_at=NOW + timedelta(seconds=i)
        )
    r = await authed_client.get("/deleted?q=gone&from=7")
    assert r.text.count("<article") == 100
    assert "before_ts=" in r.text and "before_id=12" in r.text
    kwargs = fake_repo.calls[-1][1]
    assert kwargs["filters"] == MessageFilters(q="gone", sender_id=7)
    assert (
        await authed_client.get("/deleted?before_ts=2026-09-13T12:00:00%2B00:00")
    ).status_code == 422
    assert (await authed_client.get("/deleted?before_id=5")).status_code == 422
    assert (
        await authed_client.get("/deleted?before_ts=2026-09-13T12:00:00&before_id=5")
    ).status_code == 422
    assert (await authed_client.get("/deleted?chat=abc")).status_code == 422


async def test_deleted_feed_filters_by_chat_id(authed_client, fake_repo):
    seed(fake_repo)
    r = await authed_client.get("/deleted?chat=-200")
    assert r.status_code == 200
    body = r.text
    assert body.count("<article") == 1 and 'id="m5"' in body
    assert '<option value="-200" selected>Other</option>' in body
    kwargs = fake_repo.calls[-1][1]
    assert kwargs["filters"] == MessageFilters(chat_id=-200)


async def test_search(authed_client, fake_repo):
    seed(fake_repo)
    assert (await authed_client.get("/search")).status_code == 422
    assert (await authed_client.get("/search?q=")).status_code == 422
    r = await authed_client.get("/search?q=ir&deleted=1&since=2026-09-01")
    assert r.status_code == 200
    body = r.text
    assert body.count("<article") == 1 and 'id="m5"' in body  # "third" is the only deleted match
    assert 'placeholder="Search all messages" value="ir"' in body
    kwargs = fake_repo.calls[-1][1]
    assert kwargs["filters"] == MessageFilters(
        q="ir", deleted_only=True, since=datetime(2026, 9, 1, tzinfo=WARSAW)
    )
    assert kwargs["before"] is None and kwargs["limit"] == 100
    assert '<option value="-100">Grp</option>' in body and '<option value="-200">Other</option>' in body


async def test_search_filters_by_chat_id(authed_client, fake_repo):
    seed(fake_repo)
    r = await authed_client.get("/search?q=ir&chat=-100")
    assert r.status_code == 200
    body = r.text
    assert body.count("<article") == 1 and 'id="m1"' in body
    assert '<option value="-100" selected>Grp</option>' in body
    kwargs = fake_repo.calls[-1][1]
    assert kwargs["filters"] == MessageFilters(q="ir", chat_id=-100)


async def test_search_pagination(authed_client, fake_repo):
    seed(fake_repo)
    for i in range(10, 112):
        fake_repo.add_message(chat_id=-100, id=i, text="needle", sent_at=NOW + timedelta(seconds=i))
    r = await authed_client.get("/search?q=needle&chat=-100")
    assert (
        r.text.count("<article") == 100 and "before_id=12" in r.text and "q=needle&amp;" in r.text
    )
    assert "chat=-100" in r.text
