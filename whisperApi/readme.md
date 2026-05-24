# whisperApi

CPU-only HTTP transcription service using [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2 backend). Exposes `POST /transcribe` returning `{"text": "..."}` and a `GET /health` endpoint on port `4999`.

## Build & run

```sh
docker build -t whisper-api .
docker run -p 4999:4999 -v whisper-models:/models whisper-api
curl -X POST -F "file=@path_to_audio_file.ogg" http://localhost:4999/transcribe
```

Mount a volume on `/models` so the model weights (~1.5 GB for `large-v3-turbo`) survive container rebuilds.

## Configuration (env vars)

| Var | Default | Notes |
|---|---|---|
| `WHISPER_MODEL` | `large-v3-turbo` | `tiny`, `base`, `small`, `medium`, `large-v3`, `large-v3-turbo` |
| `WHISPER_COMPUTE_TYPE` | `int8` | `int8` is fastest on CPU; `float32` for max accuracy |
| `WHISPER_LANGUAGE` | _unset (auto-detect)_ | ISO code, e.g. `uk`, `en`, `ru` — saves a detection pass |
| `WHISPER_BEAM_SIZE` | `1` | `5` is more accurate but 2–3× slower on short clips |
| `WHISPER_CPU_THREADS` | `4` | Match physical thread count (R1600 = 4) |

## Tuning notes for Synology DSM 923+ (R1600, no GPU)

- `large-v3-turbo` + `int8` is the sweet spot — near-`large-v3` accuracy at ~6× the speed.
- Setting `WHISPER_LANGUAGE` is the easiest single speed win if you know the source language.
- VAD filter is always on; it skips silence in voice messages.
- Model is not thread-safe, so gunicorn runs one worker / one thread. Requests serialize.
