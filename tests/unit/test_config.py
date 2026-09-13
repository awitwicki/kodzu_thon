import pytest

from kodzu_thon.config import ConfigError, Settings


def test_from_env_reads_required_and_defaults(monkeypatch):
    monkeypatch.setenv("TELETHON_API_ID", "42")
    monkeypatch.setenv("TELETHON_API_HASH", "abc")
    monkeypatch.setenv("GEMINI_API_KEY", "gem")

    s = Settings.from_env()
    assert s.api_id == 42
    assert s.api_hash == "abc"
    assert s.gemini_api_key == "gem"
    assert s.influx_host == "monitoring_influxdb"


def test_from_env_overrides_optional(monkeypatch):
    monkeypatch.setenv("TELETHON_API_ID", "1")
    monkeypatch.setenv("TELETHON_API_HASH", "h")
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.setenv("INFLUX_HOST", "localhost")
    monkeypatch.setenv("INFLUX_PORT", "9999")

    s = Settings.from_env()
    assert s.influx_host == "localhost"
    assert s.influx_port == 9999


def test_from_env_raises_when_required_missing(monkeypatch):
    monkeypatch.delenv("TELETHON_API_ID", raising=False)
    monkeypatch.setenv("TELETHON_API_HASH", "h")
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    with pytest.raises(ConfigError, match="TELETHON_API_ID"):
        Settings.from_env()


def test_from_env_recorder_defaults(monkeypatch):
    monkeypatch.setenv("TELETHON_API_ID", "1")
    monkeypatch.setenv("TELETHON_API_HASH", "h")
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("RECORD_MEDIA_MAX_BYTES", raising=False)

    s = Settings.from_env()
    assert s.database_url is None
    assert s.record_media_max_bytes == 5 * 1024 * 1024


def test_from_env_recorder_overrides(monkeypatch):
    monkeypatch.setenv("TELETHON_API_ID", "1")
    monkeypatch.setenv("TELETHON_API_HASH", "h")
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db:5432/kodzu_messages")
    monkeypatch.setenv("RECORD_MEDIA_MAX_BYTES", "1024")

    s = Settings.from_env()
    assert s.database_url == "postgresql://u:p@db:5432/kodzu_messages"
    assert s.record_media_max_bytes == 1024


def test_from_env_empty_database_url_means_disabled(monkeypatch):
    monkeypatch.setenv("TELETHON_API_ID", "1")
    monkeypatch.setenv("TELETHON_API_HASH", "h")
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.setenv("DATABASE_URL", "")

    assert Settings.from_env().database_url is None
