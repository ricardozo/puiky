# Puiky — Especificación funcional

> Documento de referencia (fuente de verdad) del proyecto. Pensado también como
> contexto inicial para Claude Code. Última actualización: junio 2026.
>
> **Puiky** · del muisca *pquyquy*: corazón, mente y memoria. Tu segundo cerebro.

## 1. El nombre

**Puiky** es una adaptación de *pquyquy* (también *puyquy*), palabra de la lengua
muisca o chibcha, hablada por los pueblos del altiplano cundiboyacense antes de su
extinción hacia el siglo XVIII. En las gramáticas coloniales que la conservan,
*pquyquy* nombra a la vez el **corazón, la mente y el pensamiento**: no separaba el
órgano físico del asiento del entender, el querer y el recordar. Era, literalmente,
el centro de la vida y del pensamiento.

Por eso da nombre a este asistente: un "segundo cerebro" que reúne notas, tareas,
proyectos, finanzas y recordatorios en un solo lugar donde se piensa y se recuerda.
*Puiky* es una grafía simplificada del término original —cuya escritura reconstruida
(*pquyquy*) resulta poco práctica en el uso diario— que conserva su sonido y su raíz,
ganando facilidad para escribirlo y pronunciarlo al hablarle por Telegram.

### Mensaje de bienvenida del bot

> **Hola, soy Puiky**
> El corazón y la mente, el centro donde se piensa y se recuerda.
> Puedo guardar tus notas, organizar tareas y proyectos, llevar tus finanzas y
> recordarte lo que importa. Háblame con naturalidad —por texto o por audio— y yo
> me encargo.
> ¿Por dónde quieres empezar?

## 2. Visión

Un asistente personal de un solo usuario para llevar el control de notas, tareas,
proyectos, responsabilidades recurrentes y finanzas. La interacción principal es
conversacional, por texto y audio, a través de Telegram. Existe además una
interfaz visual tipo Kanban (fase posterior) que lee de la misma base de datos.

El problema que origina el proyecto: hoy se usa Notion para notas y proyectos,
pero encontrar y actualizar información ahí es lento. La meta es poder escribir o
mandar un audio al asistente y que este registre, actualice y, sobre todo,
**recupere contexto por significado**, no solo por palabra exacta.

**El núcleo del sistema son las notas**: la memoria de los proyectos, el "segundo
cerebro". La búsqueda semántica sobre las notas es la funcionalidad más
diferenciadora frente a Notion.

## 3. Principios de diseño

- **Personal, un solo usuario.** Simplifica autenticación y multi-tenencia.
- **Capas desacopladas.** El canal (Telegram) es reemplazable sin tocar el resto.
  El proveedor del modelo de lenguaje también es intercambiable.
- **El sistema no te suelta.** Los recordatorios son escalonados e insistentes,
  pensados para una persona que se concentra mucho en un proyecto y olvida lo demás.
- **Reutilizar conceptos antes que inventar nuevos.** Ej.: el ahorro se resuelve
  con cuentas + transferencias + notas, sin un dominio nuevo de "metas".
- **Privacidad y bajo costo operativo.** El cerebro corre localmente (Qwen) en el
  servidor; los datos personales no salen de ahí.

## 4. Arquitectura (resumen)

Cuatro capas, de abajo hacia arriba:

1. **Backend / cerebro de datos** — API REST en Python. Postgres con `pgvector`
   para búsqueda semántica. Expone operaciones concretas (crear nota, registrar
   gasto, listar tareas de hoy, etc.).
2. **Capa de interpretación (NLU)** — un LLM con *tool/function calling* que mapea
   lenguaje natural a llamadas de la API. Transcripción de audio con Whisper.
   El proveedor del modelo es intercambiable mediante una interfaz interna.
3. **Canal de mensajería** — Telegram Bot API (gratuito, oficial, sin fricción).
   Desacoplado del resto; migrable a WhatsApp en el futuro.
4. **Frontend Kanban (React)** — fase posterior. Lee de la misma API.

Componente transversal: **scheduler** (proceso programado en el servidor) que
revisa vencimientos y dispara recordatorios proactivos por Telegram.

### Alojamiento

Todo el lado servidor (Postgres, API, NLU, bot, scheduler) corre en un servidor
Ubuntu propio, encendido de forma permanente, de modo que el asistente esté
disponible 24/7 sin depender del computador personal. Solo requiere salida a
internet (conexiones salientes hacia Telegram y, si aplica, APIs externas); no
necesita IP pública ni puertos abiertos. Organización recomendada con Docker
(un contenedor para Postgres, otro para la aplicación). El computador personal
queda como entorno de desarrollo.

### Stack confirmado

