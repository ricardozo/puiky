# Puiky: resumen para un agente de código

Puiky es un asistente personal multiusuario (familia del dueño, en Colombia, todo en español) que funciona como "segundo cerebro": notas, proyectos y tareas, registro de tiempo, finanzas, mercado, pagos recurrentes y recordatorios. Se usa por una web y por un bot conversacional (Telegram y WhatsApp) que entiende lenguaje natural y voz.

Este documento describe qué hace y cómo está construido, para que puedas trabajar en el repo sin redescubrirlo. El diseño del agente conversacional está en detalle en [arquitectura-agente.md](arquitectura-agente.md); el manual para usuarios finales, en [manual-usuario.md](manual-usuario.md).

## Stack y despliegue

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, gestor `uv` |
| Base de datos | PostgreSQL 16 + pgvector (imagen `pgvector/pgvector:pg16`) |
| Frontend | React + Vite + TypeScript + Tailwind, gestor **pnpm** (npm falla por el protocolo `workspace:`) |
| LLM | Qwen3 14B en Ollama, servidor de la LAN, vía API **nativa** `/api/chat` |
| Embeddings | `multilingual-e5-base` (768 dim) con sentence-transformers |
| Voz | faster-whisper (modelo configurable, `WHISPER_MODEL`) |
| Canales | Telegram (python-telegram-bot) y WhatsApp (Meta Cloud API, Graph v21.0) |

Servicios Docker (`docker-compose.yml` en dev, `docker-compose.prod.yml` en prod): `db`, `migrate` (corre `app.migrate_all` y sale), `app` (uvicorn), `bot` (Telegram), `scheduler` (bucle cada 60 s) y `web` (nginx que sirve el SPA y hace proxy de `/api/*` a `app:8000`).

- **Dev**: Windows, `http://localhost`, contenedores `puiky-app-1`, `puiky-db-1`. Inquilinos de prueba `t_dev` (usuario ricardo) y `t_demo`.
- **Prod**: Ubuntu, `/opt/puiky/instances/ricardozo`, proyecto compose `puiky-ricardozo`, https://puiky.iconred.co. Despliegue: `git pull origin main && docker compose -p puiky-ricardozo -f docker-compose.prod.yml up -d --build`.

## Multiusuario: un schema por inquilino

- Schema `public` = **control**: usuarios (`app_user`), vínculos de Telegram (`telegram_link`) y WhatsApp (`whatsapp_link`).
- Un schema `t_<slug>` por usuario = **dominio**: todas sus notas, tareas, finanzas, etc.
- `app/tenancy.py::get_tenant_db` autentica (JWT de la web, o token de servicio + cabecera `X-Tenant-User` con el UUID del usuario, que usan bot y scheduler) y fija el `search_path` al schema del inquilino.
- **Gotcha crítico**: un `commit()` intermedio pierde el `search_path`. Un listener `after_begin` lo reaplica en cada transacción. No lo quites.
- Dos cadenas de Alembic: `control_000N` (una vez) y `domain_00NN` (por cada inquilino). `python -m app.migrate_all` aplica ambas a todos.
- **Las migraciones de dominio deben ser idempotentes** (`ADD COLUMN IF NOT EXISTS`, `CREATE TABLE IF NOT EXISTS`): al aprovisionar un inquilino nuevo, el baseline crea las tablas desde los modelos actuales y luego corren todas las migraciones. Última: `domain_0017`.

## Módulos funcionales

Cada dominio sigue el patrón `models/` → `schemas/` → `services/` (lógica, lanza `ValueError` que el router traduce a 400) → `routers/`. La web consume la API desde `frontend/src/api.ts`.

### Notas y cuadernos
Hojas con título y contenido, agrupadas en cuadernos. Cada nota guarda un embedding para **búsqueda semántica** (pgvector, distancia coseno). Las notas se pueden **vincular** a proyectos o tareas (`note_link`); crear y vincular es atómico. Cada proyecto nace con su **cuaderno de proyecto** (mismo nombre, se renombra con él).

### Portafolios, proyectos y tareas
- **Portafolio** agrupa proyectos. **Proyecto** tiene descripción, fechas de inicio/fin, estado (activo/pausado/terminado = archivado) y avance (tareas terminadas / total). Se borran solo vacíos.
- **Personal** (`es_personal`) es un proyecto real por inquilino que recibe las tareas sin proyecto; no se puede borrar. **Vida** se siembra con tareas permanentes para cronometrar (familia, entretenimiento, estudio).
- **Tarea**: Kanban de 4 estados (planeada, en_ejecucion, en_pausa, terminada), checklist reordenable (el avance se calcula del checklist), fechas planeadas/reales, notas, **prioridad** (alta/media/baja) y **foco del día** (`foco_fecha` = hoy; se limpia sola al cambiar de día y al completar).
- **Tareas recurrentes**: al completarlas no terminan, se reciclan (vuelven a planeada y la fecha límite avanza un periodo).
- Web: tablero Kanban por proyecto y página **Tareas** con dos vistas: *Por proyecto* y *🎯 Foco* (foco de hoy, vencidas, prioridad alta, próximos 3 días).

