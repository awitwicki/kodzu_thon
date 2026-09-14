"""In-memory stand-in for kodzu_thon.web.repository.Repository. Same method
names, same dict shapes, simple Python filtering. Records calls for assertions."""

from datetime import UTC, datetime
from typing import Any

from kodzu_thon.db import SCHEMA_VERSION
from kodzu_thon.web.repository import PAGE_SIZE, MessageFilters

NOW = datetime(2026, 9, 13, 12, 0, tzinfo=UTC)


def make_message_row(**overrides: Any) -> dict:
    row = {
        "chat_id": -100,
        "id": 1,
        "sender_user_id": 7,
        "sender_chat_id": None,
        "is_outgoing": False,
        "sent_at": NOW,
        "text": "hello",
        "reply_to_msg_id": None,
        "grouped_id": None,
        "fwd_from_user_id": None,
        "fwd_from_chat_id": None,
        "fwd_from_name": None,
        "fwd_date": None,
        "media_type": None,
        "media_size": None,
        "media_meta": None,
        "media_blob_id": None,
        "edited_at": None,
        "edit_count": 0,
        "deleted_at": None,
        "chat_title": "Grp",
        "chat_type": "supergroup",
        "sender_first_name": "Ann",
        "sender_last_name": "Lee",
        "sender_username": "ann",
        "sender_photo_blob_id": None,
        "sender_chat_title": None,
        "sender_chat_photo_blob_id": None,
        "reply_text": None,
        "reply_first_name": None,
        "reply_last_name": None,
        "reply_chat_title": None,
        "fwd_first_name": None,
        "fwd_last_name": None,
        "fwd_chat_title": None,
        "raw": {},
    }
    row.update(overrides)
    return row