- Backend y NLU: **Python**
- Base de datos: **Postgres + pgvector**
- Modelo de lenguaje: **Qwen3 14B local** (vía Qwen-Agent / formato Hermes para
  tool calling), con la opción de enrutar casos difíciles a un modelo de API más
  capaz sin reescribir la capa NLU.
- Transcripción: **Whisper** (puede correr localmente).
- Mensajería: **Telegram Bot API**.
- Frontend (fase 2): **React**.
- Desarrollo: **Claude Code** instalado en el servidor vía SSH.

## 5. Dominios funcionales

### 5.1 Notas — núcleo (prioridad alta)

La memoria del sistema. Una nota puede vincularse a un proyecto, una tarea, una
responsabilidad o una cuenta. Búsqueda semántica vía pgvector.

Operaciones:
- Crear nota (con texto libre).
- Vincular una nota a un proyecto / tarea / responsabilidad / cuenta.
- Búsqueda semántica ("¿qué pensé sobre el tema de facturación?").
- Recuperar el contexto de un proyecto (sus notas asociadas).
- Editar / eliminar.

### 5.2 Tareas

Operaciones:
- Crear tarea.
- Marcar avance (porcentaje).
- Marcar completada.
- Listar tareas de hoy.
- Listar pendientes.
- Editar / eliminar.

Campos: título, **estado** (planeada / en ejecución / en pausa / terminada),
porcentaje de avance, fecha límite (opcional), proyecto (opcional).
**Etiquetas: pospuestas** — se añadirán más adelante, no son críticas al arranque.

Los cuatro estados de las tareas son la base del tablero Kanban (ver Proyectos):
cada estado es una columna.

### 5.3 Proyectos

Agrupan tareas y notas.

**Tablero Kanban del proyecto.** El tablero de cada proyecto se genera a partir de
los estados de las tareas: una columna por estado (planeada, en ejecución, en
pausa, terminada). Mover una tarjeta entre columnas cambia el estado de la tarea.

*Orden de las columnas:* es una decisión de presentación del frontend, no del
modelo de datos, por lo que se deja abierta hasta la Fase 5. El usuario trabaja
de derecha a izquierda (terminadas, en ejecución, en pausa, planeadas). El orden
convencional de Kanban es el inverso (planeadas → … → terminadas, de izquierda a
derecha). Recomendación: hacer el orden de columnas **configurable**, y considerar
poder colapsar la columna de terminadas, en lugar de fijar un único orden.

Operaciones:
- Crear proyecto.
- Ver un proyecto con sus tareas y notas.
- Listar proyectos.
- Editar / archivar.

Campos: nombre, descripción, estado (activo / pausado / terminado).

### 5.4 Responsabilidades (compromisos recurrentes)

Distintas de las tareas: son compromisos que se repiten (arriendo, renovaciones).
Al marcar una como cumplida, su próximo vencimiento se recalcula automáticamente
según el patrón de recurrencia.

Operaciones:
- Crear responsabilidad recurrente.
- Marcar cumplida (recalcula el próximo vencimiento).
- Listar próximos vencimientos.

Campos: nombre, patrón de recurrencia (p. ej. mensual, anual, cada N días),
fecha del próximo vencimiento, monto (opcional, si implica un pago).

### 5.5 Finanzas (completo)

Modelo: **cuentas** con saldo, **categorías** y **presupuestos**.

- **Cuentas**: efectivo, banco, ahorros, etc. Cada una tiene un saldo. La cuenta
  de ahorros es una cuenta normal más.
- **Movimientos**: gasto o ingreso. Campos: monto, fecha, categoría, cuenta, nota.
- **Transferencias internas**: mover dinero entre dos cuentas propias (así se
  "aparta" un ahorro de forma explícita; actualiza el saldo de ambas).
- **Categorías**: **fijas pero extensibles.** Se arranca con un conjunto sugerido;
  se pueden añadir nuevas por el bot o por la interfaz. El cerebro debe **mapear**
  expresiones libres ("mercado", "súper") a la categoría fija correspondiente
  ("comida"), y solo crear una categoría nueva cuando se pida explícitamente.
- **Presupuestos**: topes de gasto (definición de granularidad pendiente de
  afinar: por categoría, por cuenta o global del mes). Seguimiento de avance.
- **Ahorro**: NO es un dominio aparte. La *meta* de ahorro es una **nota** asociada
  a la cuenta (información, no dinero); el *movimiento* de ahorro es una
  transferencia interna explícita ordenada por el usuario.

Operaciones:
- Registrar gasto / ingreso.
- Consultar saldo de una cuenta.
- Gastos del mes / por categoría.
- Transferir entre cuentas.
- Definir presupuesto y consultar avance.

### 5.6 Recordatorios escalonados (prioridad alta)

El sistema avisa proactivamente por Telegram, sin que el usuario pregunte. Diseñado
para alguien olvidadizo y propenso a postergar.

