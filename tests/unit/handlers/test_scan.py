from kodzu_thon.handlers.scan import (
    _scan_logic,
    _scans_logic,
    _scraps_logic,
)


async def test_scan_edits_with_built_text(fake_event, fake_client, fake_ctx, mocker):
    mocker.patch("kodzu_thon.handlers.scan.build_message_chat_info", return_value="INFO")
    await _scan_logic(fake_event, fake_client, fake_ctx)
    fake_event.edit.assert_awaited_with("INFO")


async def test_scans_sends_to_self_and_deletes(fake_event, fake_client, fake_ctx, mocker):
    mocker.patch("kodzu_thon.handlers.scan.build_message_chat_info", return_value="INFO")
    await _scans_logic(fake_event, fake_client, fake_ctx)
    fake_event.delete.assert_awaited()
    fake_client.send_message.assert_awaited_with("me", "INFO")


async def test_scraps_success_sends_csv(fake_event, fake_client, fake_ctx, mocker):
    mocker.patch("kodzu_thon.handlers.scan.scrap_chat_users", return_value=(True, "/tmp/x.csv"))
    rm = mocker.patch("kodzu_thon.handlers.scan.safe_remove")
    fake_client.send_message.return_value.delete = mocker.AsyncMock()

    await _scraps_logic(fake_event, fake_client, fake_ctx)

    fake_client.send_file.assert_awaited()
    rm.assert_called_once_with("/tmp/x.csv")
