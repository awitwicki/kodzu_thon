from kodzu_thon.speech.voice import build_voice


def test_build_voice_runs_ffmpeg_and_returns_ogg(mocker, tmp_path):
    mocker.patch("kodzu_thon.speech.voice.synthesize_mp3", return_value=str(tmp_path / "temp.mp3"))
    mocker.patch("kodzu_thon.speech.voice.run_ffmpeg")
    mocker.patch("kodzu_thon.speech.voice.probe_duration", return_value=7)
    mocker.patch("kodzu_thon.speech.voice.safe_remove")

    path, dur = build_voice("hello", media_dir=str(tmp_path), background=False)
    assert path.endswith(".ogg")
    assert dur == 7


def test_build_voice_with_background_makes_extra_call(mocker, tmp_path):
    mocker.patch("kodzu_thon.speech.voice.synthesize_mp3", return_value=str(tmp_path / "temp.mp3"))
    run = mocker.patch("kodzu_thon.speech.voice.run_ffmpeg")
    mocker.patch("kodzu_thon.speech.voice.probe_duration", return_value=3)
    mocker.patch("kodzu_thon.speech.voice.safe_remove")

    path, _ = build_voice("hi", media_dir=str(tmp_path), background=True)
    assert path.endswith("_merged.ogg")
    assert run.call_count >= 2