### Registro de tiempo
Tabla `time_entry` (tarea, inicio, fin; `fin` NULL = corriendo). **Una sola sesión activa**: iniciar otra cierra la anterior. Cronometrar **nunca completa** la tarea. Pomodoro configurable (45 min por defecto, preferencia del navegador) que viaja con la sesión (`aviso_min`); el scheduler avisa por Telegram al cumplirse. Página **Tiempo** con botones por tarea, sesiones editables por día y consolidado mensual por tarea y proyecto. También se inicia/para desde cada fila de Tareas y desde la tarea abierta.

### Finanzas
- **Cuentas** con saldo (se renombran; las que están en cero se borran, o se archivan si tienen movimientos).
- **Movimientos**: gasto, ingreso o transferencia. El saldo se mantiene en el servicio: crear aplica, editar revierte y reaplica (incluido cambiar el tipo, también a/desde transferencia), borrar revierte. `fecha` contable + `creado` (orden de registro dentro del día).
- **Categorías** (se desactivan, no se borran) y **presupuestos** por categoría o global, con alertas al cruzar el umbral.
- Web: por categoría con totales del periodo (mes o rango libre), filtros de movimientos, exportar a Excel.

### Responsabilidades (pagos recurrentes)
Compromisos con recurrencia (`unica`, diaria, semanal, mensual, bimestral, trimestral, anual, `cada_N_dias`), monto, cuenta y categoría opcionales, y **cuotas** opcionales. **Registrar pago** crea el gasto en finanzas, avanza el vencimiento y apaga los avisos; si es única o era la última cuota, la responsabilidad desaparece. Resumen en equivalente mensual por categoría.

### Mercado
Productos con cadencia de compra; el sistema **aprende el ciclo** real y estadísticas de precio de las compras registradas, y avisa cuándo toca reponer. **Modo compra**: lista del súper, marcar comprado con precio, cerrar la compra con una cuenta (crea el gasto).

### Recordatorios
- Manuales (con recurrencia opcional) y automáticos generados por el scheduler: escalera de avisos para tareas y responsabilidades (3, 1 y 0 días antes, a las 9:00), presupuestos y mercado.
- Los de tareas/responsabilidades calculan su **texto en vivo** contra el vencimiento real ("vence en 3 días", "venció hace 6 días").
- Entrega por Telegram con **insistencia** (reaviso cada N horas hasta resolver) y **horario de silencio** (21:00–07:00, salvo pomodoros).

## El bot conversacional (NLU)

- Entrada: texto o nota de voz (transcrita con Whisper) por Telegram o WhatsApp. El bot llama a la API con token de servicio.
- `app/nlu/orchestrator.py::interpret` arma un prompt de sistema con el contexto del usuario (cuentas, categorías, proyectos, productos, responsabilidades), llama a Qwen con **71 herramientas** (`app/nlu/tools.py`), ejecuta las tool calls y redacta la respuesta.
- `num_ctx` = 12288 (con la API OpenAI-compatible de Ollama el prompt se truncaba en silencio a 4096) y `think: false`.
- **Guardias deterministas** que corrigen fallos conocidos del modelo, sin depender del prompt:
  - montos pegados y magnitud ("130mil" nunca es 130 millones);
  - "recuérdame…" siempre es recordatorio, no responsabilidad;
  - tool calls emitidas como texto se rescatan;
  - **éxito alucinado**: si el usuario pidió una acción y el modelo responde solo con texto, se reintenta y si no, se responde con un fallo honesto;
  - confirmaciones de dinero se redactan desde los resultados reales, no por el LLM;
  - el pomodoro inventado ("25 min") se descarta si el usuario no dijo minutos.
- Gastos grandes (≥ 5.000.000) piden confirmación con botones.
- Vinculación: el usuario envía `/vincular <código>` (códigos de un solo uso con `python -m app.enroll_code <usuario>`).

## Convenciones del repo

- Código, comentarios, commits y UI en **español**. Montos colombianos: `$1.234.567`.
- Zona horaria `America/Bogota`; usa `app.timeutils.now_local()` y `zona()`, no `datetime.now()` a secas.
- Commits estilo `feat(area): …` / `fix(area): …` con cuerpo explicativo.
- Tests: `docker exec puiky-app-1 python -m pytest tests/ -q`. Typecheck web: `cd frontend && pnpm exec tsc -b`.
- Para probar lógica contra la base de dev: abrir `SessionLocal()`, `_set_search_path(db, "t_dev")` y `db.info["tenant_schema"] = "t_dev"`, y limpiar los datos de prueba al final.

## Trampas operativas conocidas

- Tras recrear el contenedor `app`, nginx (`web`) puede quedar apuntando a la IP vieja: la web carga pero el login falla. Arreglo: `restart web`.
- Tras un deploy, el navegador puede servir la versión vieja del SPA: Ctrl+Shift+R.
- La base de prod no se llama `puiky`: usar `$POSTGRES_USER` / `$POSTGRES_DB` dentro del contenedor `db`.
- WhatsApp solo permite mensajes libres dentro de la ventana de 24 h desde el último mensaje del usuario; la app de Meta debe estar publicada y suscrita al WABA (`POST /{waba}/subscribed_apps`). Los avisos proactivos hoy solo salen por Telegram.
