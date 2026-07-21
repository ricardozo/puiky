# Guión de video demo — Puiky (formato vertical 9:16)

**Formato recomendado:** **Vertical 1080×1920 (9:16)**, para **Reels / TikTok / Shorts**
— es el que más alcance da para promocionar. Duración objetivo: **~75 segundos**
(se puede recortar a 60s; ver variante al final).

**Ventaja clave:** Puiky **ya es responsive**, así que grabas la **web en vista móvil**
(el navegador en tamaño celular, o desde el teléfono) + el **bot de Telegram**. Todo
sale vertical, sin recortes forzados.

**Idea fuerza:** *"Una persona ocupada, pero tranquila, que le habla a su celular y
todo queda organizado solo."* El gancho es el **bot por voz**: hablas y Puiky actúa.

---

## Antes de grabar (checklist)

- Entra con el **usuario demo** (datos de ejemplo ya cargados). Nada de datos reales.
- **Vertical 1080×1920.** Si grabas la web, pon el navegador en modo responsive
  (DevTools → dispositivo móvil, o ventana angosta) para que se vea como app de celular.
- **Cursor / toques suaves** y deliberados. Nada nervioso.
- Ten el **celular con Telegram** y la **nota de voz** pensada (texto exacto abajo).
- Lo que se escribe/carga se **acelera 1.5–2×** en edición.
- Graba **cada bloque como un clip corto** — más fácil de editar y de sincronizar la voz.

---

## Shot list (vertical, ~75s)

| # | Tiempo | Bloque | Qué se ve (encuadre vertical) |
|---|--------|--------|-------------------------------|
| 1 | 0:00–0:05 | Gancho | Logo + "tu segundo cerebro" / landing "¿Qué es Puiky?" |
| 2 | 0:05–0:22 | **Bot por voz** | Telegram: nota de voz → confirma gasto + recordatorio; luego "¿qué tengo pendiente?" |
| 3 | 0:22–0:32 | Notas | Cuadernos (uno marcado "Proyecto 💼") + búsqueda por significado |
| 4 | 0:32–0:46 | Proyectos | Tablero Kanban: arrastrar tarea; abrir tarea (avance %, recurrencia 🔁) |
| 5 | 0:46–1:02 | Finanzas | Cuentas; por categoría (◀▶ mes); presupuesto; Exportar a Excel |
| 6 | 1:02–1:10 | Mercado | Modo compra → cerrar → gasto automático en Finanzas |
| 7 | 1:10–1:16 | Cierre | Logo + frase + llamado a la acción |

*(Si quieres meter Responsabilidades/Recordatorios recurrentes, súmalos 6s antes del
cierre y quedas en ~80s.)*

### Detalle de cada toma

**1 · Gancho (5s):** logo animado o el landing "¿Qué es Puiky?". Corte al beat.
Mientras la voz dice "Citas… pagos… pendientes", esas tres palabras aparecen en
pantalla al ritmo (kinetic type). El gancho cierra en círculo con el final
("¿y si no tuvieras que recordar nada?" → "deja de recordar, empieza a vivir").

> **Gancho alternativo (cold open, aún más punch):** arranca EN SECO con la nota
> de voz sonando en Telegram —sin logo ni música— y deja que el bot responda; el
> logo entra después. En redes, abrir directo con la acción retiene más que
> cualquier intro.

**2 · Bot por voz (17s) — el "wow":** en Telegram envías la nota de voz y se ve la
respuesta del bot confirmando el **gasto** y el **recordatorio recurrente**; luego
escribes *"¿Qué tengo pendiente?"* y aparece la lista de **tareas + recordatorios**
(algunas con 🔁). Deja que se lea 1–2 segundos.

**3 · Notas (10s):** entra a Notas; se ven los **cuadernos**; escribe en el buscador
algo por **significado** (no palabra exacta) y aparecen notas afines.

**4 · Proyectos (14s):** abre un proyecto; **arrastra una tarea** de columna; abre una
tarea y muestra **% avance**, **fechas** y **Recurrencia 🔁**.

**5 · Finanzas (16s):** cuentas con saldos; en **Por categoría** navega el mes (◀ ▶);
muestra un **presupuesto** con su barra; clic en **Exportar a Excel** (se descarga).

**6 · Mercado (8s):** inicia una compra, marca 1–2 productos con precio, **cierra**;
corte a Finanzas mostrando el **gasto automático**.

