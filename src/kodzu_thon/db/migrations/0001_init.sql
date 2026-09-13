-- Message archive schema. Chat ids are Telethon marked ids (negative for groups/channels).
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE blobs (
  id          BIGSERIAL PRIMARY KEY,
  sha256      BYTEA NOT NULL UNIQUE,
  mime_type   TEXT NOT NULL,
  size        BIGINT NOT NULL,
  data        BYTEA NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE chats (
  id               BIGINT PRIMARY KEY,
  type             TEXT NOT NULL CHECK (type IN ('group', 'supergroup', 'channel')),
  title            TEXT,
  username         TEXT,
  photo_id         BIGINT,
  photo_blob_id    BIGINT REFERENCES blobs(id),
  first_seen_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_message_at  TIMESTAMPTZ
);

CREATE TABLE users (
  id             BIGINT PRIMARY KEY,
  first_name     TEXT,
  last_name      TEXT,
  username       TEXT,
  is_bot         BOOLEAN NOT NULL DEFAULT false,
  is_self        BOOLEAN NOT NULL DEFAULT false,
  photo_id       BIGINT,
  photo_blob_id  BIGINT REFERENCES blobs(id),
  first_seen_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE user_name_history (
  id          BIGSERIAL PRIMARY KEY,
  user_id     BIGINT NOT NULL REFERENCES users(id),
  first_name  TEXT,
  last_name   TEXT,
  username    TEXT,
  seen_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX user_name_history_user_idx ON user_name_history (user_id, seen_at DESC);

CREATE TABLE messages (
  chat_id           BIGINT NOT NULL REFERENCES chats(id),
  id                BIGINT NOT NULL,
  sender_user_id    BIGINT REFERENCES users(id),
  sender_chat_id    BIGINT REFERENCES chats(id),
  is_outgoing       BOOLEAN NOT NULL DEFAULT false,
  sent_at           TIMESTAMPTZ NOT NULL,
  text              TEXT,
  reply_to_msg_id   BIGINT,
  grouped_id        BIGINT,
  fwd_from_user_id  BIGINT,
  fwd_from_chat_id  BIGINT,
  fwd_from_name     TEXT,
  fwd_date          TIMESTAMPTZ,
  media_type        TEXT CHECK (media_type IN ('photo', 'video', 'document', 'voice',
                      'audio', 'sticker', 'gif', 'video_note', 'webpage', 'other')),
  media_size        BIGINT,
  media_meta        JSONB,
  media_blob_id     BIGINT REFERENCES blobs(id),
  raw               JSONB NOT NULL,
  edited_at         TIMESTAMPTZ,
  edit_count        INTEGER NOT NULL DEFAULT 0,
  deleted_at        TIMESTAMPTZ,
  recorded_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (chat_id, id)
);
CREATE INDEX messages_sender_idx         ON messages (sender_user_id, sent_at DESC)
  WHERE sender_user_id IS NOT NULL;
CREATE INDEX messages_deleted_chat_idx   ON messages (chat_id, id DESC) WHERE deleted_at IS NOT NULL;
CREATE INDEX messages_deleted_global_idx ON messages (deleted_at DESC, id DESC) WHERE deleted_at IS NOT NULL;
CREATE INDEX messages_edited_idx         ON messages (chat_id, id DESC) WHERE edit_count > 0;
CREATE INDEX messages_sent_at_idx        ON messages (sent_at DESC, id DESC);
CREATE INDEX messages_text_trgm_idx      ON messages USING gin (text gin_trgm_ops);

CREATE TABLE message_edits (
  id                 BIGSERIAL PRIMARY KEY,
  chat_id            BIGINT NOT NULL,
  message_id         BIGINT NOT NULL,
  edited_at          TIMESTAMPTZ NOT NULL,
  old_text           TEXT,
  old_media_blob_id  BIGINT REFERENCES blobs(id),
  old_raw            JSONB NOT NULL,
  FOREIGN KEY (chat_id, message_id) REFERENCES messages (chat_id, id)
);
CREATE INDEX message_edits_msg_idx ON message_edits (chat_id, message_id, edited_at);

CREATE TABLE web_sessions (
  token_hash    BYTEA PRIMARY KEY,
  state         TEXT NOT NULL CHECK (state IN ('anon', 'pending_totp', 'authed')),
  username      TEXT,
  csrf_token    TEXT NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at    TIMESTAMPTZ NOT NULL,
  ip            INET,
  user_agent    TEXT
);
CREATE INDEX web_sessions_expires_idx ON web_sessions (expires_at);

CREATE TABLE web_login_attempts (
  id            BIGSERIAL PRIMARY KEY,
  ip            INET NOT NULL,
  username      TEXT,
  attempted_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  success       BOOLEAN NOT NULL
);
CREATE INDEX web_login_attempts_ip_idx ON web_login_attempts (ip, attempted_at DESC);
CREATE INDEX web_login_attempts_ts_idx ON web_login_attempts (attempted_at DESC);

CREATE TABLE web_totp_state (
  id            INTEGER PRIMARY KEY CHECK (id = 1),
  last_counter  BIGINT NOT NULL
);

-- Read-only role used by kodzuthon.web (created by deploy/postgres-init.sql).
-- Phase 2 (the web viewer) is what actually creates and uses this role; guard the
-- grants so a Phase-1-only deploy that skips deploy/postgres-init.sql's role-creation
-- step does not fail the migration permanently with "role kodzuweb_ro does not exist".
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'kodzuweb_ro') THEN
    GRANT SELECT ON chats, users, user_name_history, messages, message_edits, blobs,
      schema_migrations TO kodzuweb_ro;
    GRANT SELECT, INSERT, UPDATE, DELETE ON web_sessions, web_login_attempts,
      web_totp_state TO kodzuweb_ro;
    GRANT USAGE, SELECT ON SEQUENCE web_login_attempts_id_seq TO kodzuweb_ro;
  END IF;
END $$;
