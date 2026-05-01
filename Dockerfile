FROM python:3.12-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install dependencies in a builder layer so we can keep the final image
# free of build tooling. README.md is referenced by pyproject.toml's
# `readme = "README.md"` field, so it must be present at install time.
FROM base AS builder
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir .

FROM base AS production

# Copy installed packages from the builder stage.
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Source last so the layer cache invalidates only on src/dashboard changes.
COPY src/ ./src/
COPY dashboard/ ./dashboard/

RUN adduser --disabled-password --no-create-home appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "src.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
