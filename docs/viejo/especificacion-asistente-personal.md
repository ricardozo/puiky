# Asistente personal — Especificación funcional

> Documento de referencia (fuente de verdad) del proyecto. Pensado también como
> contexto inicial para Claude Code. Última actualización: junio 2026.

## 1. Visión

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

## 2. Principios de diseño

- **Personal, un solo usuario.** Simplifica autenticación y multi-tenencia.
- **Capas desacopladas.** El canal (Telegram) es reemplazable sin tocar el resto.
  El proveedor del modelo de lenguaje también es intercambiable.
- **El sistema no te suelta.** Los recordatorios son escalonados e insistentes,
  pensados para una persona que se concentra mucho en un proyecto y olvida lo demás.
- **Reutilizar conceptos antes que inventar nuevos.** Ej.: el ahorro se resuelve
  con cuentas + transferencias + notas, sin un dominio nuevo de "metas".
- **Privacidad y bajo costo operativo.** El cerebro corre localmente (Qwen) en el
  servidor; los datos personales no salen de ahí.

## 3. Arquitectura (resumen)

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

## 4. Dominios funcionales

### 4.1 Notas — núcleo (prioridad alta)

La memoria del sistema. Una nota puede vincularse a un proyecto, una tarea, una
responsabilidad o una cuenta. Búsqueda semántica vía pgvector.

Operaciones:
- Crear nota (con texto libre).
- Vincular una nota a un proyecto / tarea / responsabilidad / cuenta.
- Búsqueda semántica ("¿qué pensé sobre el tema de facturación?").
- Recuperar el contexto de un proyecto (sus notas asociadas).
- Editar / eliminar.

### 4.2 Tareas

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

### 4.3 Proyectos

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

### 4.4 Responsabilidades (compromisos recurrentes)

Distintas de las tareas: son compromisos que se repiten (arriendo, renovaciones).
Al marcar una como cumplida, su próximo vencimiento se recalcula automáticamente
según el patrón de recurrencia.

Operaciones:
- Crear responsabilidad recurrente.
- Marcar cumplida (recalcula el próximo vencimiento).
- Listar próximos vencimientos.

Campos: nombre, patrón de recurrencia (p. ej. mensual, anual, cada N días),
fecha del próximo vencimiento, monto (opcional, si implica un pago).

### 4.5 Finanzas (completo)

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

### 4.6 Recordatorios escalonados (prioridad alta)

El sistema avisa proactivamente por Telegram, sin que el usuario pregunte. Diseñado
para alguien olvidadizo y propenso a postergar.

Comportamiento:
- **Avisos escalonados**: varios antes del vencimiento (p. ej. varios días antes,
  el día antes, el día de). Cantidad y anticipación configurables.
- **Insistencia**: el recordatorio no desaparece hasta que el asunto se resuelve.
- **Posponer**: "recuérdame mañana" sin que el sistema olvide.
- **Alertas de presupuesto**: avisar al acercarse al tope (p. ej. al 90%).

Implementado por el scheduler en el servidor.

## 5. Ejemplo de flujo end-to-end

Usuario envía un audio por Telegram: *"marca la tarea del informe al 80% y registra
un gasto de 1000 en la cuenta de ahorros"*.

1. **Bot de Telegram** recibe el audio.
2. **NLU**: Whisper transcribe a texto; el LLM (Qwen) detecta dos intenciones y
   produce dos llamadas: `update_task_progress(...)` y `add_expense(...)`.
3. **Backend** ejecuta ambas operaciones sobre Postgres.
4. El resultado vuelve al bot, que responde por Telegram con la confirmación.
5. El **Kanban** (fase 2) reflejará el cambio leyendo de la misma base de datos.

## 6. Plan por fases

1. **Fase 0 — Modelo de datos.** Diseñar tablas y relaciones (notas, tareas,
   proyectos, responsabilidades, cuentas, movimientos, categorías, presupuestos,
   recordatorios) con pgvector para los embeddings de notas.
2. **Fase 1 — Backend / API.** Implementar las operaciones de cada dominio.
3. **Fase 2 — NLU.** Conectar el LLM (Qwen) con tool calling a las operaciones;
   añadir transcripción con Whisper.
4. **Fase 3 — Canal.** Conectar Telegram (texto y audio) end-to-end.
5. **Fase 4 — Scheduler.** Recordatorios escalonados y alertas de presupuesto.
6. **Fase 5 — Frontend Kanban (React).**

## 7. Decisiones abiertas

- Granularidad de los presupuestos (por categoría / por cuenta / global).
- Anticipación y número exacto de recordatorios por defecto (configurable).
- Conjunto inicial de categorías sugeridas.
- Orden de las columnas del Kanban (Fase 5): convencional vs. invertido vs.
  configurable. Recomendación: configurable, con opción de colapsar "terminadas".
- Forma de servir Qwen (vLLM vs Ollama vs otro) y manejo del tamaño de contexto
  para que el tool calling se mantenga fiable.
