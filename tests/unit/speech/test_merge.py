from kodzu_thon.speech.merge import merge_with_background


def test_merge_returns_new_path_and_probes_duration(mocker):
    run = mocker.patch("kodzu_thon.speech.merge.run_ffmpeg")
    mocker.patch("kodzu_thon.speech.merge.probe_duration", return_value=12)
    mocker.patch("kodzu_thon.speech.merge.safe_remove")

    path, dur = merge_with_background("voice.ogg")
    assert path.endswith("voice.ogg") is False  # changed name
    assert path.startswith("new_")
    assert dur == 12
    run.assert_called_once()
