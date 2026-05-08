import datetime

from kodzu_thon.speech.ffmpeg import run_ffmpeg


def mount_video(sound_file: str, source_video: str = "media/diesel.mp4") -> str:
    out = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S") + ".mp4"
    run_ffmpeg(
        [
            "-i",
            source_video,
            "-i",
            sound_file,
            "-c:v",
            "copy",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-shortest",
            out,
        ]
    )
    return out
