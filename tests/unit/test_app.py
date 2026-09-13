import asyncio
import signal
from unittest.mock import AsyncMock, MagicMock

from kodzu_thon.app import (
    AppContext,
    _install_stop_signal_handlers,
    _remove_stop_signal_handlers,
    _shutdown,
    build_app,
    run_app,
)


def _env(monkeypatch):
    monkeypatch.setenv("TELETHON_API_ID", "1")
    monkeypatch.setenv("TELETHON_API_HASH", "h")
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db/kodzu_messages")


def _patch_collaborators(mocker):
    for name in ("GeminiClient", "Translator", "AirAlarmService", "InfluxWriter"):
        mocker.patch(f"kodzu_thon.app.{name}")
    mocker.patch("kodzu_thon.app.handlers.register_all")
    client_cls = mocker.patch("kodzu_thon.app.TelegramClient")
    store_cls = mocker.patch("kodzu_thon.app.MessageStore")
    fetcher_cls = mocker.patch("kodzu_thon.app.MediaFetcher")
    return client_cls, store_cls, fetcher_cls


def test_build_app_constructs_context(mocker, monkeypatch):
    _env(monkeypatch)
    client_cls, store_cls, fetcher_cls = _patch_collaborators(mocker)

    client, ctx = build_app()

    assert isinstance(ctx, AppContext)
    assert ctx.settings.api_id == 1
    assert client_cls.call_args.kwargs["catch_up"] is True
    store_cls.assert_called_once_with("postgresql://u:p@db/kodzu_messages")
    fetcher_cls.assert_called_once_with(client, store_cls.return_value, 5 * 1024 * 1024)
    assert ctx.message_store is store_cls.return_value
    assert ctx.media_fetcher is fetcher_cls.return_value


async def test_run_app_starts_and_stops_recorder(mocker, fake_ctx):
    client = MagicMock()
    client.start = AsyncMock()
    client.run_until_disconnected = AsyncMock()
    client.disconnect = AsyncMock()
    fake_ctx.message_store.start = AsyncMock()
    fake_ctx.message_store.stop = AsyncMock()
    fake_ctx.media_fetcher.stop = AsyncMock()
    mocker.patch("kodzu_thon.app.build_app", return_value=(client, fake_ctx))
    mocker.patch("kodzu_thon.app._bio_loop", AsyncMock())

    await run_app()

    client.start.assert_awaited_once()
    fake_ctx.message_store.start.assert_awaited_once()
    fake_ctx.media_fetcher.stop.assert_awaited_once()
    fake_ctx.message_store.stop.assert_awaited_once()
    client.disconnect.assert_awaited_once()


async def test_shutdown_isolates_exception_in_first_stage(capsys):
    bio_task = MagicMock()
    ctx = MagicMock()
    ctx.media_fetcher.stop = AsyncMock(side_effect=RuntimeError("fetcher boom"))
    ctx.message_store.stop = AsyncMock()
    client = MagicMock()
    client.disconnect = AsyncMock()

    await _shutdown(bio_task, ctx, client)

    bio_task.cancel.assert_called_once()
    ctx.media_fetcher.stop.assert_awaited_once()
    ctx.message_store.stop.assert_awaited_once()
    client.disconnect.assert_awaited_once()
    assert "shutdown: fetcher boom" in capsys.readouterr().err


async def test_shutdown_continues_after_multiple_failures(capsys):
    bio_task = MagicMock()
    ctx = MagicMock()
    ctx.media_fetcher.stop = AsyncMock(side_effect=RuntimeError("fetcher boom"))
    ctx.message_store.stop = AsyncMock(side_effect=RuntimeError("store boom"))
    client = MagicMock()
    client.disconnect = AsyncMock()

    await _shutdown(bio_task, ctx, client)

    # Every stage still ran despite the first two raising.
    ctx.media_fetcher.stop.assert_awaited_once()
    ctx.message_store.stop.assert_awaited_once()
    client.disconnect.assert_awaited_once()
    err = capsys.readouterr().err
    assert "shutdown: fetcher boom" in err
    assert "shutdown: store boom" in err


async def test_install_and_remove_stop_signal_handlers():
    # Structural check: signal handlers can be installed on the running loop and
    # removed again without error (real SIGTERM/SIGINT delivery is impractical to
    # simulate in a unit test). On this Unix event loop both signals are supported.
    stop_event = asyncio.Event()
    installed = _install_stop_signal_handlers(stop_event)
    assert set(installed) == {signal.SIGTERM, signal.SIGINT}

    _remove_stop_signal_handlers(installed)  # must not raise