class FakeRepository:
    def __init__(self) -> None:
        self.chats: dict[int, dict] = {}
        self.users: dict[int, dict] = {}
        self.messages: list[dict] = []
        self.edits: dict[tuple[int, int], list[dict]] = {}
        self.blobs: dict[int, dict] = {}
        self.name_history: dict[int, list[dict]] = {}
        self.sessions: dict[bytes, dict] = {}
        self.attempts: list[dict] = []
        self.totp_counter: int | None = None
        self.ping_ok = True
        self.version: int | None = SCHEMA_VERSION
        self.closed = False
        self.calls: list[tuple[str, dict]] = []

    # ---- builders ----------------------------------------------------------

    def add_chat(self, **fields: Any) -> dict:
        chat = {
            "id": -100,
            "type": "supergroup",
            "title": "Grp",
            "username": None,
            "photo_blob_id": None,
            "first_seen_at": NOW,
            "last_message_at": NOW,
        }
        chat.update(fields)
        self.chats[chat["id"]] = chat
        return chat

    def add_user(self, **fields: Any) -> dict:
        user = {
            "id": 7,
            "first_name": "Ann",
            "last_name": "Lee",
            "username": "ann",
            "is_bot": False,
            "is_self": False,
            "photo_blob_id": None,
            "first_seen_at": NOW,
            "last_seen_at": NOW,
        }
        user.update(fields)
        self.users[user["id"]] = user
        return user

    def add_message(self, **fields: Any) -> dict:
        row = make_message_row(**fields)
        chat = self.chats.get(row["chat_id"])
        if chat is not None:
            row["chat_title"], row["chat_type"] = chat["title"], chat["type"]
        user = self.users.get(row["sender_user_id"]) if row["sender_user_id"] else None
        if user is not None:
            row["sender_first_name"] = user["first_name"]
            row["sender_last_name"] = user["last_name"]
            row["sender_username"] = user["username"]
            row["sender_photo_blob_id"] = user["photo_blob_id"]
        self.messages.append(row)
        return row

    def add_edit(self, chat_id: int, message_id: int, **fields: Any) -> dict:
        edit = {
            "id": len(self.edits) + 1,
            "edited_at": NOW,
            "old_text": None,
            "old_media_blob_id": None,
            "old_raw": {},
        }
        edit.update(fields)
        self.edits.setdefault((chat_id, message_id), []).append(edit)
        return edit

    def add_blob(self, **fields: Any) -> dict:
        blob = {"id": 1, "mime_type": "image/jpeg", "size": 0, "data": b""}
        blob.update(fields)
        blob["size"] = blob["size"] or len(blob["data"])
        self.blobs[blob["id"]] = blob
        return blob

    def add_name_history(self, user_id: int, **fields: Any) -> dict:
        entry = {"first_name": None, "last_name": None, "username": None, "seen_at": NOW}
        entry.update(fields)
        self.name_history.setdefault(user_id, []).append(entry)
        return entry

    # ---- helpers -----------------------------------------------------------

    def _record(self, name: str, **kwargs: Any) -> None:
        self.calls.append((name, kwargs))

    @staticmethod
    def _apply_filters(rows: list[dict], f: MessageFilters) -> list[dict]:
        if f.chat_id is not None:
            rows = [r for r in rows if r["chat_id"] == f.chat_id]
        if f.deleted_only:
            rows = [r for r in rows if r["deleted_at"] is not None]
        if f.edited_only:
            rows = [r for r in rows if r["edit_count"] > 0]
        if f.sender_id is not None:
            rows = [r for r in rows if r["sender_user_id"] == f.sender_id]
        if f.q:
            rows = [r for r in rows if r["text"] and f.q.lower() in r["text"].lower()]
        if f.since is not None:
            rows = [r for r in rows if r["sent_at"] >= f.since]
        if f.until is not None:
            rows = [r for r in rows if r["sent_at"] < f.until]
        return rows

    @staticmethod
    def _keyset(rows: list[dict], column: str, before: tuple[datetime, int] | None) -> list[dict]:
        if before is None:
            return rows
        ts, mid = before
        return [r for r in rows if (r[column], r["id"]) < (ts, mid)]

    @staticmethod
    def _copy(row: dict | None) -> dict | None:
        return None if row is None else dict(row)

    # ---- meta --------------------------------------------------------------

    async def close(self) -> None:
        self.closed = True

    async def ping(self) -> bool:
        return self.ping_ok

    async def schema_version(self) -> int | None:
        return self.version

    # ---- chats and messages -----------------------------------------------

    async def list_chats(self) -> list[dict]:
        self._record("list_chats")
        chats = sorted(
            self.chats.values(),
            key=lambda c: (
                c["last_message_at"] is None,
                -(c["last_message_at"] or NOW).timestamp(),
                c["id"],
            ),
        )
        return [dict(c) for c in chats]

    async def get_chat(self, chat_id: int) -> dict | None:
        self._record("get_chat", chat_id=chat_id)
        return self._copy(self.chats.get(chat_id))

    async def chat_messages(
        self,
        chat_id: int,
        *,
        before_id: int | None = None,
        limit: int = PAGE_SIZE,
        filters: MessageFilters = MessageFilters(),
    ) -> list[dict]:
        self._record(
            "chat_messages", chat_id=chat_id, before_id=before_id, limit=limit, filters=filters
        )
        rows = [r for r in self.messages if r["chat_id"] == chat_id]
        if before_id is not None:
            rows = [r for r in rows if r["id"] < before_id]
        rows = self._apply_filters(rows, filters)
        rows.sort(key=lambda r: r["id"], reverse=True)
        return [dict(r) for r in rows[: limit + 1]]

    async def get_message(self, chat_id: int, message_id: int) -> dict | None:
        self._record("get_message", chat_id=chat_id, message_id=message_id)
        for r in self.messages:
            if r["chat_id"] == chat_id and r["id"] == message_id:
                return dict(r)
        return None

    async def message_edits(self, chat_id: int, message_id: int) -> list[dict]:
        self._record("message_edits", chat_id=chat_id, message_id=message_id)
        return [dict(e) for e in self.edits.get((chat_id, message_id), [])]

    async def deleted_messages(
        self,
        *,
        before: tuple[datetime, int] | None = None,
        limit: int = PAGE_SIZE,
        filters: MessageFilters = MessageFilters(),
    ) -> list[dict]:
        self._record("deleted_messages", before=before, limit=limit, filters=filters)
        rows = [r for r in self.messages if r["deleted_at"] is not None]
        rows = self._keyset(rows, "deleted_at", before)
        rows = self._apply_filters(rows, filters)
        rows.sort(key=lambda r: (r["deleted_at"], r["id"]), reverse=True)
        return [dict(r) for r in rows[: limit + 1]]

    async def search_messages(
        self,
        *,
        before: tuple[datetime, int] | None = None,
        limit: int = PAGE_SIZE,
        filters: MessageFilters,
    ) -> list[dict]:
        if not filters.q:
            raise ValueError("search requires filters.q")
        self._record("search_messages", before=before, limit=limit, filters=filters)
        rows = self._keyset(list(self.messages), "sent_at", before)
        rows = self._apply_filters(rows, filters)
        rows.sort(key=lambda r: (r["sent_at"], r["id"]), reverse=True)
        return [dict(r) for r in rows[: limit + 1]]

    # ---- users -------------------------------------------------------------

    async def get_user(self, user_id: int) -> dict | None:
        self._record("get_user", user_id=user_id)
        return self._copy(self.users.get(user_id))

    async def user_name_history(self, user_id: int) -> list[dict]:
        self._record("user_name_history", user_id=user_id)
        entries = sorted(
            self.name_history.get(user_id, []), key=lambda e: e["seen_at"], reverse=True
        )
        return [dict(e) for e in entries]

    async def user_chats(self, user_id: int) -> list[dict]:
        self._record("user_chats", user_id=user_id)
        counts: dict[int, int] = {}
        for r in self.messages:
            if r["sender_user_id"] == user_id:
                counts[r["chat_id"]] = counts.get(r["chat_id"], 0) + 1
        result = [
            {
                "id": cid,
                "title": self.chats[cid]["title"],
                "type": self.chats[cid]["type"],
                "message_count": n,
            }
            for cid, n in counts.items()
            if cid in self.chats
        ]
        result.sort(key=lambda c: c["message_count"], reverse=True)
        return result

    async def user_messages(
        self,
        user_id: int,
        *,
        before: tuple[datetime, int] | None = None,
        limit: int = PAGE_SIZE,
        filters: MessageFilters = MessageFilters(),
    ) -> list[dict]:
        self._record("user_messages", user_id=user_id, before=before, limit=limit, filters=filters)
        rows = [r for r in self.messages if r["sender_user_id"] == user_id]
        rows = self._keyset(rows, "sent_at", before)
        rows = self._apply_filters(rows, filters)
        rows.sort(key=lambda r: (r["sent_at"], r["id"]), reverse=True)
        return [dict(r) for r in rows[: limit + 1]]

    # ---- media -------------------------------------------------------------

    async def get_blob(self, blob_id: int) -> dict | None:
        self._record("get_blob", blob_id=blob_id)
        return self._copy(self.blobs.get(blob_id))

    # ---- auth tables -------------------------------------------------------

    async def get_session(self, token_hash: bytes) -> dict | None:
        return self._copy(self.sessions.get(token_hash))

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
        self.sessions[token_hash] = {
            "token_hash": token_hash,
            "state": state,
            "username": username,
            "csrf_token": csrf_token,
            "created_at": created_at,
            "last_seen_at": created_at,
            "expires_at": expires_at,
            "ip": ip,
            "user_agent": user_agent,
        }

    async def touch_session(
        self, token_hash: bytes, last_seen_at: datetime, expires_at: datetime
    ) -> None:
        if token_hash in self.sessions:
            self.sessions[token_hash].update(last_seen_at=last_seen_at, expires_at=expires_at)

    async def set_session_state(self, token_hash: bytes, state: str) -> None:
        if token_hash in self.sessions:
            self.sessions[token_hash]["state"] = state

    async def delete_session(self, token_hash: bytes) -> None:
        self.sessions.pop(token_hash, None)

    async def delete_expired_sessions(self, now: datetime) -> int:
        expired = [h for h, s in self.sessions.items() if s["expires_at"] <= now]
        for h in expired:
            del self.sessions[h]
        return len(expired)

    async def record_login_attempt(self, ip: str, username: str | None, success: bool) -> None:
        self.attempts.append(
            {"ip": ip, "username": username, "success": success, "attempted_at": datetime.now(UTC)}
        )

    async def failed_attempts_by_ip(self, ip: str, since: datetime) -> int:
        return sum(
            1
            for a in self.attempts
            if a["ip"] == ip and not a["success"] and a["attempted_at"] >= since
        )

    async def failed_attempts_by_username(self, username: str, since: datetime) -> int:
        return sum(
            1
            for a in self.attempts
            if a["username"] == username and not a["success"] and a["attempted_at"] >= since
        )

    async def get_totp_counter(self) -> int | None:
        return self.totp_counter

    async def set_totp_counter(self, counter: int) -> None:
        self.totp_counter = counter
