import os
import tempfile

from faster_whisper import WhisperModel
from flask import Flask, jsonify, request

MODEL_SIZE = os.environ.get("WHISPER_MODEL", "large-v3-turbo")
COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")
LANGUAGE = os.environ.get("WHISPER_LANGUAGE") or None
BEAM_SIZE = int(os.environ.get("WHISPER_BEAM_SIZE", "1"))
CPU_THREADS = int(os.environ.get("WHISPER_CPU_THREADS", "4"))
PORT = int(os.environ.get("PORT", "4999"))

app = Flask(__name__)

model = WhisperModel(
    MODEL_SIZE,
    device="cpu",
    compute_type=COMPUTE_TYPE,
    cpu_threads=CPU_THREADS,
    num_workers=1,
)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "model": MODEL_SIZE,
        "compute_type": COMPUTE_TYPE,
        "language": LANGUAGE or "auto",
    })


@app.route("/transcribe", methods=["POST"])
def transcribe():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    upload = request.files["file"]
    suffix = os.path.splitext(upload.filename or "")[1]
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        upload.save(tmp.name)
        tmp_path = tmp.name

    try:
        segments, _info = model.transcribe(
            tmp_path,
            language=LANGUAGE,
            beam_size=BEAM_SIZE,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
            condition_on_previous_text=False,
        )
        text = "".join(segment.text for segment in segments).strip()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    return jsonify({"text": text})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
