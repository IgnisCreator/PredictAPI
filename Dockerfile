# Imagen de desarrollo para docker compose; la de producción multi-stage llega en PA-05
FROM ghcr.io/astral-sh/uv:0.12.23-python3.12-trixie-slim
ENV UV_PYTHON_DOWNLOADS=never UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY app ./app
COPY models ./models
COPY migrations ./migrations
EXPOSE 8000
CMD ["uv", "run", "--no-sync", "fastapi", "run", "app/main.py", "--port", "8000"]