**7 · Cierre (6s):** logo + **"Puiky — tu segundo cerebro"** + llamado a la acción.

---

## Guión para la narración con IA

> Para herramientas tipo **ElevenLabs / PlayHT / similares**.

**Voz:** español **latino**, cálida y cercana (hombre o mujer). Evita acento neutro
robótico.
**Ajustes sugeridos (ElevenLabs):** Stability ~50 · Similarity ~75 · Style ~20 ·
Speaker Boost ON · Velocidad ~0.95–1.0.
**Pronunciación:** di **"Puiky"** como **"Puiqui"** (no en inglés).
**Cifras:** ya van escritas en palabras para que la IA las lea bien.
**Pausas:** los `…` marcan respiración; si la herramienta acepta SSML, usa la versión
de abajo.

### Versión para pegar (texto plano, con pausas)

```
Citas… pagos… pendientes. ¿Y si no tuvieras que recordar nada de eso… nunca más?

Con Puiky, tú solo hablas. «Gasté cuarenta y cinco mil en el almuerzo… y recuérdame la cuenta de cobro cada mes.» Listo: registrado… y agendado.

Pregúntale qué tienes pendiente… y nada se te escapa.

Tus notas te entienden: búscalas por la idea… no por la palabra exacta.

Tus proyectos, en un tablero claro: tareas, avance, fechas… y lo que se repite, se repite solo.

Tu plata, bajo control: por categoría, mes a mes, con presupuestos… y todo a Excel, en un clic.

Haces mercado, marcas lo que compraste… y el gasto queda registrado solo.

Puiky. Tu segundo cerebro. Deja de recordar… empieza a vivir.
```

### Versión con SSML (si la herramienta lo acepta)

```xml
<speak>
Citas<break time="250ms"/> pagos<break time="250ms"/> pendientes.<break time="350ms"/> ¿Y si no tuvieras que recordar nada de eso<break time="300ms"/> nunca más?<break time="500ms"/>
Con Puiky, tú solo hablas.<break time="250ms"/> <prosody rate="95%">«Gasté cuarenta y cinco mil en el almuerzo<break time="200ms"/> y recuérdame la cuenta de cobro cada mes.»</prosody><break time="300ms"/> Listo: registrado<break time="200ms"/> y agendado.<break time="450ms"/>
Pregúntale qué tienes pendiente<break time="250ms"/> y nada se te escapa.<break time="450ms"/>
Tus notas te entienden: búscalas por la idea<break time="200ms"/> no por la palabra exacta.<break time="450ms"/>
Tus proyectos, en un tablero claro: tareas, avance, fechas<break time="200ms"/> y lo que se repite, se repite solo.<break time="450ms"/>
Tu plata, bajo control: por categoría, mes a mes, con presupuestos<break time="200ms"/> y todo a Excel, en un clic.<break time="450ms"/>
Haces mercado, marcas lo que compraste<break time="200ms"/> y el gasto queda registrado solo.<break time="500ms"/>
<prosody rate="92%">Puiky. Tu segundo cerebro.</prosody><break time="300ms"/> Deja de recordar<break time="250ms"/> empieza a vivir.
</speak>
```

### Sincronización voz ↔ imagen

| Línea de narración | Bloque de imagen |
|--------------------|------------------|
| "Citas… pagos… pendientes…" | 1 · Gancho |
| "Con Puiky, tú solo hablas… agendado." | 2 · Bot por voz |
| "Pregúntale qué tienes pendiente…" | 2 · Bot (lista pendientes) |
| "Tus notas te entienden…" | 3 · Notas |
| "Tus proyectos, en un tablero claro…" | 4 · Proyectos |
| "Tu plata, bajo control…" | 5 · Finanzas |
| "Haces mercado…" | 6 · Mercado |
| "Puiky. Tu segundo cerebro…" | 7 · Cierre |

*(Duración hablada ≈ 60–70s; el resto es aire + música. Encaja en el master de ~75s.)*

---

## La nota de voz exacta (para grabar el bot al primer intento)

Dile al bot, tal cual:
> *"Gasté cuarenta y cinco mil en el almuerzo con Bancolombia, y recuérdame enviar la cuenta de cobro cada mes."*

Luego escribe:
> *"¿Qué tengo pendiente?"*

*(Con el usuario demo, ambas respuestas salen limpias y muestran gasto + recordatorio
recurrente + lista de pendientes.)*

---

## Música y ritmo

