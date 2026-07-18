#!/usr/bin/env bash
# Alta de un usuario en la instancia multi-usuario de Puiky (schema-per-tenant).
#
#   ./scripts/crear-usuario.sh <slug>
#
# Crea el schema del inquilino (t_<slug>), corre las migraciones de dominio,
# da de alta el login web y (opcional) enlaza su Telegram. Todo sobre la misma
# instancia y la misma URL: sin puerto, sin túnel, sin bot nuevos.
set -euo pipefail

PROJECT="${PUIKY_PROJECT:-puiky}"
COMPOSE="${PUIKY_COMPOSE:-docker-compose.prod.yml}"
dc() { docker compose -p "$PROJECT" -f "$COMPOSE" "$@"; }

SLUG="${1:-}"
[[ -n "$SLUG" ]] || { echo "Uso: $0 <slug>   (ej: $0 mama)"; exit 1; }

read -rp "Usuario web [$SLUG]: " USUARIO
USUARIO="${USUARIO:-$SLUG}"
read -rsp "Contraseña web: " PASS; echo
read -rp "ID de Telegram (opcional, Enter para omitir): " TGID

echo "-> Creando usuario '$USUARIO' e inquilino t_$SLUG…"
dc exec -T app python -m app.create_user "$USUARIO" "$PASS" "$SLUG"

if [[ -n "$TGID" ]]; then
  echo "-> Enlazando Telegram $TGID…"
  dc exec -T app python -m app.link_telegram "$USUARIO" "$TGID"
fi

cat <<EOF

== Usuario '$USUARIO' listo ==
  Web:  puede entrar en la misma URL de Puiky con su usuario y contraseña.
  Bot:  $( [[ -n "$TGID" ]] && echo "ya enlazado; puede escribirle al bot." || echo "sin Telegram; enlázalo luego con app.link_telegram." )
EOF
