from kodzu_thon.speech.video import mount_video


def test_mount_video_calls_ffmpeg_with_argv(mocker):
    run = mocker.patch("kodzu_thon.speech.video.run_ffmpeg")
    out = mount_video("sound.ogg", source_video="media/diesel.mp4")
    assert out.endswith(".mp4")
    args, _ = run.call_args
    assert "-i" in args[0]
    assert "media/diesel.mp4" in args[0]
    assert "sound.ogg" in args[0]
