# syntax=docker/dockerfile:1
# Build context: ai-data/ml-service/
# Tag + multi-platform digest fixes the base image used by the team.
FROM ghcr.io/astral-sh/uv:0.12.14@sha256:1946145b8706ad9e5c0e79a513f9e324b58d5e38126bb2c8b7dbfca61febeb45 AS uv
FROM python:3.12.13-slim-bookworm@sha256:4766d8b510c428e595d74b9cc5bbb2fae8e26316fffb4adc89908d79aacd58a2 AS build

COPY --from=uv /uv /usr/local/bin/uv
ENV UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1
WORKDIR /app

# Cache dependencies independently of source changes. Never copy the host .venv.
COPY .python-version pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project
COPY README.md ./
COPY src/ ./src/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

# Development keeps the source, editable package and test/lint tools.
# Compose Watch synchronizes src/ and tests/ into these writable paths.
FROM build AS development
COPY tests/ ./tests/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home --shell /bin/sh app \
    && chown -R 10001:10001 /app
ENV PATH="/app/.venv/bin:$PATH" \
    HOME=/home/app \
    UV_CACHE_DIR=/home/app/.cache/uv \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
USER 10001:10001
EXPOSE 8000
# Process liveness only; business/model readiness is added with those features.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).close()"]
CMD ["python", "-m", "uvicorn", "port8282_ml.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app/src"]

FROM python:3.12.13-slim-bookworm@sha256:4766d8b510c428e595d74b9cc5bbb2fae8e26316fffb4adc89908d79aacd58a2 AS runtime
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
USER 10001:10001

EXPOSE 8000
# Liveness only. This does not certify a loaded model or working optimization.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).close()"]
CMD ["python", "-m", "uvicorn", "port8282_ml.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
