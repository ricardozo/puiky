# Puiky — Arquitectura del agente (y por qué es fluido)

> Documento de referencia y enseñanza. Explica cómo está construido Puiky y, sobre
> todo, **qué decisiones de diseño hacen que su asistente conversacional se sienta
> fluido** — no solo que "funcione". Escrito a partir del código real (`backend/`).
> Actualizado: julio 2026, tras varias semanas de uso real en producción — las
> secciones §4.9–§4.13 son **lecciones ganadas a golpes**, no teoría.

---

## 1. Qué es Puiky

Un asistente personal ("segundo cerebro") **multi-usuario** (schema-per-tenant en
Postgres: una instancia sirve a varias personas y cada una ve solo lo suyo). Guarda
notas, tareas, proyectos, finanzas, mercado, responsabilidades y recordatorios. Se
opera de dos formas sobre **los mismos datos**: hablándole por **Telegram** (texto
o voz) y por una **interfaz web**. Un **scheduler** avisa de forma proactiva.

La pieza diferenciadora es la **capa NLU**: convierte lenguaje natural
("en la hoja de la reunión de hoy añade que definimos el hosting") en llamadas
concretas a operaciones de negocio, de forma que se sienta como hablarle a una
persona, no como llenar un formulario.

---

## 2. Arquitectura por capas

```mermaid
flowchart TB
    subgraph Canales
      TG["Bot de Telegram<br/>(texto y voz)"]
      WEB["Web React<br/>(login JWT)"]
    end
    subgraph NLU["Capa NLU"]
      ORQ["Orquestador"]
      TOOLS["Herramientas (tools)"]
      PROV["LLMProvider<br/>(Qwen / fake)"]
      WHIS["Whisper<br/>(voz→texto)"]
    end
    API["API REST (FastAPI)<br/>+ Auth"]
    SVC["Servicios (lógica de negocio)"]
    DB[("Postgres + pgvector")]
    SCH["Scheduler<br/>(recordatorios proactivos)"]

    TG -->|/nlu| ORQ
    WEB -->|HTTP| API
    ORQ --> PROV
    ORQ --> TOOLS
    TG -.audio.-> WHIS --> ORQ
    TOOLS --> SVC
    API --> SVC
    SVC --> DB
    SCH --> DB
    SCH -->|avisos| TG
```

**Regla de oro:** el canal (Telegram) y el modelo (Qwen) son **reemplazables** sin
tocar el resto. La lógica de negocio vive en **una sola capa** (`services/`) que
usan por igual la API web, las tools del bot y el scheduler. Nada de lógica
duplicada por canal.

- **Datos/API** — FastAPI + SQLAlchemy + Alembic; Postgres con `pgvector` para
  búsqueda semántica de notas. Expone operaciones concretas (crear nota, registrar
  gasto, mover proyecto…).
- **NLU** — un LLM con *tool calling* mapea lenguaje natural a esas operaciones;
  Whisper transcribe la voz.
- **Canal** — bot de Telegram (long-polling, sin puertos abiertos).
- **Scheduler** — proceso aparte que revisa vencimientos y avisa.
- **Web** — React + Tailwind, cliente de la misma API.

---

## 3. El corazón: cómo un mensaje se vuelve acciones

```mermaid
sequenceDiagram
    participant U as Usuario (Telegram)
    participant B as Bot
    participant O as Orquestador
    participant L as LLM (Qwen)
    participant T as Tools → Services
    U->>B: "gasté 20 mil en mercado con efectivo"
    B->>O: interpret(texto, historial)
    O->>L: system(contexto) + historial + user + tools
    L-->>O: tool_calls: registrar_gasto(20000, "mercado", "efectivo")
    O->>T: dispatch → resuelve "mercado"→Comida, "efectivo"→cuenta → crea gasto
    T-->>O: resultado {ok, saldo:80000}
    O->>L: mensajes + resultado (2ª pasada, sin tools)
    L-->>O: "Registré 20.000 en Comida. Saldo: 80.000."
    O-->>B: respuesta + acciones
    B-->>U: responde (y si es borrado, botones Sí/Cancelar)
```

Para **voz**, el bot primero transcribe con Whisper y luego sigue el mismo flujo con
el texto. La memoria de conversación se envía en cada llamada (ver §4.4).

