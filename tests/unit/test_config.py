import pytest

from kodzu_thon.config import ConfigError, Settings


def test_from_env_reads_required_and_defaults(monkeypatch):
    monkeypatch.setenv("TELETHON_API_ID", "42")
    monkeypatch.setenv("TELETHON_API_HASH", "abc")
    monkeypatch.setenv("GEMINI_API_KEY", "gem")
    monkeypatch.delenv("WHISPER_API_URL", raising=False)

    s = Settings.from_env()
    assert s.api_id == 42
    assert s.api_hash == "abc"
    assert s.gemini_api_key == "gem"
    assert s.whisper_url == "http://whisper:4999/transcribe"
    assert s.influx_host == "monitoring_influxdb"


def test_from_env_overrides_optional(monkeypatch):
    monkeypatch.setenv("TELETHON_API_ID", "1")
    monkeypatch.setenv("TELETHON_API_HASH", "h")
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.setenv("WHISPER_API_URL", "http://other/transcribe")
    monkeypatch.setenv("INFLUX_HOST", "localhost")
    monkeypatch.setenv("INFLUX_PORT", "9999")

    s = Settings.from_env()
    assert s.whisper_url == "http://other/transcribe"
    assert s.influx_host == "localhost"
    assert s.influx_port == 9999


def test_from_env_raises_when_required_missing(monkeypatch):
    monkeypatch.delenv("TELETHON_API_ID", raising=False)
    monkeypatch.setenv("TELETHON_API_HASH", "h")
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    with pytest.raises(ConfigError, match="TELETHON_API_ID"):
        Settings.from_env()