- Estilo: **corporate / lo-fi optimista**, sin letra, tempo medio (100–115 BPM).
- **Sube** en el bloque del bot (2) y en el cierre (7); parejo en el resto.
- **Cortes de escena en el beat** (cada 2–4s) → sensación de agilidad.
- Voz **por encima** de la música (música a ~−18 dB bajo la narración).

## Textos en pantalla (kinetic type)

Una palabra por bloque: **Habla · Organiza · Busca · Controla tu plata · Todo conectado.**
Y en el gancho: **Citas · Pagos · Pendientes**, apareciendo al ritmo de la voz.

## Llamado a la acción (elige uno)

- "Escríbele a Puiky y pruébalo hoy."
- "Tu segundo cerebro te está esperando."
- (Si hay web/registro) enlace en pantalla al final.

---

## Variante 60s (aún más corta)

Deja: **1 Gancho → 2 Bot por voz → 4 Proyectos → 5 Finanzas → 7 Cierre**.
De la narración, usa solo esas líneas. Es el "trailer".

---

## Voz femenina (versión lista)

El texto de la narración es el mismo (habla en segunda persona, sirve igual). Cambian
la **voz** y los **ajustes** para que suene cálida y creíble.

**Voz:** español **latino femenino**, cercana y con energía tranquila (no locutora de
noticias). En ElevenLabs sirven voces como *Valentina*, *Sara* o cualquier voz
latina joven-adulta; en otras herramientas, elige "Spanish (Latin America) — Female,
warm".
**Ajustes sugeridos (ElevenLabs):** Stability ~55 · Similarity ~80 · Style ~25 ·
Speaker Boost ON · Velocidad ~0.97. *(Un pelín más de Stability que la voz masculina
para que no suene sobreactuada.)*
**Pronunciación:** **"Puiky" → "Puiqui"**. **Cifras** ya escritas en palabras.
**Intención de lectura:** cómplice y ligera; sonríe al leer el gancho y el cierre.

### Texto para pegar (voz femenina)

```
Citas… pagos… pendientes. ¿Y si no tuvieras que recordar nada de eso… nunca más?

Con Puiky, tú solo hablas. «Gasté cuarenta y cinco mil en el almuerzo… y recuérdame la cuenta de cobro cada mes.» Listo: registrado… y agendado.

Pregúntale qué tienes pendiente… y nada se te escapa.

Tus notas te entienden: búscalas por la idea… no por la palabra exacta.

Tus proyectos, en un tablero claro: tareas, avance, fechas… y lo que se repite, se repite solo.

Tu plata, bajo control: por categoría, mes a mes, con presupuestos… y todo a Excel, en un clic.

Haces mercado, marcas lo que compraste… y el gasto queda registrado solo.

Puiky. Tu segundo cerebro. Deja de recordar… empieza a vivir.
```

### SSML (voz femenina)

```xml
<speak>
<prosody rate="97%">
Citas<break time="250ms"/> pagos<break time="250ms"/> pendientes.<break time="350ms"/> ¿Y si no tuvieras que recordar nada de eso<break time="300ms"/> nunca más?<break time="500ms"/>
Con Puiky, tú solo hablas.<break time="250ms"/> «Gasté cuarenta y cinco mil en el almuerzo<break time="200ms"/> y recuérdame la cuenta de cobro cada mes.»<break time="300ms"/> Listo: registrado<break time="200ms"/> y agendado.<break time="450ms"/>
Pregúntale qué tienes pendiente<break time="250ms"/> y nada se te escapa.<break time="450ms"/>
Tus notas te entienden: búscalas por la idea<break time="200ms"/> no por la palabra exacta.<break time="450ms"/>
Tus proyectos, en un tablero claro: tareas, avance, fechas<break time="200ms"/> y lo que se repite, se repite solo.<break time="450ms"/>
Tu plata, bajo control: por categoría, mes a mes, con presupuestos<break time="200ms"/> y todo a Excel, en un clic.<break time="450ms"/>
Haces mercado, marcas lo que compraste<break time="200ms"/> y el gasto queda registrado solo.<break time="500ms"/>
</prosody>
<prosody rate="92%">Puiky. Tu segundo cerebro.</prosody><break time="300ms"/> Deja de recordar<break time="250ms"/> empieza a vivir.
</speak>
```

*Tip: genera la misma toma con la voz masculina y la femenina, y en edición elige la
que mejor combine con tu música.*
