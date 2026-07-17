# Puiky

> Del muisca *pquyquy*: corazón, mente y memoria. Tu segundo cerebro.

Asistente personal de un solo usuario: notas con búsqueda semántica, tareas,
proyectos, responsabilidades recurrentes, finanzas y recordatorios.
Documentación de diseño en [docs/](docs/).

## Estructura

```
backend/    API FastAPI + SQLAlchemy + Alembic (Postgres + pgvector)
frontend/   (Fase 5) interfaz React
docs/       especificación funcional y modelo de datos
```

## Levantar el entorno

Requisitos: Docker (Desktop en Windows, Engine en Ubuntu).

```bash
cp .env.example .env   # y ajustar valores
docker compose up --build
```

- API + Swagger UI: http://localhost:8000/docs

*(Instrucciones detalladas al completar la Fase 1 — en construcción.)*