Comportamiento:
- **Avisos escalonados**: varios antes del vencimiento (p. ej. varios días antes,
  el día antes, el día de). Cantidad y anticipación configurables.
- **Insistencia**: el recordatorio no desaparece hasta que el asunto se resuelve.
- **Posponer**: "recuérdame mañana" sin que el sistema olvide.
- **Alertas de presupuesto**: avisar al acercarse al tope (p. ej. al 90%).

Implementado por el scheduler en el servidor.

## 6. Ejemplo de flujo end-to-end

Usuario envía un audio por Telegram: *"marca la tarea del informe al 80% y registra
un gasto de 1000 en la cuenta de ahorros"*.

1. **Bot de Telegram** recibe el audio.
2. **NLU**: Whisper transcribe a texto; el LLM (Qwen) detecta dos intenciones y
   produce dos llamadas: `update_task_progress(...)` y `add_expense(...)`.
3. **Backend** ejecuta ambas operaciones sobre Postgres.
4. El resultado vuelve al bot, que responde por Telegram con la confirmación.
5. El **Kanban** (fase 2) reflejará el cambio leyendo de la misma base de datos.

## 7. Plan por fases

1. **Fase 0 — Modelo de datos. (RESUELTA, ver sección 8.)** Tablas y relaciones
   con pgvector para los embeddings de notas.
2. **Fase 1 — Backend / API.** Implementar las operaciones de cada dominio.
3. **Fase 2 — NLU.** Conectar el LLM (Qwen) con tool calling a las operaciones;
   añadir transcripción con Whisper.
4. **Fase 3 — Canal.** Conectar Telegram (texto y audio) end-to-end.
5. **Fase 4 — Scheduler.** Recordatorios escalonados y alertas de presupuesto.
6. **Fase 5 — Frontend Kanban (React).**

## 8. Modelo de datos (Fase 0)

Postgres con la extensión `pgvector`. Identificadores `uuid`. A continuación, las
entidades, sus campos clave y las relaciones.

### Entidades

- **PROJECT** — `id`, `nombre`, `descripcion`, `estado` (activo / pausado /
  terminado). Contiene tareas; puede ser referido por notas.
- **TASK** — `id`, `project_id` (FK, opcional), `titulo`, `estado` (planeada /
  en ejecución / en pausa / terminada), `avance_pct`, `fecha_limite` (opcional).
  Los cuatro estados son las columnas del Kanban.
- **NOTE** — `id`, `contenido`, `embedding` (vector pgvector para búsqueda
  semántica), `creada`. El núcleo del sistema.
- **NOTE_LINK** — tabla de vínculos polimórficos. `id`, `note_id` (FK),
  `entidad_tipo` (project / task / responsibility / account), `entidad_id`.
  Permite que **una nota se vincule a varias cosas a la vez**. Es la base para,
  más adelante, "pintar relaciones entre cosas" estilo Obsidian.
- **RESPONSIBILITY** — `id`, `nombre`, `recurrencia` (p. ej. mensual / anual /
  cada N días), `proximo_venc`, `monto` (opcional).
- **REMINDER** — `id`, `origen_tipo` (task / responsibility / budget, **opcional**),
  `origen_id` (opcional), `texto`, `disparar_en`, `veces_avisado`,
  `pospuesto_para`, `resuelto`. Cubre recordatorios **atados** (con origen) y
  **sueltos** (sin origen, p. ej. "recuérdame llamar a Juan el viernes"). Los
  campos de conteo, posposición y resolución habilitan los avisos escalonados e
  insistentes gestionados por el scheduler.
- **ACCOUNT** — `id`, `nombre`, `tipo` (efectivo / banco / ahorros / …), `saldo`.
  La cuenta de ahorros es una cuenta normal más.
- **CATEGORY** — `id`, `nombre`, `activa`. Categorías fijas pero extensibles.
- **TRANSACTION** — `id`, `tipo` (gasto / ingreso / transferencia), `monto`,
  `account_id` (FK, cuenta origen), `cuenta_destino_id` (FK, solo en
  transferencias), `category_id` (FK), `fecha`, `nota`. El campo `tipo` permite
  **excluir las transferencias de los reportes de gasto**: una transferencia
  mueve saldo entre dos cuentas propias pero no es gasto real.
- **BUDGET** — `id`, `category_id` (FK, **opcional**), `tope`, `periodo`. Si
  `category_id` está lleno, es un presupuesto por categoría ("máx. 500 en comida");
  si va vacío, es el **presupuesto global del mes**. Esto permite **transitar
  gradualmente** de un único tope global (uso actual) a un control detallado por
  categoría, e incluso combinarlos. Genera recordatorios de alerta (p. ej. al 90%).
