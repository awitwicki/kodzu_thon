import os
from dataclasses import dataclass


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Settings:
    api_id: int
    api_hash: str
    gemini_api_key: str
    session_path: str = "session_data/session_name"
    whisper_url: str = "http://whisper:4999/transcribe"
    influx_host: str = "monitoring_influxdb"
    influx_port: int = 8086
    influx_db: str = "bots"
    geojson_path: str = "media/ukraine-with-regions_1530.geojson"
    media_dir: str = "media"
    img_dir: str = "img"
    version: str = "v1.18.3"
    bio_update_interval_s: int = 300

    @classmethod
    def from_env(cls) -> "Settings":
        def required(name: str) -> str:
            v = os.environ.get(name)
            if not v:
                raise ConfigError(f"Missing required env var: {name}")
            return v

        return cls(
            api_id=int(required("TELETHON_API_ID")),
            api_hash=required("TELETHON_API_HASH"),
            gemini_api_key=required("GEMINI_API_KEY"),
            session_path=os.environ.get("SESSION_PATH", cls.session_path),
            whisper_url=os.environ.get("WHISPER_API_URL", cls.whisper_url),
            influx_host=os.environ.get("INFLUX_HOST", cls.influx_host),
            influx_port=int(os.environ.get("INFLUX_PORT", cls.influx_port)),
        )
