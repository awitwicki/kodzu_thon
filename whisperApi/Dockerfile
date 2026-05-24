FROM python:3.12-slim-trixie

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

ENV WHISPER_MODEL=large-v3-turbo \
    WHISPER_COMPUTE_TYPE=int8 \
    WHISPER_CPU_THREADS=4 \
    WHISPER_BEAM_SIZE=1 \
    HF_HOME=/models \
    OMP_NUM_THREADS=4

EXPOSE 4999

HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:4999/health',timeout=5).status==200 else 1)"

CMD ["gunicorn", "--bind", "0.0.0.0:4999", "--workers", "1", "--threads", "1", "--timeout", "600", "app:app"]
