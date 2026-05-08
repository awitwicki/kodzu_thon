from kodzu_thon.speech.ffmpeg import probe_duration, run_ffmpeg
from kodzu_thon.utils.files import safe_remove


def merge_with_background(audio_file: str, background_file: str = "media/r.ogg") -> tuple[str, int]:
    # Strip the original filename entirely and create a new one
    new_name = "new_merged.ogg"
    run_ffmpeg(
        [
            "-filter_complex",
            f"amovie={audio_file} [a0]; amovie={background_file} [a1]; "
            f"[a0][a1] amix=inputs=2:duration=shortest [aout]",
            "-map",
            "[aout]",
            "-acodec",
            "libopus",
            "-b:a",
            "96K",
            new_name,
        ]
    )
    safe_remove(audio_file)
    return new_name, probe_duration(new_name)
