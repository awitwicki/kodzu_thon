import datetime
import os

from gtts import gTTS


def synthesize_mp3(text: str, media_dir: str = "media", lang: str = "ru") -> str:
    os.makedirs(media_dir, exist_ok=True)
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(media_dir, f"temp{timestamp}.mp3")
    gTTS(text, lang=lang).save(path)
    return path
