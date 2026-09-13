"""Every SQL statement the web viewer runs. Parameterized asyncpg only; rows come
back as plain dicts with JSONB columns decoded, so templates and the test fake
see identical shapes."""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from kodzu_thon.web.textfmt import escape_like

PAGE_SIZE = 100
MAX_PAGE_SIZE = 200


@dataclass(frozen=True)
class MessageFilters:
    q: str | None = None
    sender_id: int | None = None
    deleted_only: bool = False
    edited_only: bool = False
    since: datetime | None = None
    until: datetime | None = None


MESSAGE_SELECT = """
SELECT m.chat_id, m.id, m.sender_user_id, m.sender_chat_id, m.is_outgoing, m.sent_at, m.text,
       m.reply_to_msg_id, m.grouped_id, m.fwd_from_user_id, m.fwd_from_chat_id, m.fwd_from_name,
       m.fwd_date, m.media_type, m.media_size, m.media_meta, m.media_blob_id, m.edited_at,
       m.edit_count, m.deleted_at,
       c.title AS chat_title, c.type AS chat_type,
       u.first_name AS sender_first_name, u.last_name AS sender_last_name,
       u.username AS sender_username, u.photo_blob_id AS sender_photo_blob_id,
       sc.title AS sender_chat_title, sc.photo_blob_id AS sender_chat_photo_blob_id,
       r.text AS reply_text, ru.first_name AS reply_first_name, ru.last_name AS reply_last_name,
       rsc.title AS reply_chat_title,
       fu.first_name AS fwd_first_name, fu.last_name AS fwd_last_name, fc.title AS fwd_chat_title
FROM messages m
JOIN chats c ON c.id = m.chat_id
LEFT JOIN users u ON u.id = m.sender_user_id
LEFT JOIN chats sc ON sc.id = m.sender_chat_id
LEFT JOIN messages r ON r.chat_id = m.chat_id AND r.id = m.reply_to_msg_id
LEFT JOIN users ru ON ru.id = r.sender_user_id
LEFT JOIN chats rsc ON rsc.id = r.sender_chat_id
LEFT JOIN users fu ON fu.id = m.fwd_from_user_id
LEFT JOIN chats fc ON fc.id = m.fwd_from_chat_id
""".strip()

MESSAGE_SELECT_WITH_RAW = MESSAGE_SELECT.replace(
    "m.edit_count, m.deleted_at,", "m.edit_count, m.deleted_at, m.raw,", 1
)

LIST_CHATS = (
    "SELECT id, type, title, username, photo_blob_id, first_seen_at, last_message_at "
    "FROM chats ORDER BY last_message_at DESC NULLS LAST, id"
)
GET_CHAT = (
    "SELECT id, type, title, username, photo_blob_id, first_seen_at, last_message_at "
    "FROM chats WHERE id = $1"
)
GET_USER = (
    "SELECT id, first_name, last_name, username, is_bot, is_self, photo_blob_id, "
    "first_seen_at, last_seen_at FROM users WHERE id = $1"
)
USER_NAME_HISTORY = (
    "SELECT first_name, last_name, username, seen_at "
    "FROM user_name_history WHERE user_id = $1 ORDER BY seen_at DESC, id DESC"
)
USER_CHATS = (
    "SELECT c.id, c.title, c.type, count(*) AS message_count "
    "FROM messages m JOIN chats c ON c.id = m.chat_id WHERE m.sender_user_id = $1 "
    "GROUP BY c.id, c.title, c.type ORDER BY message_count DESC"
)
MESSAGE_EDITS = (
    "SELECT id, edited_at, old_text, old_media_blob_id, old_raw "
    "FROM message_edits WHERE chat_id = $1 AND message_id = $2 ORDER BY edited_at, id"
)
GET_BLOB = "SELECT id, mime_type, size, data FROM blobs WHERE id = $1"
PING = "SELECT 1"
SCHEMA_VERSION_SQL = "SELECT max(version) FROM schema_migrations"

GET_SESSION = (
    "SELECT token_hash, state, username, csrf_token, created_at, last_seen_at, expires_at "
    "FROM web_sessions WHERE token_hash = $1"
)
CREATE_SESSION = (
    "INSERT INTO web_sessions (token_hash, state, username, csrf_token, created_at, "
    "last_seen_at, expires_at, ip, user_agent) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)"
)
TOUCH_SESSION = "UPDATE web_sessions SET last_seen_at = $2, expires_at = $3 WHERE token_hash = $1"
SET_SESSION_STATE = "UPDATE web_sessions SET state = $2 WHERE token_hash = $1"
DELETE_SESSION = "DELETE FROM web_sessions WHERE token_hash = $1"
DELETE_EXPIRED_SESSIONS = "DELETE FROM web_sessions WHERE expires_at <= $1"
RECORD_LOGIN_ATTEMPT = "INSERT INTO web_login_attempts (ip, username, success) VALUES ($1, $2, $3)"
FAILED_BY_IP = (
    "SELECT count(*) FROM web_login_attempts "
    "WHERE ip = $1 AND success = false AND attempted_at >= $2"
)
FAILED_BY_USERNAME = (
    "SELECT count(*) FROM web_login_attempts "
    "WHERE username = $1 AND success = false AND attempted_at >= $2"
)
GET_TOTP_COUNTER = "SELECT last_counter FROM web_totp_state WHERE id = 1"
SET_TOTP_COUNTER = (
    "INSERT INTO web_totp_state (id, last_counter) VALUES (1, $1) "
    "ON CONFLICT (id) DO UPDATE SET last_counter = EXCLUDED.last_counter"
)


