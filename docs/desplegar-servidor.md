# Desplegar Puiky en el servidor Ubuntu

Guía de puesta en producción y de creación de instancias para la familia.

- **Aislamiento:** una instancia = un stack de Docker con su propio Postgres,
  app, web, bot y scheduler. Los datos **no se cruzan** entre personas.
- **Compartido:** todas usan el mismo **Ollama/Qwen** del servidor (el modelo
  no guarda datos; cada petición es independiente).
- **Exposición:** cada instancia publica su web en un puerto de loopback y
  **Cloudflare Tunnel** la enruta a un hostname público. La API viaja por el
  mismo origen (nginx hace proxy de `/api`), así que no hay líos de CORS.
- **El bot de Telegram** usa long-polling (sale hacia afuera): **no** necesita
  túnel de entrada. Solo la web se expone.

---

## 0. Prerrequisitos en el servidor

```bash
docker --version && docker compose version   # Docker + plugin compose
git --version
openssl version
cloudflared --version                         # el túnel que ya manejas
# Ollama con el modelo cargado:
curl -s http://10.144.82.100:11434/api/tags | grep qwen3   # debe listar qwen3:14b
```

Si falta el modelo:  `ollama pull qwen3:14b`

---

## 1. Repo privado en GitHub (una vez)

Desde tu Windows, en `c:\proyectos\Puiky`:

```bash
# Crea el repo privado y sube (necesita gh autenticado, o hazlo por la web).
gh repo create puiky --private --source=. --remote=origin --push
# Alternativa manual:
#   git remote add origin git@github.com:<tu-usuario>/puiky.git
#   git push -u origin main
```

> `.env`, `node_modules`, `dist` y `.venv` están en `.gitignore`: **los secretos
> no se suben**. Solo va el código y las plantillas (`*.example`).

En el servidor, prepara una llave de acceso al repo privado (deploy key o
`gh auth login`), y clona la base:

```bash
sudo mkdir -p /opt/puiky && sudo chown "$USER" /opt/puiky
git clone git@github.com:<tu-usuario>/puiky.git /opt/puiky/instances/ricardo
```

---

## 2. Tu instancia (manual, para validar de punta a punta)

```bash
cd /opt/puiky/instances/ricardo
cp .env.prod.example .env
nano .env
```

Ajusta en `.env`:

| Variable | Valor |
|---|---|
| `POSTGRES_PASSWORD` | `openssl rand -hex 24` |
| `POSTGRES_DB` | `puiky_ricardo` |
| `WEB_PORT` | `8080` (único por instancia) |
| `LLM_BASE_URL` | `http://10.144.82.100:11434/v1` |
| `TELEGRAM_BOT_TOKEN` | tu token de @BotFather |
| `TELEGRAM_ALLOWED_IDS` | tu ID de Telegram |
| `JWT_SECRET` | `openssl rand -hex 32` |
| `SERVICE_TOKEN` | `openssl rand -hex 32` |
| `CORS_ORIGINS` | `https://puiky.tudominio.com` |

Levanta el stack (la primera vez descarga imágenes y el modelo de embeddings,
tarda unos minutos):

```bash
docker compose -p puiky-ricardo -f docker-compose.prod.yml up -d --build
docker compose -p puiky-ricardo -f docker-compose.prod.yml ps
```

Crea tu usuario web:

```bash
docker compose -p puiky-ricardo -f docker-compose.prod.yml exec app \
  python -m app.create_user ricardo 'TU-CONTRASEÑA'
```

Prueba local (antes del túnel):

```bash
curl -s http://127.0.0.1:8080/api/health     # {"status":"ok"} vía nginx→app
curl -s http://127.0.0.1:8080/ | head        # el HTML del SPA
```

---

## 3. Cloudflare Tunnel

Añade un **public hostname** a tu túnel existente apuntando a la web local:

- **Dashboard:** Zero Trust → Networks → Tunnels → *tu túnel* → *Public Hostname* → Add:
  - **Subdomain/Hostname:** `puiky` (→ `puiky.tudominio.com`)
  - **Service:** `HTTP` → `localhost:8080`

- **O** en `config.yml` de cloudflared:
  ```yaml
  ingress:
    - hostname: puiky.tudominio.com
      service: http://localhost:8080
    # … tus otras reglas …
    - service: http_status:404
  ```
  y `sudo systemctl restart cloudflared`.

Verifica: abre `https://puiky.tudominio.com`, inicia sesión, crea una nota, y
escríbele al bot por Telegram («gasté 5 mil en café»). Si el bot responde con la
confirmación natural, Qwen está conectado correctamente.

---

## 4. Instancias de la familia (automatizado)

Para cada familiar necesitas: su **token de bot** (que cree con @BotFather) y su
**ID de Telegram** (que le escriba al bot y este le responde con su ID).

```bash
cd /opt/puiky/instances/ricardo    # cualquier checkout con los scripts
./scripts/crear-instancia.sh mama
```

El script clona el repo en `/opt/puiky/instances/mama`, genera `.env` con
**secretos aleatorios** y **BD propia** (`puiky_mama`), asigna un **puerto libre**,
levanta el stack, aplica migraciones, crea el usuario web y te imprime la regla
de Cloudflare a añadir (`puiky-mama.tudominio.com → localhost:<puerto>`).

Repite el paso 3 (Cloudflare) con el hostname/puerto que imprime el script.

---

## 5. Operación

```bash
# Estado / logs de una instancia
docker compose -p puiky-mama -f docker-compose.prod.yml ps
docker compose -p puiky-mama -f docker-compose.prod.yml logs -f app bot

# Reiniciar un servicio
docker compose -p puiky-mama -f docker-compose.prod.yml restart bot

# Actualizar TODAS las instancias (git pull + rebuild; migra solo)
./scripts/actualizar-todas.sh
# o algunas:  ./scripts/actualizar-todas.sh ricardo mama

# Backup de una instancia (BD)
docker compose -p puiky-mama -f docker-compose.prod.yml exec -T db \
  pg_dump -U puiky puiky_mama | gzip > backup-mama-$(date +%F).sql.gz

# Bajar / borrar una instancia (¡-v borra los datos!)
docker compose -p puiky-mama -f docker-compose.prod.yml down        # detiene
docker compose -p puiky-mama -f docker-compose.prod.yml down -v      # + borra BD
```

---

## Notas

- **RAM:** cada instancia carga su propio modelo de embeddings (e5, ~1 GB). Para
  pocos familiares está bien; a futuro se puede extraer a un microservicio de
  embeddings compartido.
- **Un bot por instancia:** nunca compartas un token entre instancias (daría
  conflicto 409 en Telegram).
- **Puertos:** `WEB_PORT` debe ser único por instancia (8080, 8081, …). El script
  lo asigna solo.
- **Ollama:** si los contenedores no alcanzan `10.144.82.100:11434`, usa
  `http://host.docker.internal:11434/v1` y añade en cada servicio del compose
  `extra_hosts: ["host.docker.internal:host-gateway"]`.
