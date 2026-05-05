FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_HTTP_TIMEOUT=120 \
    UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/alembic.ini ./alembic.ini
COPY backend/migrations ./migrations
COPY backend/src ./src
COPY backend/tests ./tests
RUN uv sync --frozen --no-dev

EXPOSE 8000

CMD ["uvicorn", "meeting_mvp_backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
