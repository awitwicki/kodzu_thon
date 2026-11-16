FROM python:3.12-slim-trixie
WORKDIR /app
# The package runs straight from the source tree: no `pip install .`, which needed the
# network and a wheel build on every code change.
ENV PYTHONPATH=/app/src \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Static ffmpeg/ffprobe: ~260 MB vs ~440 MB for Debian's ffmpeg and its codec/GPU deps.
COPY --from=mwader/static-ffmpeg:7.1.1 /ffmpeg /ffprobe /usr/local/bin/

# Dependencies first, so a code change doesn't invalidate this layer. When pyproject.toml
# does change, the cache mount keeps already-downloaded wheels on the build host.
# basemap ships an x86_64 wheel with libgeos bundled, so no compiler or libgeos-dev is needed.
COPY pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install $(python -c 'import tomllib;print(" ".join(tomllib.load(open("pyproject.toml","rb"))["project"]["dependencies"]))')

COPY media/ ./media/
# Last: the only layer rebuilt by a code change.
COPY src/ ./src/

CMD ["python", "-u", "-m", "kodzu_thon"]