---

## 4. Las decisiones que hacen fluido al agente

Esto es lo importante. Un agente "funciona" con solo exponer tools; se siente
**fluido** por estas decisiones. Cada una incluye el **anti-patrón** que evita.

### 4.1 Las tools son operaciones reales, no un CRUD genérico
Cada herramienta refleja una **intención del usuario** (`registrar_gasto`,
`anadir_a_hoja`, `cumplir_responsabilidad`), no `insertar_fila(tabla, datos)`.
- **Por qué:** el modelo elige mucho mejor entre verbos con significado que entre
  operaciones abstractas; y cada tool encapsula sus reglas (validaciones, efectos).
- **Anti-patrón:** exponer la base de datos cruda o un único `ejecutar_sql`. El
  modelo se pierde y hace cosas peligrosas.
- **Código:** `app/nlu/tools.py` (54 tools), cada una con `handler` → `services/`.

### 4.2 Referencias por nombre/semántica, nunca por ID
El usuario dice "la tarea del informe", "la cuenta de ahorros", "la hoja de la
reunión". Las tools **resuelven** eso a un id internamente (por `ilike` sobre el
título/nombre, o por búsqueda semántica en notas), y si hay ambigüedad **preguntan
cuál**.
- **Por qué:** nadie habla con UUIDs. Sin esto, el agente es inusable para editar
  cosas existentes.
- **Anti-patrón:** que la tool pida un `id`. El modelo lo inventa o falla.
- **Código:** `_resolver_tarea`, `_resolver_hoja`, `_resolver_cuenta`, … en
  `tools.py`. Devuelven error legible si no encuentran o si hay varios.

### 4.3 Inyección de contexto en el system prompt
Antes de cada interpretación, el prompt incluye **el estado volátil relevante**:
fecha/hora actual (para "mañana", "el viernes"), y las **listas** de cuadernos,
portafolios, categorías, cuentas y proyectos del usuario.
- **Por qué:** así el modelo mapea "mercado"→categoría *Comida*, "efectivo"→la
  cuenta real, y "mañana"→fecha ISO **sin preguntar**. Menos fricción, menos
  alucinación.
- **Anti-patrón:** un system prompt estático. El modelo no sabe qué existe y
  pregunta todo o inventa nombres.
- **Código:** `app/nlu/orchestrator.py::_system_prompt(db)`.

### 4.4 Memoria de conversación (multi-turno)
El bot guarda los últimos turnos por chat y los envía en cada petición. Así, cuando
el agente pregunta "¿cuál de los dos ítems?", la respuesta del usuario **tiene
contexto**.
- **Por qué:** sin memoria, cada mensaje se interpreta de cero; las aclaraciones se
  malinterpretan (p. ej. "bórralo" se rutea a la tool equivocada).
- **Anti-patrón:** agente stateless. Rompe cualquier diálogo de dos pasos.
- **Código:** `InterpretRequest.historial`; el bot lo mantiene en
  `context.chat_data` (`app/bot/handlers.py`), el orquestador lo antepone.

