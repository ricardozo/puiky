# Narración para IA de voz — Puiky

Instrucciones **solo para generar el audio de la narración** (ElevenLabs, PlayHT o
similar). Duración hablada objetivo: **60–70 segundos**.

---

## Reglas generales (aplican a ambas voces)

- **Idioma:** español **latino**, cálido y cercano. Nada de acento neutro robótico
  ni tono de locutor de noticias.
- **Pronunciación:** la marca **"Puiky" se pronuncia "Puiqui"** (nunca en inglés).
  Si la herramienta lo permite, agrégalo al diccionario de pronunciación; si no,
  puedes escribir "Puiqui" en el texto y listo.
- **Cifras:** ya van escritas en palabras («cuarenta y cinco mil») — no cambiarlas
  a números.
- **Pausas:** los `…` marcan respiración. Si la herramienta acepta SSML, usa la
  versión SSML (pausas exactas con `<break>`).
- **Intención de lectura:** cómplice y ligera. El gancho inicial y el cierre se
  leen "con una sonrisa"; el resto, con energía tranquila.
- Genera **las dos voces** (femenina y masculina) con el mismo texto y elige en
  edición la que mejor combine con la música.

---

## Opción A · Voz femenina

**Voz:** español latino femenino, joven-adulta, cercana (en ElevenLabs sirven
*Valentina*, *Sara* o similar; en otras herramientas: "Spanish (Latin America) —
Female, warm").

**Ajustes (ElevenLabs):**
- Stability: **~55**
- Similarity: **~80**
- Style: **~25**
- Speaker Boost: **ON**
- Velocidad: **~0.97**

### Texto (pegar tal cual)

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

### SSML (si la herramienta lo acepta)

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

---

## Opción B · Voz masculina

**Voz:** español latino masculino, cálido y cercano.

**Ajustes (ElevenLabs):**
- Stability: **~50**
- Similarity: **~75**
- Style: **~20**
- Speaker Boost: **ON**
- Velocidad: **~0.95–1.0**

### Texto (pegar tal cual)

*(El mismo texto de la Opción A — cópialo de arriba.)*

### SSML (si la herramienta lo acepta)

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

---

## Verificación del audio generado

Antes de dar por buena una toma, revisa que:

1. **"Puiky" suene "Puiqui"** (no "piuki" ni en inglés).
2. **"cuarenta y cinco mil"** se diga completo y natural (sin leerlo como número).
3. Las **pausas** se sientan (especialmente tras "¿…nunca más?" y antes del cierre).
4. El **cierre** ("Puiky. Tu segundo cerebro…") baje un poco el ritmo — es el remate.
5. Duración total entre **60 y 70 segundos**; si queda muy rápida, baja la velocidad
   un punto (0.95) y regenera.
