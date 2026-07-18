#!/usr/bin/env bash
# Crea (o recrea) una instancia aislada de Puiky en el servidor Ubuntu.
#
#   ./scripts/crear-instancia.sh <nombre>
#
# Cada instancia vive en su propia carpeta con su propio .env y su propio
# stack de Docker (Postgres, app, web, bot, scheduler). Datos aislados.
# Todas comparten el mismo Ollama/Qwen del servidor.
#
# Variables de entorno opcionales:
#   INSTANCES_DIR   carpeta base de instancias (default: /opt/puiky/instances)
#   REPO_URL        repo git a clonar (default: el 'origin' de este checkout)
set -euo pipefail

# --- utilidades ---
rand()  { openssl rand -hex "${1:-32}"; }
ask()   { local p="$1" d="${2:-}" r; if [[ -n "$d" ]]; then read -rp "$p [$d]: " r; echo "${r:-$d}"; else read -rp "$p: " r; echo "$r"; fi; }
die()   { echo "ERROR: $*" >&2; exit 1; }

# --- argumentos ---
NOMBRE="${1:-}"
[[ -n "$NOMBRE" ]] || die "Uso: $0 <nombre>   (ej: $0 mama)"
[[ "$NOMBRE" =~ ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$ ]] || die "Nombre inválido (usa minúsculas, números y guiones): $NOMBRE"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
INSTANCES_DIR="${INSTANCES_DIR:-/opt/puiky/instances}"
REPO_URL="${REPO_URL:-$(git -C "$REPO_DIR" remote get-url origin 2>/dev/null || echo "")}"
DEST="$INSTANCES_DIR/$NOMBRE"
PROJECT="puiky-$NOMBRE"

echo "== Crear instancia Puiky: $NOMBRE =="
echo "  carpeta:  $DEST"
echo "  proyecto: $PROJECT"
echo

# --- 1) obtener el código en la carpeta de la instancia ---
mkdir -p "$INSTANCES_DIR"
if [[ ! -d "$DEST" ]]; then
  if [[ -n "$REPO_URL" ]]; then
    echo "-> Clonando $REPO_URL"
    git clone "$REPO_URL" "$DEST"
  else
    echo "-> Copiando el checkout actual (sin remoto git)"
    git -C "$REPO_DIR" archive HEAD | (mkdir -p "$DEST" && tar -x -C "$DEST")
  fi
else
  echo "-> La carpeta ya existe; se reutiliza (git pull si aplica)."
  git -C "$DEST" pull --ff-only 2>/dev/null || true
fi

# --- 2) elegir puerto web libre (único por instancia) ---
PUERTO_SUGERIDO=8080
if compgen -G "$INSTANCES_DIR/*/.env" > /dev/null; then
  MAX=$(grep -hoE '^WEB_PORT=[0-9]+' "$INSTANCES_DIR"/*/.env 2>/dev/null | cut -d= -f2 | sort -n | tail -1 || echo 8079)
  PUERTO_SUGERIDO=$(( MAX + 1 ))
fi

# --- 3) datos de la instancia (interactivo) ---
if [[ -f "$DEST/.env" ]]; then
  echo "-> Ya existe $DEST/.env; se conserva. (Borra el archivo para regenerarlo.)"
else
  echo "-- Datos de la instancia --"
  BOT_TOKEN="$(ask 'Token del bot de Telegram (@BotFather)')"
  ALLOWED_IDS="$(ask 'IDs de Telegram autorizados (coma-separados)')"
  WEB_PORT="$(ask 'Puerto web (loopback)' "$PUERTO_SUGERIDO")"
  LLM_URL="$(ask 'URL de Ollama (LLM)' 'http://10.144.82.100:11434/v1')"
  HOSTNAME_PUB="$(ask 'Hostname público (Cloudflare)' "puiky-$NOMBRE.tudominio.com")"

  echo "-> Generando $DEST/.env"
  cp "$DEST/.env.prod.example" "$DEST/.env"
  # Sustituciones (| como delimitador porque hay / en URLs)
  sed -i \
    -e "s|^INSTANCIA=.*|INSTANCIA=$NOMBRE|" \
    -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(rand 24)|" \
    -e "s|^POSTGRES_DB=.*|POSTGRES_DB=puiky_$NOMBRE|" \
    -e "s|^WEB_PORT=.*|WEB_PORT=$WEB_PORT|" \
    -e "s|^LLM_BASE_URL=.*|LLM_BASE_URL=$LLM_URL|" \
    -e "s|^TELEGRAM_BOT_TOKEN=.*|TELEGRAM_BOT_TOKEN=$BOT_TOKEN|" \
    -e "s|^TELEGRAM_ALLOWED_IDS=.*|TELEGRAM_ALLOWED_IDS=$ALLOWED_IDS|" \
    -e "s|^JWT_SECRET=.*|JWT_SECRET=$(rand 32)|" \
    -e "s|^SERVICE_TOKEN=.*|SERVICE_TOKEN=$(rand 32)|" \
    -e "s|^CORS_ORIGINS=.*|CORS_ORIGINS=https://$HOSTNAME_PUB|" \
    "$DEST/.env"
fi

# --- 4) levantar el stack ---
echo "-> Construyendo y levantando el stack ($PROJECT)…"
cd "$DEST"
docker compose -p "$PROJECT" -f docker-compose.prod.yml up -d --build

# --- 5) esperar a la API y crear el usuario web ---
echo "-> Esperando a que la API responda…"
for i in $(seq 1 60); do
  if docker compose -p "$PROJECT" -f docker-compose.prod.yml exec -T app \
       python -c "import urllib.request as u; u.urlopen('http://localhost:8000/health')" 2>/dev/null; then
    break
  fi
  sleep 3
done

echo "-- Usuario de la web --"
WEB_USER="$(ask 'Usuario web' "$NOMBRE")"
read -rsp "Contraseña web: " WEB_PASS; echo
docker compose -p "$PROJECT" -f docker-compose.prod.yml exec -T app \
  python -m app.create_user "$WEB_USER" "$WEB_PASS"

# --- 6) instrucciones de túnel ---
WEB_PORT_FINAL=$(grep -oE '^WEB_PORT=[0-9]+' "$DEST/.env" | cut -d= -f2)
HOST_FINAL=$(grep -oE '^CORS_ORIGINS=.*' "$DEST/.env" | cut -d= -f2- | sed 's|https\?://||')
cat <<EOF

== Instancia '$NOMBRE' lista ==
  Stack:  docker compose -p $PROJECT -f docker-compose.prod.yml ps
  Web local:  http://127.0.0.1:$WEB_PORT_FINAL

  ÚLTIMO PASO — Cloudflare Tunnel:
  Añade un public hostname en tu túnel apuntando a esta instancia:
     Hostname : $HOST_FINAL
     Service  : http://localhost:$WEB_PORT_FINAL
  (Dashboard: Zero Trust > Networks > Tunnels > tu túnel > Public Hostname.
   O en config.yml de cloudflared, una regla de ingress equivalente.)
EOF
