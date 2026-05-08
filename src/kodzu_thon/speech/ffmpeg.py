import subprocess


class FFmpegError(Exception):
    pass


def run_ffmpeg(args: list[str]) -> None:
    cmd = ["ffmpeg", *args]
    result = subprocess.run(cmd, capture_output=True, shell=False)
    if result.returncode != 0:
        raise FFmpegError(result.stderr.decode(errors="replace"))


def probe_duration(path: str) -> int:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, shell=False)
    if result.returncode != 0:
        return 0
    text = result.stdout.decode(errors="replace").strip()
    return int(float(text)) if text else 0