### 4.5 Los errores se devuelven como resultado, no como excepción
Si una tool falla (categoría inexistente, cuenta ambigua), devuelve
`{"ok": false, "error": "..."}` en vez de reventar. El modelo **lee ese error** y
se lo explica al usuario en lenguaje natural (o pide el dato que falta).
- **Por qué:** convierte fallos en conversación ("no encontré esa categoría, ¿creo
  una?") en vez de un "error 500".
- **Anti-patrón:** dejar que las excepciones maten el turno.
- **Código:** `tools.py::dispatch` captura `ValueError/KeyError` → resultado.

### 4.6 Confirmación de acciones destructivas
Las tools de borrado **no borran**: devuelven una petición de confirmación
`{"confirmar": {tipo, id, que}}`. El bot muestra botones **Sí/Cancelar**; solo al
tocar "Sí" se borra (vía la API, no vía el modelo).
- **Por qué:** un LLM no debe borrar datos por su cuenta a partir de una frase
  ambigua. Seguridad + confianza.
- **Anti-patrón:** ejecutar el borrado directo desde el tool call.
- **Código:** `_eliminar_*` en `tools.py` (payload `confirmar`);
  `handlers.on_callback` + botones inline; borra con `client.delete_entity`.

### 4.7 Proveedor y modelo intercambiables (real / fake)
`LLMProvider` es una interfaz con dos implementaciones: **real** (endpoint
OpenAI-compatible → Ollama/Qwen) y **fake** (intérprete determinista por reglas).
Lo mismo para Whisper (real/fake) y embeddings (real/fake).
- **Por qué:** se desarrolla y testea **sin** el modelo (rápido, barato, offline), y
  en producción se cambia con una variable de entorno. También permite enrutar
  casos difíciles a un modelo más capaz sin reescribir nada.
- **Anti-patrón:** acoplar el código a un SDK/modelo concreto.
- **Código:** `app/nlu/provider.py`, `transcriber.py`, `embeddings.py`.

### 4.8 Orquestación: una ronda de tools + confirmación natural
El orquestador hace **una** ronda: pide al modelo qué hacer, ejecuta las tools
(pueden ser varias — multi-intención), y hace una **segunda llamada sin tools** solo
para que redacte la confirmación en lenguaje natural con los resultados reales.
- **Por qué:** evita bucles de tools infinitos y da respuestas naturales basadas en
  lo que **de verdad** pasó (saldos, ids), no en lo que el modelo "cree".
- **Anti-patrón:** dejar al modelo iterar sin límite, o narrar sin ver resultados.
- **Código:** `app/nlu/orchestrator.py::interpret`.

### 4.9 ⚠️ La ventana de contexto: el bug silencioso más caro
La lección más importante de producción. **Ollama trunca el prompt en silencio** al
`num_ctx` por defecto (4096 tokens). Nuestro prompt real (system + 67 tools) mide
~7.000: durante semanas el modelo **no veía** parte de las reglas ni de las
herramientas, y la inestabilidad resultante (montos inflados, tools equivocadas,
reglas ignoradas) se atribuía "al modelo".
- **Cómo detectarlo:** mide `prompt_tokens` de una respuesta real. Si da **exacto**
  un número redondo (4096, 8192…), estás truncado.
- **Solución:** la **API nativa de Ollama** (`/api/chat`) permite `options.num_ctx`
  por petición (la OpenAI-compatible no). De paso, `think: false` apaga de verdad
  el razonamiento largo de Qwen3 — el switch suave `/no_think` por prompt **no es
  confiable**. Resultado: 2,5× más rápido **y** más preciso (61,7s → 24,5s).
- **Anti-patrón:** usar el endpoint OpenAI-compatible de Ollama a ciegas y "tunear
  el prompt" para arreglar fallos que en realidad son truncado.
- **Código:** `app/nlu/provider.py::RealLLMProvider` (nativa, `num_ctx`, `think`).

### 4.10 Desconfía del modelo: correcciones deterministas en código
Las reglas de prompt son probabilísticas: el modelo las ignora un % de las veces,
y "una frase más en el prompt" no arregla un fallo repetido. Los fallos conocidos
se corrigen **en código, después del tool call**:
- **Magnitudes:** "130mil" leído como 130.000.000. Se normaliza el texto antes
  ("130mil"→"130 mil") y, si el usuario dijo «N mil» sin mencionar millones y el
  modelo puso N×1.000.000, se corrige a N×1.000.
- **Tool mal elegida:** «recuérdame X cada mes» convertido en otra entidad → se
  re-rutea a la tool correcta detectando el patrón en el texto.
- **Tool calls narrados:** a veces el modelo emite el JSON del tool call **como
  texto** en vez de usar el canal nativo → un regex lo rescata y lo ejecuta.
- **Datos inventados:** categoría inexistente → cae a un valor seguro ('Otros')
  en vez de reventar; el usuario corrige después.
- **Anti-patrón:** iterar el prompt infinitamente esperando obediencia.
- **Código:** `orchestrator.py::_corregir_tool_calls`, `_corregir_magnitud`,
  `_tool_calls_desde_texto`; `tools.py::_resolver_categoria`.

### 4.11 Confirmación también para lo riesgoso (no solo lo destructivo)
Además de los borrados (§4.6), las acciones **de dinero por encima de un umbral**
piden confirmación con botones: la tool devuelve `{"confirmar_gasto": {...}}` en
vez de registrar, y el bot pregunta «⚠️ Es un monto alto. ¿Registro $X…?».
- **Por qué:** es la red de seguridad cuando las correcciones de §4.10 no alcanzan.
  Una mala interpretación **no debe mover dinero** sin un toque humano.
- **Código:** `tools.py::_registrar_movimiento` (umbral), `handlers.py` (botones).

### 4.12 Prompt cacheable: lo volátil va en el mensaje, no en el system
La fecha/hora (con minutos) estaba al inicio del system prompt → **rompía el caché
de prefijo** de Ollama en cada petición y en la 2ª pasada. Se movió al final del
**mensaje del usuario** (`[ahora: …]`): el bloque system+tools queda idéntico entre
llamadas y el servidor lo reutiliza.
- **Regla:** system prompt = todo lo estable (reglas + listas del usuario); lo que
  cambia por minuto va con el mensaje.

### 4.13 Detalles que separan "demo" de "producto"
- **Operaciones compuestas = una transacción.** "Crear nota y vincularla" eran dos
  peticiones; cuando la 2ª fallaba quedaban huérfanas. Ahora la nota nace ya
  vinculada en una sola petición (validando el destino ANTES de crear).
- **Proactividad educada.** La insistencia de recordatorios sin horario despierta
  a la gente a las 3 am: **horario de silencio** configurable (21:00–7:00); lo
  pendiente sale al terminar.
- **Alertas "vivas".** Una alerta generada (p. ej. presupuesto excedido) debe
  **auto-resolverse** cuando su causa desaparece (se corrigió el gasto) y
  **refrescar sus cifras** si siguen cambiando. Texto congelado = spam eterno.
- **Formato por canal.** El modelo emite negrillas Markdown (`**así**`); Telegram
  sin `parse_mode` las muestra literales. Sanitiza la salida según el canal.
- **Multi-tenant por schema (Postgres):** cada `commit` devuelve la conexión al
  pool; si la petición hace un 2º commit, la conexión nueva llega **sin el
  `search_path` del inquilino**. Solución: listener `after_begin` que lo reaplica
  en cada transacción (`app/tenancy.py`).

---

## 5. Componentes en detalle

**NLU (`app/nlu/`)**
- `provider.py` — `LLMProvider` (real/fake). El real habla con la **API nativa de
  Ollama** (`num_ctx` por petición, `think:false`); descarta bloques `<think>`.
- `tools.py` — ~67 tools: esquema (para el modelo) + `handler` (resuelve referencias
  y llama a `services/`). `dispatch()` ejecuta y captura errores.
- `orchestrator.py` — construye el prompt con contexto, normaliza el texto, corre
  la ronda de tools, aplica las **correcciones deterministas** (§4.10) y la segunda
  pasada; recibe el `historial`.
- `transcriber.py` — Whisper (faster-whisper) real/fake.

**Canal (`app/bot/`)**
- `main.py` — arranca el bot (long-polling); registra handlers.
- `handlers.py` — vinculación multi-usuario (`telegram_id → usuario` con código de
  un solo uso `/vincular`), memoria por chat, texto/voz, sanitizado de Markdown, y
  el `CallbackQueryHandler` de los botones de confirmación (borrados y montos altos).
- `client.py` — cliente HTTP a la API (usa un **token de servicio** + cabecera
  `X-Tenant-User`, no el login humano).

**Scheduler (`app/scheduler/`)** — bucle que genera avisos escalonados de
vencimientos, alertas de presupuesto, y entrega recordatorios con insistencia.

**Datos** — `models/` (SQLAlchemy), `services/` (lógica), `routers/` (HTTP),
`alembic/` (migraciones), auth con JWT (usuario web) + token de servicio (bot).

---

## 6. Checklist para hacer un agente fluido (replicable)

1. **Verbos, no CRUD.** Define tools por intención del usuario.
2. **Resuelve referencias por nombre/semántica.** Nunca pidas IDs.
3. **Desambigua.** Si hay varios candidatos, pregunta cuál.
4. **Inyecta contexto** (qué existe: nombres de sus cosas) en el prompt.
5. **Da memoria** de conversación (aunque sean pocos turnos).
6. **Errores como datos**, no como excepciones: el modelo los explica.
7. **Confirma fuera del modelo** lo destructivo Y lo riesgoso (dinero sobre un
   umbral): botones/segundo paso.
8. **Una ronda de tools + respuesta con resultados reales.**
9. **Abstrae el modelo** (interfaz + fake) para desarrollar sin depender de él.
10. **No preguntes lo que ya se dijo** (dilo en el prompt) y **responde breve**.
11. **Mide `prompt_tokens` el primer día.** Si iguala exacto un número redondo
    (4096, 8192…), tu prompt está siendo **truncado en silencio** — la causa nº 1
    de "el modelo es malo". Fija la ventana de contexto explícitamente.
12. **Corrige en código los fallos repetidos del modelo** (magnitudes, tool mal
    elegida, tool calls narrados como texto). El prompt es probabilístico; el
    post-procesamiento es determinista.
13. **Lo volátil (fecha/hora) va en el mensaje del usuario**, no en el system
    prompt: mantén el prefijo system+tools idéntico para que el caché sirva.
14. **Operaciones compuestas en una sola transacción** — nada de "crear y luego
    vincular" en dos peticiones: la segunda fallará algún día y dejará huérfanos.
15. **Proactividad educada:** horario de silencio para los avisos, y alertas que
    se **auto-resuelven** y refrescan sus cifras cuando la causa cambia.
16. **Sanitiza la salida por canal** (Markdown del modelo vs. lo que el canal
    renderiza de verdad).

Los primeros diez hacen que el agente se sienta **natural**; los últimos seis lo
hacen **confiable en producción**. Son la diferencia entre "un agente que llama
funciones" y "un asistente al que le confías tu plata".

---

## 7. Stack e infraestructura

- **Backend/NLU:** Python, FastAPI, SQLAlchemy, Alembic; deps con `uv`.
- **BD:** Postgres + `pgvector`. Embeddings: `multilingual-e5-base` (768 dims).
  **Multi-tenant por schema** (`t_<slug>` por usuario; `public` para control), con
  un único punto de aislamiento (`get_tenant_db` fija el `search_path`).
- **Modelo:** Qwen3 14B local vía **Ollama, API nativa** (`/api/chat`) con
  `options.num_ctx=12288` por petición y `think:false` (ver §4.9). Latencia real:
  ~20–25 s por interpretación (interpretar + confirmar) en hardware modesto.
  Transcripción: Whisper. Ambos intercambiables por variable de entorno.
- **Canal:** Telegram Bot API (long-polling → sin IP pública ni puertos abiertos).
- **Web:** React + Vite + TypeScript + Tailwind; auth JWT (el JWT lleva el tenant).
- **Orquestación:** Docker Compose (Postgres, app, bot, scheduler, migrate).
  Desarrollo en Windows, ejecución en Ubuntu; el código es idéntico (config `.env`).
  Exposición pública vía Cloudflare Tunnel.
- **Seguridad:** dos tipos de llamante — usuario web (JWT tras login, con claim de
  tenant) y bot (token de servicio interno + `X-Tenant-User`). Telegram se protege
  con vinculación por código de un solo uso (`/vincular`), no con allowlist fija.

---

## 8. Por qué "el otro agente" no fluye igual

Si un agente parecido no se siente fluido, casi siempre falta uno de estos:
- Pide **IDs** o datos que el usuario no tiene a mano (falta §4.2/§4.3).
- Es **stateless** y pierde el hilo en cuanto hay una aclaración (falta §4.4).
- Sus tools son **genéricas** o demasiadas sin buenas descripciones (falta §4.1).
- **Revienta** ante un fallo en vez de convertirlo en diálogo (falta §4.5).
- El prompt no le dice **qué existe**, así que pregunta todo o inventa (falta §4.3).
- Su prompt está **truncado en silencio** por la ventana de contexto y nadie lo ha
  medido (falta §4.9) — se manifiesta como "el modelo es tonto a ratos".
- Confía **todo** al prompt y nada al post-procesamiento determinista (falta §4.10):
  los mismos errores vuelven una y otra vez.

La fluidez no viene del modelo; viene de **cómo se le da el contexto, cómo se
resuelven las referencias y cómo se maneja el error y la memoria**. Y la
confiabilidad no viene de un prompt más largo; viene de **medir lo que el modelo
realmente recibe y corregir en código lo que repite mal**.
