from kodzu_thon.services.message_cache import CachedMessage, MessageCache


def test_add_and_get_round_trips():
    c = MessageCache()
    c.add(chat_id=1, message_id=10, sender_id=7, sender_name="@a", chat_title="Group", text="hi")
    m = c.get(chat_id=1, message_id=10)
    assert isinstance(m, CachedMessage)
    assert m.text == "hi"
    assert m.sender_id == 7


def test_get_missing_returns_none():
    assert MessageCache().get(chat_id=1, message_id=99) is None


def test_multiple_chats_isolated():
    c = MessageCache()
    c.add(1, 10, 1, "a", "A", "one")
    c.add(2, 10, 2, "b", "B", "two")
    assert c.get(1, 10).text == "one"
    assert c.get(2, 10).text == "two"
