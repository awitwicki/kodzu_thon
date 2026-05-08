import asyncio
from dataclasses import dataclass, field

from telethon import TelegramClient
from telethon.tl.functions.account import UpdateProfileRequest

from kodzu_thon import handlers
from kodzu_thon.config import Settings
from kodzu_thon.services.air_alarm import AirAlarmService
from kodzu_thon.services.gemini import GeminiClient
from kodzu_thon.services.message_cache import MessageCache
from kodzu_thon.services.observability import InfluxWriter
from kodzu_thon.services.translator import Translator
from kodzu_thon.services.two_hundred import TwoHundredService
from kodzu_thon.services.whisper import WhisperClient
from kodzu_thon.services.year_progress import get_year_progress


@dataclass
class AppContext:
    gemini: GeminiClient
    whisper: WhisperClient
    translator: Translator
    air_alarm: AirAlarmService
    influx: InfluxWriter
    message_cache: MessageCache
    two_hundred: TwoHundredService
    settings: Settings
    help_lines: list[tuple[str, str]] = field(default_factory=list)


def build_app() -> tuple[TelegramClient, AppContext]:
    settings = Settings.from_env()
    client = TelegramClient(settings.session_path, settings.api_id, settings.api_hash)
    ctx = AppContext(
        gemini=GeminiClient(settings.gemini_api_key),
        whisper=WhisperClient(settings.whisper_url),
        translator=Translator(),
        air_alarm=AirAlarmService(settings.geojson_path, img_dir=settings.img_dir),
        influx=InfluxWriter(settings.influx_host, settings.influx_port, settings.influx_db),
        message_cache=MessageCache(),
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


async def run_app() -> None:
    client, ctx = build_app()
    await client.start()
    bio_task = asyncio.create_task(_bio_loop(client, ctx))
    try:
        await client.run_until_disconnected()
    finally:
        bio_task.cancel()
        await client.disconnect()
