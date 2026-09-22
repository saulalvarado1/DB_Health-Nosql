# syntax=docker/dockerfile:1.7

FROM python:3.13.15-slim-bookworm AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

COPY pyproject.toml README.md ./
COPY app ./app

RUN python -m pip wheel --wheel-dir /wheels .


FROM python:3.13.15-slim-bookworm AS runtime

LABEL org.opencontainers.image.title="DB Health Monitor Backend" \
      org.opencontainers.image.description="FastAPI API and monitoring worker for MongoDB and Redis"

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home --shell /usr/sbin/nologin app \
    && python -m venv /opt/venv

COPY --from=builder /wheels /wheels
RUN python -m pip install --no-index --find-links=/wheels db-health-monitor \
    && rm -rf /wheels

WORKDIR /app
COPY --chown=app:app alembic.ini ./
COPY --chown=app:app migrations ./migrations

USER 10001:10001
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