def _json(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def _message_row(record: Any) -> dict:
    row = dict(record)
    if "media_meta" in row:
        row["media_meta"] = _json(row["media_meta"])
    if "raw" in row:
        row["raw"] = _json(row["raw"])
    return row


def _filter_clauses(filters: MessageFilters, params: list[Any]) -> list[str]:
    clauses: list[str] = []
    if filters.deleted_only:
        clauses.append("m.deleted_at IS NOT NULL")
    if filters.edited_only:
        clauses.append("m.edit_count > 0")
    if filters.sender_id is not None:
        params.append(filters.sender_id)
        clauses.append(f"m.sender_user_id = ${len(params)}")
    if filters.q:
        params.append(escape_like(filters.q))
        clauses.append(f"m.text ILIKE '%' || ${len(params)} || '%' ESCAPE '\\'")
    if filters.since is not None:
        params.append(filters.since)
        clauses.append(f"m.sent_at >= ${len(params)}")
    if filters.until is not None:
        params.append(filters.until)
        clauses.append(f"m.sent_at < ${len(params)}")
    return clauses


def _feed_query(
    base_clauses: list[str],
    params: list[Any],
    *,
    keyset_columns: tuple[str, str],
    before: tuple[datetime, int] | None,
    limit: int,
    filters: MessageFilters,
) -> tuple[str, list[Any]]:
    clauses = list(base_clauses)
    if before is not None:
        params.extend(before)
        clauses.append(
            f"({keyset_columns[0]}, {keyset_columns[1]}) < (${len(params) - 1}, ${len(params)})"
        )
    clauses += _filter_clauses(filters, params)
    if not clauses:
        clauses = ["true"]
    params.append(limit + 1)
    where = " AND ".join(clauses)
    order = f"{keyset_columns[0]} DESC, {keyset_columns[1]} DESC"
    return f"{MESSAGE_SELECT} WHERE {where} ORDER BY {order} LIMIT ${len(params)}", params


class Repository:
    def __init__(self, pool) -> None:
        self._pool = pool

    async def close(self) -> None:
        await self._pool.close()

    # ---- low-level -------------------------------------------------------

    async def _fetch(self, sql: str, *args: Any) -> list[dict]:
        async with self._pool.acquire() as conn:
            return [dict(r) for r in await conn.fetch(sql, *args)]

    async def _fetchrow(self, sql: str, *args: Any) -> dict | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(sql, *args)
        return None if row is None else dict(row)

    async def _fetchval(self, sql: str, *args: Any) -> Any:
        async with self._pool.acquire() as conn:
            return await conn.fetchval(sql, *args)

    async def _execute(self, sql: str, *args: Any) -> str:
        async with self._pool.acquire() as conn:
            return await conn.execute(sql, *args)

    # ---- meta ------------------------------------------------------------

    async def ping(self) -> bool:
        try:
            return await self._fetchval(PING) == 1
        except Exception:
            return False

    async def schema_version(self) -> int | None:
        return await self._fetchval(SCHEMA_VERSION_SQL)

    # ---- chats and messages ---------------------------------------------

    async def list_chats(self) -> list[dict]:
        return await self._fetch(LIST_CHATS)

    async def get_chat(self, chat_id: int) -> dict | None:
        return await self._fetchrow(GET_CHAT, chat_id)

    async def chat_messages(
        self,
        chat_id: int,
        *,
        before_id: int | None = None,
        limit: int = PAGE_SIZE,
        filters: MessageFilters = MessageFilters(),
    ) -> list[dict]:
        params: list[Any] = [chat_id]
        clauses = ["m.chat_id = $1"]
        if before_id is not None:
            params.append(before_id)
            clauses.append(f"m.id < ${len(params)}")
        clauses += _filter_clauses(filters, params)
        params.append(limit + 1)
        sql = f"{MESSAGE_SELECT} WHERE {' AND '.join(clauses)} ORDER BY m.id DESC LIMIT ${len(params)}"
        return [_message_row(r) for r in await self._fetch(sql, *params)]

    async def get_message(self, chat_id: int, message_id: int) -> dict | None:
        sql = f"{MESSAGE_SELECT_WITH_RAW} WHERE m.chat_id = $1 AND m.id = $2"
        row = await self._fetchrow(sql, chat_id, message_id)
        return None if row is None else _message_row(row)

    async def message_edits(self, chat_id: int, message_id: int) -> list[dict]:
        rows = await self._fetch(MESSAGE_EDITS, chat_id, message_id)
        for row in rows:
            row["old_raw"] = _json(row["old_raw"])
        return rows

    async def deleted_messages(
        self,
        *,
        before: tuple[datetime, int] | None = None,
        limit: int = PAGE_SIZE,
        filters: MessageFilters = MessageFilters(),
    ) -> list[dict]:
        sql, params = _feed_query(
            ["m.deleted_at IS NOT NULL"],
            [],
            keyset_columns=("m.deleted_at", "m.id"),
            before=before,
            limit=limit,
            filters=filters,
        )
        return [_message_row(r) for r in await self._fetch(sql, *params)]

    async def search_messages(
        self,
        *,
        before: tuple[datetime, int] | None = None,
        limit: int = PAGE_SIZE,
        filters: MessageFilters,
    ) -> list[dict]:
        if not filters.q:
            raise ValueError("search requires filters.q")
        sql, params = _feed_query(
            [],
            [],
            keyset_columns=("m.sent_at", "m.id"),
            before=before,
            limit=limit,
            filters=filters,
        )
        return [_message_row(r) for r in await self._fetch(sql, *params)]

    # ---- users -----------------------------------------------------------

    async def get_user(self, user_id: int) -> dict | None:
        return await self._fetchrow(GET_USER, user_id)

    async def user_name_history(self, user_id: int) -> list[dict]:
        return await self._fetch(USER_NAME_HISTORY, user_id)

    async def user_chats(self, user_id: int) -> list[dict]:
        return await self._fetch(USER_CHATS, user_id)

    async def user_messages(
        self,
        user_id: int,
        *,
        before: tuple[datetime, int] | None = None,
        limit: int = PAGE_SIZE,
        filters: MessageFilters = MessageFilters(),
    ) -> list[dict]:
        sql, params = _feed_query(
            ["m.sender_user_id = $1"],
            [user_id],
            keyset_columns=("m.sent_at", "m.id"),
            before=before,
            limit=limit,
            filters=filters,
        )
        return [_message_row(r) for r in await self._fetch(sql, *params)]

    # ---- media -----------------------------------------------------------

    async def get_blob(self, blob_id: int) -> dict | None:
        return await self._fetchrow(GET_BLOB, blob_id)

    # ---- auth tables -----------------------------------------------------

    async def get_session(self, token_hash: bytes) -> dict | None:
        return await self._fetchrow(GET_SESSION, token_hash)

    async def create_session(
        self,
        token_hash: bytes,
        state: str,
        username: str | None,
        csrf_token: str,
        created_at: datetime,
        expires_at: datetime,
        ip: str,
        user_agent: str | None,
    ) -> None:
        await self._execute(
            CREATE_SESSION,
            token_hash,
            state,
            username,
            csrf_token,
            created_at,
            created_at,
            expires_at,
            ip,
            user_agent,
        )

    async def touch_session(
        self, token_hash: bytes, last_seen_at: datetime, expires_at: datetime
    ) -> None:
        await self._execute(TOUCH_SESSION, token_hash, last_seen_at, expires_at)

    async def set_session_state(self, token_hash: bytes, state: str) -> None:
        await self._execute(SET_SESSION_STATE, token_hash, state)

    async def delete_session(self, token_hash: bytes) -> None:
        await self._execute(DELETE_SESSION, token_hash)

    async def delete_expired_sessions(self, now: datetime) -> int:
        status = await self._execute(DELETE_EXPIRED_SESSIONS, now)
        try:
            return int(status.rsplit(" ", 1)[-1])
        except (ValueError, AttributeError):
            return 0

    async def record_login_attempt(self, ip: str, username: str | None, success: bool) -> None:
        await self._execute(RECORD_LOGIN_ATTEMPT, ip, username, success)

    async def failed_attempts_by_ip(self, ip: str, since: datetime) -> int:
        return await self._fetchval(FAILED_BY_IP, ip, since) or 0

    async def failed_attempts_by_username(self, username: str, since: datetime) -> int:
        return await self._fetchval(FAILED_BY_USERNAME, username, since) or 0

    async def get_totp_counter(self) -> int | None:
        return await self._fetchval(GET_TOTP_COUNTER)

    async def set_totp_counter(self, counter: int) -> None:
        await self._execute(SET_TOTP_COUNTER, counter)
