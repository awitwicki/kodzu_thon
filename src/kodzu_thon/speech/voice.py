from kodzu_thon.speech.ffmpeg import probe_duration, run_ffmpeg
from kodzu_thon.speech.tts import synthesize_mp3
from kodzu_thon.utils.files import safe_remove


def build_voice(text: str, media_dir: str = "media", background: bool = False) -> tuple[str, int]:
    mp3 = synthesize_mp3(text, media_dir=media_dir)
    ogg = mp3.replace(".mp3", ".ogg")

    run_ffmpeg(
        [
            "-i",
            mp3,
            "-af",
            "volume=13dB",
            "-c:a",
            "libopus",
            "-b:a",
            "96K",
            ogg,
        ]
    )

    output = ogg
    if background:
        merged = ogg.replace(".ogg", "_merged.ogg")
        run_ffmpeg(
            [
                "-filter_complex",
                f"amovie={ogg} [a0]; amovie=media/r.ogg [a1]; "
                f"[a0][a1] amix=inputs=2:duration=shortest [aout]",
                "-map",
                "[aout]",
                "-acodec",
                "libopus",
                "-b:a",
                "96K",
                merged,
            ]
        )
        output = merged
        safe_remove(ogg)

    safe_remove(mp3)
    return output, probe_duration(output)
