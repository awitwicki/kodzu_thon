FROM python:3.12-trixie
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libgeos-dev \
 && rm -rf /var/lib/apt/lists/*

COPY README.md pyproject.toml ./
COPY src/ ./src/
RUN pip3 install --no-cache-dir .

COPY media/ ./media/

CMD ["python", "-u", "-m", "kodzu_thon"]
