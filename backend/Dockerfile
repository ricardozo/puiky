# Imagen de la app Puiky. Idéntica en Windows (desarrollo) y Ubuntu (producción).
FROM python:3.12-slim

# uv: gestor de dependencias (binario copiado desde su imagen oficial)
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /uvx /bin/

# No escribir .pyc, salida sin buffer, y venv del proyecto en ruta fija
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# 1) Instalar dependencias primero (capa cacheada mientras no cambie el lock).
# Sin `--mount=type=cache` para no depender de BuildKit (portable al builder clásico).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# 2) Copiar el código y terminar la instalación
COPY . .
RUN uv sync --frozen

# Ejecutar dentro del venv sin escribir "uv run" en cada comando
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
