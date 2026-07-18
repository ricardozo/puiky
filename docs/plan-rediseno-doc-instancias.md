# Plan: rediseño visual · documento de arquitectura · instancias aisladas

> Tres iniciativas independientes. Se pueden hacer en el orden que prefieras.

---

## A. Rediseño visual

**Meta:** que la interfaz web se vea bien y coherente, con identidad Puiky
(muisca / "segundo cerebro"). Hoy es funcional pero básica (dark slate Tailwind).

**Decisiones a tomar antes de empezar:**
- **Dirección visual:** te propongo 2-3 estilos (paleta, tipografía, densidad,
  estilo de tarjetas/sidebar) como muestras y eliges una.
- **¿Modo claro + oscuro, o solo oscuro?**
- **Identidad:** color de acento, tipografía, logotipo/marca.

**Pasos:**
1. **Dirección** — presento 2-3 opciones visuales (mockups/paletas); elegimos.
2. **Sistema de diseño** — tokens (colores, radios, sombras, espaciados) +
   primitivas reutilizables: `Button`, `Input`, `Textarea`, `Select`, `Card`,
   `Badge`, `Modal`, `SidebarItem`. Centraliza el estilo en un solo lugar.
3. **Refactor por pantalla** usando las primitivas (Notas, Kanban, Tareas,
   Finanzas, Recordatorios, Responsabilidades, Login).
4. **Pulido** — responsive/móvil, estados (hover/focus/vacío/carga), microdetalles,
   íconos consistentes.

**Esfuerzo:** medio-alto (varias sesiones). **Riesgo funcional:** bajo (solo estilos).

---

## B. Documento de arquitectura del agente

**Meta:** explicar cómo funciona Puiky y **por qué su agente es fluido**, para que
puedas enseñar/replicar la experiencia (tu otro proyecto de agente no fluye igual).

**Contenido:**
1. **Visión y arquitectura por capas** — datos/API, NLU, canal (Telegram),
   scheduler, web. Diagrama.
2. **El diseño de la NLU que la hace fluida** (lo importante):
   - Herramientas (*tools*) que mapean a **operaciones reales** → `services`.
   - **Resolución de referencias por nombre/semántica** (no UUIDs): el usuario
     dice "la tarea del informe", no un id.
   - **Inyección de contexto** en el system prompt (fecha, categorías, cuentas,
     proyectos, cuadernos, portafolios) → el modelo mapea sin preguntar.
   - **Memoria de conversación** (multi-turno) → mantiene el hilo.
   - **Confirmación de borrados** (botones) → seguridad.
   - **Proveedor intercambiable** (real/fake) y modelo swappable.
   - **Errores como resultado** (no excepciones) → el modelo los explica.
   - **Orquestador**: una ronda de tools + segunda pasada para confirmar natural.
   - **Voz** con Whisper.
3. **Lecciones — qué hace fluido a un agente vs. frustrante** (checklist de buenas
   prácticas, con el "por qué" de cada decisión).
4. **Flujo de un mensaje** paso a paso (texto y voz), con diagrama.

**Formato:** markdown en `docs/`, y (opcional) un **Artifact** — página web bonita
para compartir/enseñar.

**Esfuerzo:** bajo-medio (1 sesión). Lo redacto a partir del código real.

---

## C. Instancias aisladas ("empaquetar") para la familia

**Meta:** crear instancias separadas de Puiky para familiares, con **datos
totalmente aislados** (que no se crucen con los tuyos).

**Enfoque recomendado: INSTANCIAS SEPARADAS (no multi-tenant).**
Cada persona = su propio stack: Postgres propio, app propia, bot propio, datos
propios. Aislamiento **físico** por base de datos. Comparten el mismo **Ollama/Qwen**
del servidor (el modelo no guarda datos; cada petición es independiente).

*¿Por qué no multi-tenant (una sola app con varios usuarios)?* La app es
single-user por diseño (un USER, una allowlist). Meter multi-tenant (scoping de
`user_id` en cada tabla y en la auth) es mucho trabajo y **riesgo de cruce de
datos**. Instancias separadas es más seguro y directo.

**Decisiones a tomar:**
- ¿Cada instancia con su **web**, o la familia usa **solo Telegram**? (Telegram es
  lo más simple para ellos; la web es opcional por instancia.)
- ¿Todas en tu **servidor Ubuntu** (varios stacks), o algunas en otro lado?

**Pasos:**
1. **Parametrizar el stack** — `docker compose -p puiky-<nombre> --env-file
   .env.<nombre>` aísla volúmenes y red por nombre de proyecto. Cada `.env`:
   `POSTGRES_DB`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_IDS`, secretos
   (JWT/SERVICE), puertos propios. Todas apuntan al mismo `LLM_BASE_URL` (Qwen).
2. **Script de aprovisionamiento** — `crear-instancia.sh <nombre> <bot_token>
   <telegram_id>`: genera `.env.<nombre>` con secretos aleatorios, levanta el stack,
   corre migraciones y crea el usuario web.
3. **Alta de cada familiar** — crea su bot con @BotFather (su token) y te pasa su
   ID de Telegram → aprovisionas la instancia.
4. **Operación** — documentar cómo actualizar todas las instancias (`git pull` +
   rebuild + `up -d` por instancia; script para actualizar en lote).

**Consideraciones:**
- **RAM:** cada instancia carga su propio modelo de embeddings (e5, ~1 GB). Para
  pocos familiares está bien en un servidor decente; a futuro se puede compartir un
  microservicio de embeddings (optimización posterior).
- **Bot:** cada instancia necesita su **propio** token de bot (no se comparte uno;
  daría conflicto 409).
- **Qwen compartido:** sin cruce de datos (el modelo es stateless); una sola GPU
  sirve a todas las instancias.

**Esfuerzo:** medio (1-2 sesiones).

---

## Orden sugerido

1. **B (documento)** — rápido, y cristaliza la arquitectura (útil para lo demás).
2. **A (rediseño)** — el esfuerzo creativo grande; así las instancias de la familia
   ya salen con la UI pulida.
3. **C (instancias)** — empaquetar y aprovisionar.

Pero es flexible: si quieres las instancias de la familia ya, C puede ir primero
(la funcionalidad está completa).
