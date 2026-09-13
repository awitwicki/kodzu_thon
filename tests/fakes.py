"""Fakes for the asyncpg boundary. `calls` records every statement in order,
including `BEGIN`/`COMMIT`/`ROLLBACK` markers emitted by `transaction()`."""

from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any


class FakeConn:
    def __init__(
        self,
        *,
        fetch_results: list[list[dict[str, Any]]] | None = None,
        fetchrow_results: list[dict[str, Any] | None] | None = None,
        fetchval_results: list[Any] | None = None,
        fail_on: Callable[[str, tuple], Exception | None] | None = None,
    ) -> None:
        self.calls: list[tuple[str, tuple]] = []
        self._fetch_results = list(fetch_results or [])
        self._fetchrow_results = list(fetchrow_results or [])
        self._fetchval_results = list(fetchval_results or [])
        self.fail_on = fail_on
        self.closed = False

    def _maybe_fail(self, sql: str, args: tuple) -> None:
        if self.fail_on is not None:
            exc = self.fail_on(sql, args)
            if exc is not None:
                raise exc

    async def execute(self, sql: str, *args: Any) -> str:
        self._maybe_fail(sql, args)
        self.calls.append((sql, args))
        return "OK"

    async def fetch(self, sql: str, *args: Any) -> list[dict[str, Any]]:
        self._maybe_fail(sql, args)
        self.calls.append((sql, args))
        return self._fetch_results.pop(0) if self._fetch_results else []

    async def fetchrow(self, sql: str, *args: Any) -> dict[str, Any] | None:
        self._maybe_fail(sql, args)
        self.calls.append((sql, args))
        return self._fetchrow_results.pop(0) if self._fetchrow_results else None

    async def fetchval(self, sql: str, *args: Any) -> Any:
        self._maybe_fail(sql, args)
        self.calls.append((sql, args))
        return self._fetchval_results.pop(0) if self._fetchval_results else None

    @asynccontextmanager
    async def transaction(self):
        self.calls.append(("BEGIN", ()))
        try:
            yield
        except BaseException:
            self.calls.append(("ROLLBACK", ()))
            raise
        self.calls.append(("COMMIT", ()))

    async def close(self) -> None:
        self.closed = True

    def sqls(self) -> list[str]:
        return [sql for sql, _ in self.calls]

    def args_for(self, sql: str) -> list[tuple]:
        return [args for s, args in self.calls if s == sql]


class FakePool:
    def __init__(self, conn: FakeConn) -> None:
        self.conn = conn
        self.closed = False
        self.terminated = False

    @asynccontextmanager
    async def acquire(self):
        yield self.conn

    async def close(self) -> None:
        self.closed = True

    def terminate(self) -> None:
        self.terminated = True
        self.closed = True


def fail_once(sql: str, exc: Exception) -> Callable[[str, tuple], Exception | None]:
    """Return a `fail_on` callback raising `exc` the first time `sql` is executed."""
    state = {"armed": True}

    def _fail(executed: str, args: tuple) -> Exception | None:
        if state["armed"] and executed == sql:
            state["armed"] = False
            return exc
        return None

    return _fail
