-- Per-chat message counts on a user's profile (web USER_CHATS): lets the count run as an
-- index-only scan instead of fetching every one of the user's message rows for chat_id.
CREATE INDEX messages_sender_chat_idx ON messages (sender_user_id, chat_id)
  WHERE sender_user_id IS NOT NULL;
