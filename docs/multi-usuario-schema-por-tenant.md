# Multi-usuario: schema por inquilino (schema-per-tenant)

> Diseño para que **una sola instancia** de Puiky (un Docker, una URL, un bot)
> sirva a varias personas con **datos totalmente aislados**, cada quien viendo
> solo lo suyo y usando su propia cuenta de Telegram.
>
> Decisión (2026-07): **schema por usuario**, no filas con `user_id`. El
> aislamiento vive en la base de datos (Postgres schemas), no en filtros de
> consulta → menor superficie de fuga y el código de cada feature sigue siendo
> "de un solo usuario".

---

## 1. Modelo general

- **Schema `public` = control.** Tablas compartidas, no de dominio:
  - `app_user` — login web de cada persona: `id, usuario, password_hash,
    tenant_schema, activo, creado`.
  - `telegram_link` — mapa `telegram_id → app_user`: `telegram_id (PK), user_id,
    activo, creado`.
- **Un schema por usuario** `t_<slug>` (p. ej. `t_ricardozo`, `t_mama`) — contiene
  **todas** las tablas de dominio (notas, cuadernos, proyectos, tareas, finanzas,
  recordatorios, responsabilidades y, a futuro, mercado).
- **La extensión `vector` (pgvector)** se instala una vez en `public`; los tipos
  quedan disponibles para todos los schemas.

```
public:      app_user, telegram_link, alembic_version_control, (extensión vector)
t_ricardozo: notes, notebooks, projects, tasks, accounts, ... , alembic_version
t_mama:      notes, notebooks, projects, tasks, accounts, ... , alembic_version
```

## 2. Cómo se elige el inquilino en cada petición

Un **único punto de aislamiento**: una dependencia `get_tenant_db` que
autentica, resuelve el usuario y fija el `search_path` de la sesión al schema de
ese usuario. Ningún servicio ni consulta cambia — siguen sin saber de tenants.

- **Web:** el login emite un JWT que incluye `sub` (usuario) y `tenant`
  (nombre del schema). En cada petición, `get_tenant_db`:
  1. valida el JWT → obtiene `tenant_schema`;
  2. abre sesión y ejecuta `SET search_path TO "<tenant>", public`;
  3. entrega la sesión.
- **Telegram (bot):** el bot resuelve `telegram_id → app_user` (tabla
  `telegram_link`) y llama a la API con el **token de servicio** + cabecera
  `X-Tenant-User: <user_id>`. `get_tenant_db`, al ver el token de servicio,
  toma el `tenant_schema` del usuario indicado en la cabecera. Un remitente sin
  enlace → **rechazado** (el allowlist deja de existir; el enlace es la fuente).

> El `search_path` se fija por sesión (una por request). Como cada request abre
> su sesión y el tenant se conoce en ese momento, no hay fuga entre peticiones.
> Las consultas de **control** (`app_user`, `telegram_link`) usan tablas
> **calificadas a `public`** para no depender del `search_path`.

## 3. Auth: cambios concretos

- `app_user` pasa a `public` con columnas nuevas: `tenant_schema`, `activo`.
- El JWT incluye `tenant` (schema). `crear_token(usuario, tenant)`.
- `require_auth` se reemplaza por `get_tenant_db` (combina autenticación +
  sesión con `search_path`). Devuelve `(db, principal)` donde `principal`
  identifica al usuario. Los routers dejan de usar `Depends(get_db)` +
  `Depends(require_auth)` y pasan a `Depends(get_tenant_db)`.
- El bot manda `X-Tenant-User`; el token de servicio sigue siendo el candado de
  confianza para ese atajo interno.

## 4. Migraciones (Alembic) multi-schema

Dos cadenas independientes, con **tablas de versión separadas**:

- **Control** (`ControlBase`): `app_user` + `telegram_link`, en `public`,
  con `version_table=alembic_version_control`. Se aplica **una vez**.
- **Dominio** (`Base`, sin `app_user`): se aplica **por cada schema de tenant**,
  con `search_path=<tenant>` y `version_table_schema=<tenant>` (cada schema
  lleva su propio `alembic_version`).

Para evitar arrastrar `app_user` a cada schema (hoy lo crea `0006`), el dominio
se **re-baseliza**: una única migración baseline que refleja el esquema de
dominio actual (todas las tablas menos `app_user`). Las migraciones históricas
`0001–0011` quedan archivadas; el provisioning de nuevos tenants usa el baseline.

`env.py` acepta `-x tenant=<schema>` (o `-x control=1`) para elegir qué cadena y
contra qué schema corre.

**Provisionar un tenant nuevo:**
```
CREATE SCHEMA t_<slug>;
alembic -x tenant=t_<slug> upgrade head     # crea el dominio en ese schema
```

## 5. Migración de los datos actuales (`ricardozo` → tenant #1)

Los datos de producción están hoy en `public`. Migración **única, ensayada
sobre una copia** y con `pg_dump` previo:

1. `CREATE SCHEMA t_ricardozo;`
2. Mover cada tabla de dominio: `ALTER TABLE public.<tabla> SET SCHEMA t_ricardozo;`
   (mueve tabla, secuencias e índices; conserva los datos).
3. En `t_ricardozo`, crear `alembic_version` sellado en el baseline de dominio.
4. En `public`: mantener `app_user` (ya vive ahí), **añadir** `tenant_schema=
   't_ricardozo'`, `activo=true`; crear `telegram_link` e insertar el
   `telegram_id` de ricardozo → su usuario; sellar `alembic_version_control`.
5. Retirar el `alembic_version` viejo de `public` (era del dominio, ya movido).

## 6. Bot (un solo bot para toda la familia)

- **Un bot compartido.** Cada persona usa su propia cuenta de Telegram; el bot
  la distingue por su `telegram_id`. No se opera un bot por persona.
- En cada mensaje: `telegram_id → app_user` (o rechazo). Llama a la API con
  `X-Tenant-User`. La memoria por chat (`chat_data`) ya es por conversación.

## 7. Scheduler

- Itera por **todos los tenants** (lee `app_user` activos), fija `search_path`
  por cada uno, corre los avisos (recordatorios, presupuestos) y notifica al
  chat correcto vía `telegram_link`.

## 8. Alta de un familiar (nuevo flujo, liviano)

Reemplaza al pesado "crear-instancia" (que levantaba un stack Docker entero):

`crear-usuario.sh <slug>`:
1. `CREATE SCHEMA t_<slug>` + `alembic -x tenant=t_<slug> upgrade head`.
2. Crear `app_user` (login web) con su `tenant_schema`.
3. Registrar `telegram_link` con el `telegram_id` de la persona.

Sin puerto nuevo, sin túnel, sin CNAME, sin bot nuevo. Todo sobre la misma
instancia y la misma URL.

## 9. Deploy

El servicio `migrate` del compose pasa a:
1. `alembic -x control=1 upgrade head` (control en `public`).
2. Para cada tenant en `app_user`: `alembic -x tenant=<schema> upgrade head`.

Antes de migrar producción: **backup** (`pg_dump`) y ensayo de la migración de
datos (sección 5) sobre una copia.

## 10. Orden de trabajo y riesgo

Fases 1→6 (ver el plan del chat). Cada una se prueba en **dev** antes de tocar
producción; la migración de datos se ensaya sobre una copia. El punto más
delicado es el §5 (mover datos); por eso va con backup y ensayo.

> **Regla de oro anti-fuga:** solo `get_tenant_db` decide el schema. Ninguna
> consulta de dominio califica schema; ninguna consulta de control depende del
> `search_path` (van calificadas a `public`). Un solo lugar que revisar.
