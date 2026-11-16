-- Deleted feed narrowed to a chat kind (web /deleted?kind=...): lets the newest deletions
-- of each chat be read straight off an index, instead of walking the global deleted index
-- and discarding every row from chats of the other kind until a page fills.
CREATE INDEX messages_deleted_by_chat_idx ON messages (chat_id, deleted_at DESC, id DESC)
  WHERE deleted_at IS NOT NULL;