- **USER** — `id`, `usuario`, `password_hash`, `creado`. Para el login de la
  interfaz web (fase posterior). Aunque el sistema es de un solo usuario, la
  interfaz estará expuesta en el servidor y requiere autenticación. La contraseña
  se guarda siempre como hash, nunca en texto plano. (Se crea en la fase de la
  interfaz; no es necesaria para el backend inicial de notas.)

> **Nota sobre el acceso desde Telegram (no es una entidad):** el bot de Telegram
> y la API corren en el mismo servidor y se comunican internamente, así que no usan
> el login humano de USER. Dos enfoques posibles, a decidir en su fase: (a) la API
> escucha solo en `localhost` y confía en los procesos locales; (b) el componente
> de Telegram se identifica ante la API con una credencial de servicio interna
> (un token de servicio en variable de entorno, distinto del token de sesión del
> usuario web). En ambos casos, la verificación de "quién eres tú" en Telegram ya
> la hace el propio bot mediante la allowlist de IDs de Telegram.

### Relaciones principales

- PROJECT 1—N TASK
- NOTE 1—N NOTE_LINK; cada NOTE_LINK referencia (polimórfico) a PROJECT / TASK /
  RESPONSIBILITY / ACCOUNT
- TASK / RESPONSIBILITY / BUDGET 1—N REMINDER (origen opcional)
- ACCOUNT 1—N TRANSACTION (como cuenta origen); transferencias usan además
  `cuenta_destino_id`
- CATEGORY 1—N TRANSACTION; CATEGORY 1—N BUDGET (relación opcional)

### Decisiones de modelado tomadas

- **Transferencia = una sola fila** de tipo `transferencia` con cuenta origen y
  destino (no dos filas espejo). Suficiente para uso personal.
- **Presupuesto con categoría opcional**: soporta global y por categoría a la vez.
- **Etiquetas pospuestas**: cuando se añadan, entran como una tabla `TAG` más una
  tabla de vínculo análoga a `NOTE_LINK`, sin alterar lo existente.

## 9. Interfaz visual (fases posteriores)

La interfaz no es un visor de solo lectura: es un **cliente completo de la API**,
con las mismas capacidades de consulta y edición que tendría cualquier cliente.
Telegram y la interfaz web son dos formas igual de válidas de operar sobre los
mismos datos (hablar en movimiento, usar el mouse frente al computador).

Decisiones tomadas:

- **Tecnología:** aplicación web responsiva en **React**, que funciona en navegador
  de escritorio y móvil con una sola base de código. Más adelante puede empaquetarse
  como app instalable (PWA) si el uso móvil lo justifica. No se contempla app nativa.
- **Estructura:** un dashboard con navegación lateral y seis secciones (proyectos
  con Kanban, tareas, notas, finanzas, responsabilidades, recordatorios). En móvil,
  la navegación se colapsa y las columnas del Kanban se deslizan horizontalmente.
- **Kanban:** cada proyecto es un tablero; las columnas son los cuatro estados de
  tarea (planeada / en ejecución / en pausa / terminada). Arrastrar una tarjeta
  entre columnas cambia el estado de la tarea vía la API. Orden de columnas
  configurable (ver decisiones abiertas).
- **Crecimiento por dominios, no de golpe:** la interfaz se construye en paralelo
  al backend, una pantalla por dominio. Como el backend arranca por notas, la
  primera pantalla con sentido es la de notas (con su búsqueda semántica), no el
  Kanban. El Kanban llega cuando exista el backend de proyectos y tareas.
- **Autenticación:** login con usuario y contraseña (entidad USER). El usuario se
  autentica y recibe un token de sesión que acompaña cada petición a la API. Aunque
  el sistema sea de un solo usuario, la interfaz estará expuesta en el servidor y
  no debe quedar abierta a quien conozca la URL.

Implicación para el backend (a tener en cuenta desde ya, aunque la interfaz sea
posterior): la API debe quedar diseñada para servir a **dos tipos de cliente** —
el usuario humano vía React (token de sesión) y el bot de Telegram como servicio
interno de confianza (ver la nota sobre acceso desde Telegram en la sección 8).
No hace falta implementar la autenticación en el backend inicial de notas, pero el
diseño de la API no debe asumir un único tipo de llamante.

## 10. Decisiones abiertas

- **Presupuestos: RESUELTO** — categoría opcional (global + por categoría),
  con tránsito gradual. (Ver sección 8.)
- Anticipación y número exacto de recordatorios por defecto (configurable).
- Conjunto inicial de categorías sugeridas.
- Orden de las columnas del Kanban (Fase 5): convencional vs. invertido vs.
  configurable. Recomendación: configurable, con opción de colapsar "terminadas".
- Forma de servir Qwen (vLLM vs Ollama vs otro) y manejo del tamaño de contexto
  para que el tool calling se mantenga fiable.
