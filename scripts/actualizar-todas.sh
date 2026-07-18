#!/usr/bin/env bash
# Actualiza todas las instancias de Puiky: git pull + rebuild + up -d.
# Las migraciones se aplican solas (servicio `migrate` one-shot).
#
#   ./scripts/actualizar-todas.sh            # todas
#   ./scripts/actualizar-todas.sh mama papa  # solo esas
set -euo pipefail

INSTANCES_DIR="${INSTANCES_DIR:-/opt/puiky/instances}"

if [[ $# -gt 0 ]]; then
  NOMBRES=("$@")
else
  NOMBRES=()
  for d in "$INSTANCES_DIR"/*/; do
    [[ -f "$d/docker-compose.prod.yml" ]] && NOMBRES+=("$(basename "$d")")
  done
fi

[[ ${#NOMBRES[@]} -gt 0 ]] || { echo "No hay instancias en $INSTANCES_DIR"; exit 0; }

for NOMBRE in "${NOMBRES[@]}"; do
  DEST="$INSTANCES_DIR/$NOMBRE"
  PROJECT="puiky-$NOMBRE"
  echo "== Actualizando $NOMBRE =="
  [[ -d "$DEST" ]] || { echo "  (no existe $DEST, se omite)"; continue; }
  git -C "$DEST" pull --ff-only || { echo "  git pull falló, se omite"; continue; }
  docker compose -p "$PROJECT" -f "$DEST/docker-compose.prod.yml" \
    --project-directory "$DEST" up -d --build
  echo "  ok"
done

echo "== Listo =="
