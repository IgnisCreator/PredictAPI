# Etapa 1: resuelve e instala las dependencias exactas de uv.lock
FROM ghcr.io/astral-sh/uv:0.12.23-python3.12-trixie-slim AS builder
ENV UV_PYTHON_DOWNLOADS=never UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

# Etapa 2: solo Python, el entorno virtual y el código (sin uv ni herramientas de build)
FROM python:3.12-slim-trixie
# Lambda Web Adapter: permite correr esta misma imagen en AWS Lambda; fuera de Lambda no hace nada
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.9.1 /lambda-adapter /opt/extensions/lambda-adapter
RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY --from=builder /app/.venv ./.venv
COPY app ./app
COPY models ./models
COPY migrations ./migrations
ENV PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    AWS_LWA_READINESS_CHECK_PATH=/health \
    AWS_LWA_ASYNC_INIT=true \
    NUMBA_CACHE_DIR=/tmp
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
