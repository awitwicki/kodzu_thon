from kodzu_thon.app import AppContext, build_app


def test_build_app_constructs_context(mocker, monkeypatch):
    monkeypatch.setenv("TELETHON_API_ID", "1")
    monkeypatch.setenv("TELETHON_API_HASH", "h")
    monkeypatch.setenv("GEMINI_API_KEY", "g")

    mocker.patch("kodzu_thon.app.TelegramClient")
    mocker.patch("kodzu_thon.app.GeminiClient")
    mocker.patch("kodzu_thon.app.Translator")
    mocker.patch("kodzu_thon.app.AirAlarmService")
    mocker.patch("kodzu_thon.app.InfluxWriter")
    mocker.patch("kodzu_thon.app.handlers.register_all")

    _, ctx = build_app()
    assert isinstance(ctx, AppContext)
    assert ctx.settings.api_id == 1
