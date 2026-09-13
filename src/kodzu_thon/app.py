import asyncio
import contextlib
import re
import signal
import sys
from dataclasses import dataclass, field

from telethon import TelegramClient
from telethon.tl.functions.account import UpdateProfileRequest

from kodzu_thon import handlers
from kodzu_thon.config import Settings
from kodzu_thon.services.air_alarm import AirAlarmService
from kodzu_thon.services.gemini import GeminiClient
from kodzu_thon.services.media_fetcher import MediaFetcher
from kodzu_thon.services.message_store import MessageStore
from kodzu_thon.services.observability import InfluxWriter
from kodzu_thon.services.translator import Translator
from kodzu_thon.services.two_hundred import TwoHundredService
from kodzu_thon.services.year_progress import get_year_progress


@dataclass
class AppContext:
    gemini: GeminiClient
    translator: Translator
    air_alarm: AirAlarmService
    influx: InfluxWriter
    message_store: MessageStore
    media_fetcher: MediaFetcher
    two_hundred: TwoHundredService
    settings: Settings
    help_lines: list[tuple[str, str]] = field(default_factory=list)
    command_patterns: list[re.Pattern] = field(default_factory=list)


def build_app() -> tuple[TelegramClient, AppContext]:
    settings = Settings.from_env()
    client = TelegramClient(
        settings.session_path, settings.api_id, settings.api_hash, catch_up=True
    )
    message_store = MessageStore(settings.database_url)
    ctx = AppContext(
        gemini=GeminiClient(settings.gemini_api_key),
        translator=Translator(),
        air_alarm=AirAlarmService(settings.geojson_path, img_dir=settings.img_dir),
        influx=InfluxWriter(settings.influx_host, settings.influx_port, settings.influx_db),
        message_store=message_store,
        media_fetcher=MediaFetcher(client, message_store, settings.record_media_max_bytes),
        two_hundred=TwoHundredService(),
        settings=settings,
    )
    handlers.register_all(client, ctx)
    return client, ctx


async def _bio_loop(client: TelegramClient, ctx: AppContext) -> None:
    while True:
        about = get_year_progress()
        last_name = f"{ctx.two_hundred.count():.2f}"
        try:
            await client(UpdateProfileRequest(about=about, last_name=last_name))
        except Exception as e:
            print(f"bio update failed: {e}")
        await asyncio.sleep(ctx.settings.bio_update_interval_s)


def _install_stop_signal_handlers(stop_event: asyncio.Event) -> list[signal.Signals]:
    """Register SIGTERM/SIGINT handlers that set `stop_event`, so a `docker stop` /
    `docker-compose down` (which sends SIGTERM to PID 1 with no TTY involved) makes
    `run_app` reach its shutdown `finally` block instead of being SIGKILLed while
    still blocked inside `run_until_disconnected()`. `add_signal_handler` is only
    implemented on Unix event loops; where it isn't (e.g. Windows), fall back to
    the existing local-dev behavior of relying on KeyboardInterrupt for Ctrl+C."""
    loop = asyncio.get_running_loop()
    installed: list[signal.Signals] = []
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, stop_event.set)
            installed.append(sig)
        except NotImplementedError:
            pass
    return installed


def _remove_stop_signal_handlers(signals: list[signal.Signals]) -> None:
    loop = asyncio.get_running_loop()
    for sig in signals:
        with contextlib.suppress(NotImplementedError):
            loop.remove_signal_handler(sig)


async def _shutdown(bio_task: asyncio.Task, ctx: AppContext, client: TelegramClient) -> None:
    """Run the three shutdown stages, isolating exceptions so a failure in one
    (e.g. the media fetcher) does not prevent the others (e.g. flushing the
    message store's queue) from running."""
    bio_task.cancel()
    for stop in (ctx.media_fetcher.stop, ctx.message_store.stop, client.disconnect):
        try:
            await stop()
        except Exception as e:
            print(f"shutdown: {e}", file=sys.stderr)


async def run_app() -> None:
    client, ctx = build_app()
    await client.start()
    await ctx.message_store.start()
    bio_task = asyncio.create_task(_bio_loop(client, ctx))

    stop_event = asyncio.Event()
    installed_signals = _install_stop_signal_handlers(stop_event)
    try:
        run_task = asyncio.ensure_future(client.run_until_disconnected())
        stop_task = asyncio.ensure_future(stop_event.wait())
        try:
            await asyncio.wait({run_task, stop_task}, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for task in (run_task, stop_task):
                if not task.done():
                    task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await task
    finally:
        _remove_stop_signal_handlers(installed_signals)
        await _shutdown(bio_task, ctx, client)
