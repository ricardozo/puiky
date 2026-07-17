# Puiky

> Del muisca *pquyquy*: corazón, mente y memoria. Tu segundo cerebro.

Asistente personal de un solo usuario: notas con búsqueda semántica, tareas,
proyectos, responsabilidades recurrentes, finanzas y recordatorios.
Documentación de diseño en [docs/](docs/).

**Estado:** Fase 1 en curso. Dominio de **notas** completo (CRUD, vínculos y
búsqueda semántica con pgvector). Los demás dominios y el frontend llegan en
fases siguientes.

## Estructura

```
backend/    API FastAPI + SQLAlchemy + Alembic (Postgres + pgvector)
  app/
    models/     tablas SQLAlchemy (una por dominio)
    schemas/    contratos Pydantic
    services/   lógica de negocio (independiente del canal)
    routers/    endpoints HTTP
    embeddings.py  servicio de embeddings (real / fake)
  alembic/    migraciones
frontend/   (Fase 5) interfaz React — aún no creada
docs/        especificación funcional y modelo de datos
```

## Requisitos

- Docker (Desktop en Windows, Engine en Ubuntu). Nada más: Python, Postgres y
  el modelo de embeddings viven dentro de los contenedores.

## Levantar el entorno (un comando)

```bash
cp .env.example .env          # ajusta credenciales si quieres
docker compose up --build     # construye y levanta db + app
```

En **otra terminal**, aplica las migraciones (crea las tablas y la extensión
pgvector):

```bash
docker compose exec app alembic upgrade head
```

Listo. Idéntico en Windows y Ubuntu.

- **Swagger UI (probar todo sin frontend):** http://localhost:8000/docs
- Chequeo de vida: http://localhost:8000/health

> La primera vez, el backend `real` de embeddings descarga
> `multilingual-e5-base` (~1 GB) y lo guarda en un volumen; los siguientes
> arranques son inmediatos. Para desarrollo sin descarga, pon `EMBED_BACKEND=fake`
> en `.env` (vectores deterministas, sin medir significado real).

## Probar la búsqueda semántica (ejemplo)

Crea tres notas de temas distintos:

```bash
curl -X POST localhost:8000/notes -H 'Content-Type: application/json' \
  -d '{"contenido":"Reunion con el cliente sobre el problema de la facturacion mensual"}'
curl -X POST localhost:8000/notes -H 'Content-Type: application/json' \
  -d '{"contenido":"Comprar leche, pan y huevos en el supermercado"}'
curl -X POST localhost:8000/notes -H 'Content-Type: application/json' \
  -d '{"contenido":"Idea: automatizar el envio de facturas a los clientes cada mes"}'
```

Busca por significado (sin usar las mismas palabras):

```bash
curl -X POST localhost:8000/notes/search -H 'Content-Type: application/json' \
  -d '{"texto":"como van los cobros pendientes a los clientes","limite":3}'
```

Las dos notas sobre facturación/clientes aparecen arriba (mayor `similitud`) y
la del supermercado queda al final, aunque la consulta no repite sus palabras:
esa es la diferencia frente a una búsqueda por texto exacto.

## Endpoints de notas

| Método | Ruta | Qué hace |
|--------|------|----------|
| POST   | `/notes`              | Crear nota (genera su embedding) |
| GET    | `/notes`              | Listar notas |
| GET    | `/notes/{id}`         | Ver una nota con sus vínculos |
| PUT    | `/notes/{id}`         | Editar (recalcula el embedding) |
| DELETE | `/notes/{id}`         | Eliminar (borra sus vínculos en cascada) |
| POST   | `/notes/{id}/links`   | Vincular a project / task / responsibility / account |
| POST   | `/notes/search`       | Búsqueda semántica |

## Tests

```bash
docker compose exec app pytest -q
```

## Migraciones

```bash
docker compose exec app alembic upgrade head     # aplicar
docker compose exec app alembic downgrade -1     # revertir la última
# crear una nueva a partir de cambios en los modelos:
docker compose exec app alembic revision --autogenerate -m "descripcion"
```

## Configuración (`.env`)

Todo se lee del entorno; nada queda quemado en el código (portable Windows ↔
Ubuntu). Ver [.env.example](.env.example): credenciales de Postgres, puerto de
la API, modelo/dimensión de embeddings y `EMBED_BACKEND` (`real` | `fake`).
