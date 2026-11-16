-- Web viewer, "last 30 days" by default: a chat's messages in a date range (the timeline's
-- since/until filters and the per-day activity chart) without walking the whole chat.
CREATE INDEX messages_chat_sent_idx ON messages (chat_id, sent_at DESC, id DESC);

-- Edited feed (web /changes?show=edited), mirroring the two deleted-feed indexes: newest
-- edits globally, and per chat for the chat-kind filter.
CREATE INDEX messages_edited_global_idx ON messages (edited_at DESC, id DESC)
  WHERE edit_count > 0;
CREATE INDEX messages_edited_by_chat_idx ON messages (chat_id, edited_at DESC, id DESC)
  WHERE edit_count > 0;
