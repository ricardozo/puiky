# Puiky

> Del muisca *pquyquy*: corazón, mente y memoria. Tu segundo cerebro.

Asistente personal de un solo usuario: notas con búsqueda semántica, tareas,
proyectos, responsabilidades recurrentes, finanzas y recordatorios.
Documentación de diseño en [docs/](docs/).

**Estado:** Fase 1 (backend / API) **completa** y Fase 2 (**NLU**) con el núcleo
de tool-calling y transcripción de audio. Dominios: **notas** (CRUD, vínculos,
búsqueda semántica con pgvector), **proyectos** y **tareas** (Kanban por estado,
avance/completar, hoy/pendientes), **responsabilidades** (recurrencia que se
recalcula al cumplirse), **finanzas** (cuentas con saldo, categorías, movimientos
con transferencias, reportes de gasto, presupuestos con avance) y **recordatorios**
(posponer, resolver, vencidos). **NLU**: lenguaje natural → acciones, con Qwen
(Ollama) intercambiable por un intérprete `fake`, y audio→texto con Whisper.
**Telegram (Fase 3)**: bot con long-polling que recibe texto y audio, los pasa
por la NLU y responde; seguridad por allowlist de IDs. **Scheduler (Fase 4)**:
proceso que avisa proactivamente por Telegram — recordatorios escalonados (varios
días antes del vencimiento) e insistentes (reitera hasta resolver), más alertas
de presupuesto; zona horaria America/Bogota. Pendientes: entidad USER +
autenticación web y frontend.

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

> **Al cambiar dependencias** (editar `pyproject.toml`): reconstruye la imagen y
> **renueva el volumen del venv**, que si no tapa el nuevo con el viejo:
> `docker compose up -d --build --force-recreate --renew-anon-volumes app`

### Bot de Telegram (Fase 3)

El bot es un servicio aparte (perfil `bot`) que usa long-polling y llama a la API
por HTTP. No necesita IP pública ni puertos abiertos.

