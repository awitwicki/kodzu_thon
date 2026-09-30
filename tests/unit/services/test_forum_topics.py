from unittest.mock import AsyncMock, MagicMock

from telethon.tl import functions, types

from kodzu_thon.services import forum_topics as ft
from kodzu_thon.services.forum_topics import TopicTracker
from kodzu_thon.services.message_extract import ChatSnapshot, MessageRecord, TopicRecord
from tests.factories import NOW

CHAT_ID = -1000000000124


def topic(id, title=None, top_message=None):
    return types.ForumTopic(
        id=id,
        date=NOW,
        title=title or f"T{id}",
        icon_color=0,
        top_message=top_message or id,
        read_inbox_max_id=0,
        read_outbox_max_id=0,
        unread_count=0,
        unread_mentions_count=0,
        unread_reactions_count=0,
        from_id=types.PeerUser(7),
        notify_settings=types.PeerNotifySettings(),
    )


def topics_result(topics):
    return types.messages.ForumTopics(
        count=len(topics), topics=topics, messages=[], chats=[], users=[], pts=0
    )


def record(topic_id, chat_id=CHAT_ID):
    chat = ChatSnapshot(chat_id, "supergroup", "Grp", None, None, is_forum=True)
    return MessageRecord(
        chat=chat,
        sender_user=None,
        sender_chat=None,
        id=1,
        is_outgoing=False,
        sent_at=NOW,
        text=None,
        reply_to_msg_id=None,
        grouped_id=None,
        fwd_from_user_id=None,
        fwd_from_chat_id=None,
        fwd_from_name=None,
        fwd_date=None,
        media_type=None,
        media_size=None,
        media_meta=None,
        raw={},
        topic_id=topic_id,
    )


def make_tracker(*results):
    client = AsyncMock(side_effect=list(results))
    store = MagicMock()
    store.enabled = True
    return TopicTracker(client, store), client, store


def enqueued(store):
    return [c.args[0] for c in store.enqueue.call_args_list]


async def test_non_forum_messages_are_ignored():
    tracker, client, _ = make_tracker()
    tracker.observe("chat", record(None))
    await tracker.drain()
    client.assert_not_called()


async def test_first_message_syncs_all_topics_then_only_new_ones():
    tracker, client, store = make_tracker(
        topics_result([topic(1, "General"), topic(5, "News"), types.ForumTopicDeleted(id=6)]),
        topics_result([topic(9, "Fresh")]),
    )
    tracker.observe("chat", record(5))
    tracker.observe("chat", record(9))  # during the sync: skipped, the sync covers it
    await tracker.drain()
    req = client.call_args_list[0].args[0]
    assert isinstance(req, functions.channels.GetForumTopicsRequest) and req.channel == "chat"
    assert enqueued(store) == [
        TopicRecord(CHAT_ID, 1, "General", None, False),
        TopicRecord(CHAT_ID, 5, "News", None, False),
    ]
    tracker.observe("chat", record(5))  # known
    tracker.observe("chat", record(9))  # new
    await tracker.drain()
    req = client.call_args_list[1].args[0]
    assert isinstance(req, functions.channels.GetForumTopicsByIDRequest) and req.topics == [9]
    assert enqueued(store)[-1] == TopicRecord(CHAT_ID, 9, "Fresh", None, False)
    tracker.observe("chat", record(9))
    await tracker.drain()
    assert client.call_count == 2


async def test_sync_paginates(mocker):
    mocker.patch.object(ft, "PAGE_SIZE", 2)
    tracker, client, store = make_tracker(
        topics_result([topic(9), topic(8, top_message=80)]),
        topics_result([topic(7)]),
    )
    tracker.observe("chat", record(1))
    await tracker.drain()
    second = client.call_args_list[1].args[0]
    assert second.offset_topic == 8 and second.offset_id == 80
    assert [r.id for r in enqueued(store)] == [9, 8, 7]


async def test_failures_are_logged(capsys):
    tracker, _, store = make_tracker(RuntimeError("no access"))
    tracker.observe("chat", record(1))
    await tracker.drain()
    assert "forum_topics: sync of -1000000000124 failed: no access" in capsys.readouterr().err
    store.enqueue.assert_not_called()


async def test_created_and_edited_topics():
    tracker, client, store = make_tracker(topics_result([topic(5, "Renamed")]))
    tracker.topic_created(CHAT_ID, 9, "Brand new", 77)
    assert enqueued(store) == [TopicRecord(CHAT_ID, 9, "Brand new", 77, False)]
    tracker.topic_edited("peer", CHAT_ID, 5)
    await tracker.drain()
    assert client.call_args.args[0].topics == [5]
    assert enqueued(store)[-1] == TopicRecord(CHAT_ID, 5, "Renamed", None, False)


async def test_disabled_store_does_nothing():
    tracker, client, store = make_tracker()
    store.enabled = False
    tracker.observe("chat", record(5))
    tracker.topic_created(CHAT_ID, 9, "x", None)
    tracker.topic_edited("peer", CHAT_ID, 5)
    await tracker.drain()
    client.assert_not_called()
    store.enqueue.assert_not_called()
