FROM python:3.12-slim-trixie
WORKDIR /app

# Static ffmpeg/ffprobe: ~260 MB vs ~440 MB for Debian's ffmpeg and its codec/GPU deps.
COPY --from=mwader/static-ffmpeg:7.1.1 /ffmpeg /ffprobe /usr/local/bin/

# Install dependencies before copying src/ so a code change doesn't invalidate this layer.
# basemap ships an x86_64 wheel with libgeos bundled, so no compiler or libgeos-dev is needed.
COPY README.md pyproject.toml ./
RUN pip install --no-cache-dir $(python -c 'import tomllib;print(" ".join(tomllib.load(open("pyproject.toml","rb"))["project"]["dependencies"]))')

COPY src/ ./src/
RUN pip install --no-cache-dir --no-deps .

COPY media/ ./media/

CMD ["python", "-u", "-m", "kodzu_thon"]