1. Crea el bot con [@BotFather](https://t.me/BotFather) y copia el token.
2. En `.env`: `TELEGRAM_BOT_TOKEN=...`. Deja `TELEGRAM_ALLOWED_IDS` vacío la
   primera vez.
3. Levanta el bot: `docker compose --profile bot up -d bot`
4. Mándale un mensaje: te responderá con tu **ID de Telegram**. Ponlo en
   `TELEGRAM_ALLOWED_IDS=<tu_id>` y reinícialo
   (`docker compose --profile bot up -d bot`). Ya solo te atenderá a ti.

Háblale por texto o audio con naturalidad ("gasté 20 mil en mercado con
efectivo"); el bot pasa el mensaje por la capa NLU y responde. Con
`WHISPER_BACKEND=real` transcribe las notas de voz.

El perfil `bot` levanta también el **scheduler** (Fase 4), que avisa
proactivamente: recordatorios escalonados (3/1/0 días antes del vencimiento,
configurable) e insistentes (reitera cada `REMINDER_REALERT_HOURS` hasta que
resuelves), y alertas al superar el `BUDGET_ALERT_THRESHOLD` de un presupuesto.
Todo en zona horaria `TIMEZONE` (America/Bogota).

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

### Endpoints de proyectos

| Método | Ruta | Qué hace |
|--------|------|----------|
| POST   | `/projects`               | Crear proyecto |
| GET    | `/projects`               | Listar (filtro opcional `?estado=`) |
| GET    | `/projects/{id}`          | Ver proyecto con sus tareas y notas |
| PUT    | `/projects/{id}`          | Editar |
| POST   | `/projects/{id}/archive`  | Archivar (estado → terminado) |

### Endpoints de tareas

| Método | Ruta | Qué hace |
|--------|------|----------|
| POST   | `/tasks`                  | Crear tarea |
| GET    | `/tasks`                  | Listar (filtros `?project_id=` `?estado=`) |
| GET    | `/tasks/hoy`              | Vencen hoy o están vencidas y sin terminar |
| GET    | `/tasks/pendientes`       | Todas las no terminadas |
| GET    | `/tasks/{id}`             | Ver tarea |
| PUT    | `/tasks/{id}`             | Editar |
| PATCH  | `/tasks/{id}/progress`    | Marcar avance (%) |
| POST   | `/tasks/{id}/complete`    | Marcar completada (estado → terminada, 100%) |
| DELETE | `/tasks/{id}`             | Eliminar |

**Estados (slugs):** proyecto = `activo` / `pausado` / `terminado`; tarea =
`planeada` / `en_ejecucion` / `en_pausa` / `terminada` (las cuatro columnas del
Kanban). El frontend muestra el texto con acentos; la API usa los slugs.

### Endpoints de responsabilidades

| Método | Ruta | Qué hace |
|--------|------|----------|
| POST   | `/responsibilities`             | Crear compromiso recurrente |
| GET    | `/responsibilities`             | Listar por próximo vencimiento |
| GET    | `/responsibilities/{id}`        | Ver |
| PUT    | `/responsibilities/{id}`        | Editar |
| POST   | `/responsibilities/{id}/fulfill`| Marcar cumplida (recalcula próximo venc.) |
| DELETE | `/responsibilities/{id}`        | Eliminar |

**Recurrencia:** `diaria` / `semanal` / `mensual` / `trimestral` / `anual` /
`cada_<N>_dias`.

### Endpoints de finanzas

| Método | Ruta | Qué hace |
|--------|------|----------|
| POST/GET/PUT | `/accounts` `/accounts/{id}` | Cuentas (crear, listar, ver saldo, editar) |
| POST/GET/PUT | `/categories` `/categories/{id}` | Categorías (extensibles; se desactivan, no se borran) |
| POST   | `/transactions`            | Registrar gasto / ingreso / transferencia (mueve saldos) |
| GET    | `/transactions`            | Listar (filtros `account_id`, `tipo`, `category_id`, `desde`, `hasta`) |
| GET    | `/transactions/reporte`    | Gastos del mes por categoría (excluye transferencias) |
| DELETE | `/transactions/{id}`       | Eliminar (revierte saldos) |
| POST/GET/PUT/DELETE | `/budgets` | Presupuestos (categoría opcional = global) |
| GET    | `/budgets/{id}/progreso`   | Avance: gastado vs. tope en el mes |

**Movimientos:** `tipo` = `gasto` / `ingreso` / `transferencia`. Gasto e ingreso
requieren `category_id`; la transferencia requiere `cuenta_destino_id` y no lleva
categoría.

### Endpoints de recordatorios

| Método | Ruta | Qué hace |
|--------|------|----------|
| POST   | `/reminders`               | Crear (atado a task/responsibility/budget, o suelto) |
| GET    | `/reminders`               | Listar (filtro `?resuelto=`) |
| GET    | `/reminders/vencidos`      | Sin resolver y ya disparados (o pospuestos) |
| GET/PUT| `/reminders/{id}`          | Ver / editar |
| POST   | `/reminders/{id}/snooze`   | Posponer |
| POST   | `/reminders/{id}/notified` | Registrar aviso enviado (para el scheduler) |
| POST   | `/reminders/{id}/resolve`  | Marcar resuelto |
| DELETE | `/reminders/{id}`          | Eliminar |

### Endpoints de NLU (Fase 2)

Traducen lenguaje natural a las operaciones anteriores. Sirven para probar el
tool-calling sin Telegram (el bot de la Fase 3 usará estos mismos).

| Método | Ruta | Qué hace |
|--------|------|----------|
| POST   | `/nlu/interpret`  | Texto → acciones (crea nota, registra gasto, …) |
| POST   | `/nlu/transcribe` | Audio → texto (Whisper) |
| POST   | `/nlu/voice`      | Audio → texto → acciones (flujo del bot) |

**Modelo:** por defecto `LLM_BACKEND=fake` (intérprete determinista, sin modelo).
Para usar el Qwen real, en `.env`: `LLM_BACKEND=real` y `LLM_BASE_URL` apuntando
a Ollama (en el servidor, o vía túnel `ssh -L 11434:localhost:11434 usuario@servidor`).
Igual para el audio: `WHISPER_BACKEND=real`.

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
