import pytest

from kodzu_thon.speech.ffmpeg import FFmpegError, probe_duration, run_ffmpeg


def test_run_ffmpeg_passes_argv_list_with_shell_false(mocker):
    fake = mocker.patch(
        "kodzu_thon.speech.ffmpeg.subprocess.run",
        return_value=mocker.Mock(returncode=0, stderr=b""),
    )

    run_ffmpeg(["-i", "in.mp3", "out.ogg"])

    args, kwargs = fake.call_args
    assert args[0] == ["ffmpeg", "-i", "in.mp3", "out.ogg"]
    assert kwargs.get("shell", False) is False


def test_run_ffmpeg_raises_on_nonzero_return(mocker):
    mocker.patch(
        "kodzu_thon.speech.ffmpeg.subprocess.run",
        return_value=mocker.Mock(returncode=1, stderr=b"fail"),
    )
    with pytest.raises(FFmpegError):
        run_ffmpeg(["-i", "x.mp3", "y.ogg"])


def test_probe_duration_parses_seconds(mocker):
    fake = mocker.patch(
        "kodzu_thon.speech.ffmpeg.subprocess.run",
        return_value=mocker.Mock(returncode=0, stdout=b"12.345\n"),
    )
    assert probe_duration("x.ogg") == 12

    args, kwargs = fake.call_args
    assert args[0][0] == "ffprobe"
    assert kwargs.get("shell", False) is False
