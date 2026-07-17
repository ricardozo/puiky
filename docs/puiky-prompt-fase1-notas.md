# Prompt de arranque — Puiky · Fase 1 (backend / API), sesión 1: notas

> Pega esto en Claude Code. Adjunta también los dos documentos de referencia:
> `especificacion-asistente-personal.md` y `puiky-modelo-de-datos.md`.
>
> Flujo de trabajo previsto: se DESARROLLA en Windows con Claude Code y se EJECUTA
> en un servidor Ubuntu (donde viven Postgres y el modelo Qwen local). Por eso el
> código debe ser portable entre ambas máquinas (ver "Portabilidad" abajo).

---

## Contexto

Estás ayudándome a construir **Puiky**, un asistente personal de un solo usuario
(soy el único usuario; soy técnico). Te adjunto dos documentos que son la fuente
de verdad del proyecto: la especificación funcional y el modelo de datos. Léelos
antes de empezar; resumen visión, arquitectura, dominios y el esquema de datos
completo. No los repitas de vuelta, solo confírmame que los entendiste señalando
en una o dos frases qué vas a construir en esta sesión.

## Entorno y flujo de trabajo

- **Desarrollo en Windows** (aquí, con Claude Code). **Ejecución en un servidor
  Ubuntu** propio, donde corren Postgres con pgvector y un Qwen3 14B local
  (servido por Ollama en un endpoint OpenAI-compatible). El código se llevará al
  servidor con **Git** (`git pull`), no copiando carpetas a mano.
- Stack confirmado: **Python**, **FastAPI**, **SQLAlchemy**, **Alembic**,
  **Postgres con la extensión pgvector**.
- Organización con **Docker** (un contenedor para Postgres, otro para la app), lo
  que hace que el entorno sea idéntico en Windows y en Ubuntu.
- Esta es la **Fase 1**: el backend / API. Telegram, la capa NLU (Qwen) y el
  frontend React vienen en fases posteriores y NO se tocan ahora.

## Portabilidad (importante por el flujo Windows → Ubuntu)

El código debe correr sin cambios en Windows (desarrollo) y en Ubuntu (producción):

- **Nada "quemado" en el código**: ninguna ruta absoluta, URL, host, puerto,
  usuario o contraseña dentro del código fuente. TODO eso va en variables de entorno
  leídas desde un archivo `.env`.
- Crea un **`.env.example`** versionado (con valores de ejemplo, sin secretos) y
  añade `.env` al `.gitignore` para que los secretos reales nunca se suban.
- Las rutas de archivos deben construirse de forma portable (nada de separadores de
  Windows escritos a mano).
- Inicializa **Git** en el proyecto desde el inicio, con un `.gitignore` adecuado
  para Python (entornos virtuales, `__pycache__`, `.env`, etc.).

## Diseño de la API: dos tipos de cliente

Aunque en esta fase NO se implementa autenticación, la API debe diseñarse sabiendo
que más adelante la consumirán **dos tipos de llamante distintos** (ver la spec,
secciones 8 y 9):

1. Un **usuario humano** desde una interfaz web React, que se autenticará con un
   token de sesión.
2. El **bot de Telegram**, como servicio interno de confianza corriendo en el mismo
   servidor (credencial de servicio, no login humano).

No asumas un único llamante ni mezcles lógica de canal (Telegram, web) dentro de la
lógica de negocio. Las operaciones de la API deben ser independientes de quién las
llama. No implementes la autenticación ahora; solo no cierres la puerta a estos dos
casos.

## Objetivo de esta sesión: el dominio de NOTAS (el núcleo)

Quiero terminar esta sesión con una API mínima pero verificable que maneje notas,
incluida la **búsqueda semántica** con pgvector. En concreto:

1. **Estructura del proyecto.** Crea una estructura de proyecto Python limpia y
   escalable (preparada para que después se sumen los demás dominios: tareas,
   proyectos, responsabilidades, finanzas, recordatorios, y más adelante un
   frontend React en su propia carpeta). Propónmela antes de crearla y explícame
   brevemente la organización de carpetas.

2. **Entorno reproducible.** Configura Docker Compose con Postgres + pgvector y el
   contenedor de la app. Maneja dependencias con un enfoque estándar (por ejemplo
   `pyproject.toml` o `requirements.txt`, tú recomienda). Deja claro cómo levantar
   todo con un comando, y que funcione igual en Windows y en Ubuntu.

3. **Base de datos y migraciones.** Configura SQLAlchemy + Alembic. Habilita la
   extensión pgvector. Crea la migración inicial con las tablas `NOTE` y
   `NOTE_LINK` tal como están en el documento de modelo de datos. (Las demás tablas
   se añadirán en sesiones siguientes; no las crees aún, salvo que sea necesario un
   stub para una FK — si es así, consúltame.)

4. **Modelo de embeddings — DECISIÓN PENDIENTE.** Para la búsqueda semántica
   necesito generar el `embedding` de cada nota. Antes de implementarlo,
   plantéame las opciones (modelo local tipo sentence-transformers vs. servicio
   externo), con foco en: privacidad (los datos no deben salir del servidor),
   costo cero, y buen soporte de español. Recomiéndame uno y dime qué dimensión
   de vector usa, para que la columna `embedding` coincida. Espera mi confirmación
   antes de fijar la dimensión en la migración. Nota: el modelo de embeddings se
   ejecutará en el Ubuntu; ten en cuenta cómo se prueba esto en Windows durante el
   desarrollo (p. ej. que el contenedor lo descargue, o un modo de prueba).

5. **Endpoints de notas.** Implementa las operaciones del dominio de notas:
   - Crear nota (genera y guarda su embedding).
   - Vincular una nota a otra entidad (NOTE_LINK polimórfico: project / task /
     responsibility / account). Como esas tablas aún no existen, por ahora acepta
     `entidad_tipo` y `entidad_id` sin validar la FK; déjalo anotado como deuda
     técnica a resolver cuando existan esas tablas.
   - Búsqueda semántica: dado un texto, devolver las notas más cercanas por
     similitud de vectores (pgvector).
   - Listar, ver, editar y eliminar notas.

6. **Verificable sin frontend.** Quiero poder probar todo desde la documentación
   interactiva de FastAPI (Swagger UI) sin haber construido aún el bot. Al final,
   dame los pasos exactos para levantar el entorno y un par de ejemplos de prueba
   (crear dos o tres notas y hacer una búsqueda semántica que muestre que el
   ranking por significado funciona).

## Cómo quiero trabajar

- Ve por pasos pequeños y verificables. Al terminar cada paso, muéstrame qué
  hiciste y cómo comprobarlo, antes de seguir.
- Cuando una decisión dependa de mi criterio (estructura, modelo de embeddings,
  manejo de dependencias), **pregúntame en vez de asumir**.
- No implementes nada de Telegram, NLU/Qwen ni React en esta sesión.
- Mantén el código simple y legible; es un proyecto personal, no necesito
  sobreingeniería (ni colas, ni microservicios, ni capas de abstracción extra).

Empieza confirmando qué entendiste y proponiéndome la estructura del proyecto.
