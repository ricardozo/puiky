# Instalar Hermes Agent en el servidor Ubuntu — guía de arranque

> Objetivo: dejar Hermes funcionando en tu servidor, hablándole por Telegram,
> usando tu Qwen3 14B local. Sigue los pasos en orden. Cada bloque indica qué
> esperar antes de pasar al siguiente.
>
> Fuente: repositorio oficial NousResearch/hermes-agent (versión activa a jun 2026).

---

## 0. Antes de empezar: cómo "darle una carpeta concreta"

Hermes se autogestiona en una carpeta raíz llamada `HERMES_HOME` (por defecto
`~/.hermes`). Ahí guarda su copia del código, su entorno de Python, su memoria y
su configuración. La forma correcta de elegir dónde vive **no** es clonar el repo
a mano en otro sitio (eso rompe sus actualizaciones), sino **definir la variable
`HERMES_HOME` antes de instalar**.

Decide la ruta. Ejemplos:
- Por defecto: `~/.hermes`  (lo más simple, recomendado para probar)
- Carpeta concreta tuya: `/opt/puiky/hermes`  o  `~/puiky/hermes`

En esta guía uso `~/puiky/hermes` como ejemplo. Cámbialo si prefieres otra.

```bash
# Crea la carpeta y fija la variable para esta sesión
mkdir -p ~/puiky/hermes
export HERMES_HOME=~/puiky/hermes
```

Para que persista entre reinicios de tu sesión SSH, añádela a tu shell:

```bash
echo 'export HERMES_HOME=~/puiky/hermes' >> ~/.bashrc
# (si usas zsh, cambia ~/.bashrc por ~/.zshrc)
```

---

## 1. Requisitos previos (rápido de verificar)

El instalador trae casi todo (uv, Python 3.11), pero conviene tener:

```bash
# Comprobaciones
curl --version        # debe existir
git --version         # recomendado
ffmpeg -version       # necesario para transcribir audios de Telegram

# Si falta ffmpeg:
sudo apt update && sudo apt install -y ffmpeg
```

> ffmpeg importa para ti: sin él, los mensajes de voz de Telegram no se
> transcriben.

---

## 2. Instalar Hermes

Con `HERMES_HOME` ya exportado (paso 0), ejecuta el instalador oficial:

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

> Buena práctica: antes de ejecutar un script de internet con bash, puedes
> revisarlo primero. Si quieres: abre la URL en el navegador y léelo, o descárgalo
> con `curl -fsSL ...install.sh -o install.sh`, ábrelo, y luego `bash install.sh`.

Al terminar, recarga el shell para que el comando `hermes` esté disponible:

```bash
source ~/.bashrc      # o ~/.zshrc
hermes doctor         # diagnóstico: confirma que todo quedó bien
```

`hermes doctor` debería reportar que el entorno está sano. Si señala algo, resuélvelo
antes de seguir.

---

## 3. Apuntar Hermes a tu Qwen local

Hermes habla con cualquier endpoint compatible con OpenAI. Tu Qwen local debe estar
servido por algo que exponga esa interfaz (vLLM la expone; Ollama también tiene un
endpoint compatible). Necesitas saber:

- La URL base de tu servidor de Qwen (p. ej. `http://localhost:8000/v1` para vLLM,
  o `http://localhost:11434/v1` para Ollama).
- El nombre del modelo tal como lo sirve tu motor (p. ej. `Qwen3-14B`).

Configúralo con el asistente interactivo:

```bash
hermes model
```

Elige la opción de **endpoint personalizado / OpenAI-compatible** e introduce la URL
base y el nombre del modelo. Si `hermes model` no te deja escribir la URL a mano,
usa la configuración directa:

```bash
hermes config set      # te guía para fijar valores individuales
```

> Si aún NO tienes Qwen servido con un endpoint OpenAI-compatible, ese es un
> prerrequisito aparte. Dímelo y te preparo cómo levantarlo con vLLM.

Verifica el cerebro antes de seguir:

