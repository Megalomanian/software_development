FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.9.17 /uv /usr/local/bin/uv

COPY pyproject.toml .
RUN uv sync --frozen --no-dev

COPY . .
RUN uv sync --frozen --no-dev
