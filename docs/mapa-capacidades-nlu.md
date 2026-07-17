# Mapa de capacidades para Telegram (NLU)

> Inventario de **todo lo que se puede hacer** en Puiky, para exponerlo por
> Telegram (lenguaje natural → herramientas del LLM). Sirve como referencia para
> ampliar el conjunto de *tools* de la capa NLU (`backend/app/nlu/tools.py`).
>
> Estado: **✅** ya existe como tool · **⬜** por crear.

## Cómo leer este mapa

Cada operación indica:
- **Ejemplo hablado**: cómo lo diría el usuario por texto/voz.
- **R/W**: si lee (R) o modifica (W) datos.
- **Referencia**: cómo se identifica la entidad sobre la que se actúa (el reto
  principal — ver "Retos transversales").

---

## Conceptos (vocabulario que el modelo debe conocer)

El system prompt debe enseñarle estos términos para que interprete bien:

- **Hoja** = una nota. Tiene **título** (opcional) y un **cuerpo** que puede
  crecer. Vive en un **cuaderno** (o suelta) y puede **vincularse** a tareas o
  proyectos. Es buscable por significado (semántica).
- **Cuaderno** = agrupa hojas (como un cuaderno con sus páginas).
- **Portafolio** = agrupa proyectos.
- **Proyecto** = agrupa tareas; su tablero Kanban son los estados de las tareas.
- **Tarea** = título, descripción, notas rápidas, **estado** (planeada /
  en_ejecucion / en_pausa / terminada), **avance %**, **fechas** (inicio y fin,
  planeado y real), **checklist** (ítems marcables que calculan el avance) y
  **notas vinculadas** (hojas).
- **Cuenta / Categoría / Movimiento / Presupuesto** = finanzas.
- **Responsabilidad** = compromiso recurrente (arriendo, renovación).
- **Recordatorio** = aviso con fecha; puede ser suelto o atado a algo.

---

## 1. Notas / Hojas / Cuadernos

| Operación | Ejemplo hablado | R/W | Referencia | Estado |
|-----------|-----------------|-----|-----------|--------|
| Crear hoja | "anota que el cliente pidió cambiar el logo" / "hoja nueva 'Ideas': ..." | W | — (nueva; título y cuaderno opcionales) | ✅ (falta título/cuaderno) |
| Añadir a una hoja | "en la hoja de la reunión de hoy, añade que definimos el hosting" | W | hoja por **título** (semántica/ilike); crear si no existe | ⬜ |
| Editar hoja | "cambia el título de la hoja X a Y" / "reescribe la hoja X" | W | hoja por título | ⬜ |
| Mover hoja a cuaderno | "mueve la hoja X al cuaderno Iconred" | W | hoja + cuaderno por nombre | ⬜ |
| Eliminar hoja | "borra la hoja X" | W | hoja por título | ⬜ |
| Buscar hojas | "¿qué anoté sobre facturación?" | R | consulta semántica | ✅ |
| Listar hojas de cuaderno | "muéstrame las hojas del cuaderno Iconred" | R | cuaderno por nombre | ⬜ |
| Crear cuaderno | "crea un cuaderno llamado Personal" | W | — | ⬜ |
| Listar cuadernos | "¿qué cuadernos tengo?" | R | — | ⬜ |

## 2. Portafolios / Proyectos / Tareas

### Portafolios y proyectos

| Operación | Ejemplo hablado | R/W | Referencia | Estado |
|-----------|-----------------|-----|-----------|--------|
| Crear portafolio | "crea el portafolio Iconred" | W | — | ⬜ |
| Listar portafolios | "¿qué portafolios tengo?" | R | — | ⬜ |
| Crear proyecto | "nuevo proyecto Portal COLEF en Iconred" | W | portafolio por nombre (opcional) | ✅ (falta portafolio) |
| Listar proyectos | "lista mis proyectos" / "proyectos de Iconred" | R | portafolio por nombre (opcional) | ⬜ |
| Ver proyecto | "muéstrame el proyecto Portal COLEF" (tareas + notas) | R | proyecto por nombre | ⬜ |
| Mover proyecto a portafolio | "mueve Portal COLEF al portafolio Personal" | W | proyecto + portafolio | ⬜ |
| Archivar proyecto | "archiva el proyecto X" | W | proyecto por nombre | ⬜ |

### Tareas

| Operación | Ejemplo hablado | R/W | Referencia | Estado |
|-----------|-----------------|-----|-----------|--------|
| Crear tarea | "crea la tarea 'Wireframes' en Portal COLEF" | W | proyecto por nombre (opcional) | ✅ (falta fechas/desc) |
| Editar tarea | "cambia la descripción de la tarea X" / "pon la fecha límite de X al viernes" | W | tarea por título | ⬜ |
| Cambiar estado | "pasa la tarea X a en pausa" / "mueve X a terminada" | W | tarea por título | ⬜ |
| Marcar avance | "marca la tarea del informe al 80%" | W | tarea por título | ✅ |
| Completar tarea | "marca completada la tarea X" | W | tarea por título | ✅ |
| Reabrir tarea | "reabre la tarea X" | W | tarea por título | ⬜ |
| Eliminar tarea | "borra la tarea X" | W | tarea por título | ⬜ |
| Listar tareas | "tareas de Portal COLEF" / "tareas de hoy" / "pendientes" | R | proyecto (opcional) | ✅ parcial (pendientes) |
| **Fechas** planeado/real | "la tarea X la empecé el lunes" (inicio real) | W | tarea por título | ⬜ |

### Checklist y notas de una tarea

