-- Forum topics ("chats with topics"): which chats are forums, which topic each message
-- belongs to, and topic titles. General topic has id 1; topic_id is NULL outside forums.
ALTER TABLE chats ADD COLUMN is_forum BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE messages ADD COLUMN topic_id BIGINT;

-- No FK to chats: titles are fetched from Telegram independently of the message queue.
CREATE TABLE forum_topics (
  chat_id        BIGINT NOT NULL,
  id             BIGINT NOT NULL,
  title          TEXT NOT NULL,
  icon_emoji_id  BIGINT,
  closed         BOOLEAN NOT NULL DEFAULT false,
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (chat_id, id)
);

-- Backfill from the stored raw Telethon JSON: a message inside a non-General topic
-- carries reply_to.forum_topic, with the topic id in reply_to_top_id when it is also a
-- reply to another message, else in reply_to_msg_id.
UPDATE messages SET topic_id = COALESCE(
    (raw->'reply_to'->>'reply_to_top_id')::bigint,
    (raw->'reply_to'->>'reply_to_msg_id')::bigint)
WHERE (raw->'reply_to'->>'forum_topic')::boolean;

UPDATE chats SET is_forum = true
WHERE EXISTS (SELECT 1 FROM messages m WHERE m.chat_id = chats.id AND m.topic_id IS NOT NULL);

-- Everything else in a forum lives in General.
UPDATE messages m SET topic_id = 1
FROM chats c WHERE c.id = m.chat_id AND c.is_forum AND m.topic_id IS NULL;

CREATE INDEX messages_topic_idx ON messages (chat_id, topic_id, id DESC) WHERE topic_id IS NOT NULL;

DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'kodzuweb_ro') THEN
    GRANT SELECT ON forum_topics TO kodzuweb_ro;
  END IF;
END $$;