```bash
hermes
```

Esto abre el chat en la terminal. Escríbele algo simple ("hola, ¿qué modelo eres?").
Si responde, tu Qwen está conectado. Sal del chat (Ctrl+C) y sigue.

---

## 4. Conectar Telegram

Primero, crea tu bot de Telegram (fuera de Hermes):

1. En Telegram, habla con **@BotFather**.
2. Envía `/newbot`, ponle nombre (p. ej. "Puiky") y un usuario terminado en `bot`.
3. BotFather te da un **token** (una cadena larga). Guárdalo.

Luego, configura el gateway de Hermes:

```bash
hermes gateway setup
```

El asistente te preguntará por la plataforma (elige **Telegram**) y te pedirá el
**token** del bot. Sigue las indicaciones. Cuando termine, arranca el gateway:

```bash
hermes gateway start
```

Ahora abre Telegram, busca tu bot por su usuario y envíale un mensaje. Debe
responder. **Importante (seguridad):** Hermes usa emparejamiento por DM y lista de
usuarios permitidos; sigue lo que indique el asistente para autorizar tu propio
usuario y que el bot no quede abierto a cualquiera.

---

## 5. Dejarlo corriendo siempre (servicio)

Mientras pruebas, basta con `hermes gateway start` en una sesión. Para que siga
vivo aunque cierres SSH, instálalo como servicio del sistema:

```bash
hermes gateway install     # lo registra como servicio systemd
```

Comandos útiles del servicio (systemd):

```bash
systemctl --user status hermes-gateway     # ver estado (ruta puede variar)
journalctl --user -u hermes-gateway -f      # ver logs en vivo
```

> El nombre exacto del servicio lo confirma la salida de `hermes gateway install`.
> Si lo instala como servicio de sistema (no de usuario), usa `sudo systemctl`.

---

## 6. Primer uso real (esto ES la prueba)

No hay un "guion de prueba" aparte: la prueba es usarlo. Desde Telegram, empieza a
tirarle cosas reales de tus proyectos:

- "Recuérdame mañana a las 9 llamar al contador."
- "Apunta esta idea para el proyecto X: …"
- "¿Qué me habías guardado sobre el proyecto X?"
- "Todos los lunes a las 8am, mándame mis pendientes de la semana."

Durante una o dos semanas, observa tres cosas:
1. ¿Recuerda bien entre sesiones lo que le dices?
2. ¿Los recordatorios programados te llegan y te sirven?
3. ¿Qwen 14B interpreta bien tus instrucciones, o se confunde seguido?

Eso te dará la respuesta que ninguna planeación previa puede dar: si Hermes te
organiza tal cual, o si necesitas construir piezas a medida (probablemente las
finanzas estructuradas) encima.

---

## 7. Comandos de referencia

```bash
hermes                 # chat en terminal
hermes model           # cambiar proveedor/modelo
hermes tools           # activar/desactivar herramientas
hermes gateway start   # arrancar mensajería
hermes gateway setup   # reconfigurar plataformas
hermes update          # actualizar a la última versión
hermes doctor          # diagnosticar problemas
```

Documentación oficial: https://hermes-agent.nousresearch.com/docs/

---

## Notas y cautelas

- **Privacidad:** con Qwen local + Hermes autoalojado, tus datos no salen del
  servidor. Pero si activas herramientas como búsqueda web o un proveedor de modelo
  en la nube, eso sí sale. Revisa `hermes tools` y deja activo solo lo que quieras.
- **Audios:** dependen de ffmpeg (paso 1) y de la cadena de transcripción que use
  Hermes; si los audios fallan, revisa primero ffmpeg.
- **Proyecto nuevo:** Hermes es de 2026 y se actualiza muy seguido. Espera algún
  cambio o aspereza; `hermes update` y `hermes doctor` son tus aliados.
- **Seguridad del bot:** asegúrate de restringir el bot a tu usuario (paso 4). Un
  bot de Telegram abierto puede recibir mensajes de cualquiera.