| Operación | Ejemplo hablado | R/W | Referencia | Estado |
|-----------|-----------------|-----|-----------|--------|
| Añadir ítem al checklist | "en la tarea X añade el paso 'correr tests'" | W | tarea por título | ⬜ |
| Marcar/desmarcar ítem | "marca 'correr tests' como hecho en la tarea X" | W | tarea + ítem por texto | ⬜ |
| Eliminar ítem | "quita el paso 'correr tests' de X" | W | tarea + ítem | ⬜ |
| Añadir nota (hoja) a la tarea | "en la tarea X anota que el cliente aprobó el diseño" | W | tarea por título (crea hoja + vincula) | ⬜ |
| Notas rápidas de la tarea | "en las notas de la tarea X escribe ..." | W | tarea por título | ⬜ |

## 3. Finanzas

| Operación | Ejemplo hablado | R/W | Referencia | Estado |
|-----------|-----------------|-----|-----------|--------|
| Registrar gasto | "gasté 20 mil en comida con efectivo" | W | cuenta + categoría por nombre | ✅ |
| Registrar ingreso | "me pagaron 2 millones en el banco" | W | cuenta + categoría | ✅ |
| Transferir | "pasa 500 mil del banco a ahorros" | W | dos cuentas | ✅ |
| Consultar saldo | "¿cuánto tengo en ahorros?" | R | cuenta por nombre | ✅ |
| Gastos del mes | "¿cuánto llevo gastado este mes?" | R | — | ✅ |
| Crear cuenta | "crea la cuenta Nequi tipo banco" | W | — | ⬜ |
| Listar cuentas | "¿qué cuentas tengo?" | R | — | ⬜ |
| Crear categoría | "crea la categoría Mascotas" | W | — | ⬜ |
| Listar movimientos | "movimientos de la cuenta efectivo" | R | cuenta (opcional) | ⬜ |
| Eliminar movimiento | "borra el último gasto" | W | movimiento (por recencia?) | ⬜ |
| Definir presupuesto | "presupuesto de 300 mil en comida" | W | categoría (opcional = global) | ⬜ |
| Avance de presupuesto | "¿cómo voy con el presupuesto de comida?" | R | presupuesto por categoría | ⬜ |

## 4. Responsabilidades

| Operación | Ejemplo hablado | R/W | Referencia | Estado |
|-----------|-----------------|-----|-----------|--------|
| Crear | "el arriendo son 1.800.000 cada mes, vence el 5" | W | — | ✅ |
| Listar próximos | "¿qué responsabilidades tengo pronto?" | R | — | ⬜ |
| Marcar cumplida | "ya pagué el arriendo" (recalcula el próximo) | W | por nombre | ⬜ |
| Editar / eliminar | "cambia el monto del arriendo a 1.900.000" | W | por nombre | ⬜ |

## 5. Recordatorios

| Operación | Ejemplo hablado | R/W | Referencia | Estado |
|-----------|-----------------|-----|-----------|--------|
| Crear | "recuérdame llamar al dentista el viernes a las 3" | W | — | ✅ |
| Listar | "¿qué recordatorios tengo?" | R | — | ⬜ |
| Vencidos | "¿qué tengo pendiente ahora?" | R | — | ⬜ |
| Posponer | "posponer el del dentista para mañana" | W | por texto | ⬜ |
| Resolver | "ya llamé al dentista, resuélvelo" | W | por texto | ⬜ |
| Eliminar | "borra el recordatorio del dentista" | W | por texto | ⬜ |

---

## Retos transversales

1. **Resolución de referencias (lo más difícil).** La mayoría de las W actúan
   sobre algo existente ("la tarea del informe", "la hoja de la reunión"). Hay
   que resolver por **nombre/título** (ilike) o **semántica** (hojas), y manejar
   la **ambigüedad** (si coinciden varias, preguntar cuál). Patrón ya usado en
   `tools.py` (`_resolver`), a extender a hojas/tareas/cuadernos/portafolios.

2. **Contexto en el system prompt.** Ya inyectamos fecha, categorías, cuentas y
   proyectos. Habrá que sumar (según convenga): cuadernos, portafolios y quizá los
   títulos de tareas/hojas recientes, para que el modelo mapee referencias.

3. **Cantidad de herramientas.** El mapa son ~50 operaciones. Un set muy grande
   puede confundir a modelos pequeños. Con Qwen 14B es viable, pero conviene:
   descripciones claras, nombres consistentes, y agrupar donde tenga sentido
   (p. ej. un `editar_tarea` con varios campos opcionales en vez de uno por campo).

4. **Confirmaciones.** Para acciones destructivas (borrar) o de mucho impacto,
   que el bot confirme antes de ejecutar.

## Plan de implementación propuesto (por lotes)

Ordenado por lo que más usas hoy:

1. **Hojas y cuadernos** — añadir-a-hoja (con auto-crear), crear/editar/mover/
   listar hojas, crear/listar cuadernos. *(Era el objetivo original de Telegram.)*
2. **Tareas** — editar (desc/fechas/estado), reabrir/eliminar, checklist
   (añadir/marcar/quitar), notas de tarea, listar por proyecto.
3. **Portafolios/proyectos** — crear/listar/mover/archivar; crear tarea con
   proyecto por nombre.
4. **Finanzas (resto)** — cuentas, categorías, movimientos, presupuestos.
5. **Responsabilidades y recordatorios (resto)** — listar, cumplir, posponer,
   resolver, eliminar.

Cada lote: definir las tools en `tools.py` (con resolución de referencias),
ajustar el system prompt, y probar con el backend `fake` y luego con Qwen real.
