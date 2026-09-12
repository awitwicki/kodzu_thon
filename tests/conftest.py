from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def fake_event():
    e = MagicMock()
    e.message = MagicMock()
    e.message.text = ""
    e.message.is_reply = False
    e.message.reply_to_msg_id = None
    e.message.id = 1
    e.message.is_channel = False
    e.message.is_group = False
    e.chat_id = 123
    e._message_id = 1
    e.is_private = False
    e.is_group = False
    e.voice = None
    e.edit = AsyncMock()
    e.delete = AsyncMock()
    e.get_chat = AsyncMock(return_value=MagicMock(id=123, title="Test"))
    e.get_reply_message = AsyncMock(return_value=None)
    e.message.get_reply_message = AsyncMock(return_value=None)
    e.download_media = AsyncMock(return_value="/tmp/fake.ogg")
    e.message.download_media = AsyncMock(return_value="/tmp/fake.ogg")
    return e


@pytest.fixture
def fake_client():
    c = AsyncMock()
    c.send_message = AsyncMock()
    c.send_file = AsyncMock()
    c.iter_messages = MagicMock()
    c.action = MagicMock()
    c.get_participants = AsyncMock(return_value=[])
    return c


@pytest.fixture
def fake_settings():
    s = MagicMock()
    s.version = "v1.17.0"
    s.api_id = 1
    s.api_hash = "hash"
    s.gemini_api_key = "gemini-key"
    s.influx_host = "monitoring_influxdb"
    s.influx_port = 8086
    s.influx_db = "bots"
    s.session_path = "session_data/session_name"
    s.geojson_path = "media/ukraine-with-regions_1530.geojson"
    s.media_dir = "media"
    s.img_dir = "img"
    s.bio_update_interval_s = 300
    return s


@pytest.fixture
def fake_ctx(fake_settings):
    ctx = MagicMock()
    ctx.gemini = AsyncMock()
    ctx.translator = AsyncMock()
    ctx.air_alarm = MagicMock()
    ctx.influx = MagicMock()
    ctx.message_cache = MagicMock()
    ctx.two_hundred = MagicMock()
    ctx.settings = fake_settings
    ctx.help_lines = []
    return ctx
