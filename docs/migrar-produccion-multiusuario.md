# Migrar producción a multi-usuario (runbook)

Convierte la instancia de producción (single-tenant, datos en `public`) al modelo
multi-inquilino, y despliega el código nuevo. **Interactivo y con backup.** El
orden importa: primero se convierten los datos, luego corre el deploy normal.

> Se hace sobre la instancia existente en el servidor (p. ej.
> `/opt/puiky/instances/ricardozo`, proyecto `puiky-ricardozo`). Ajusta
> `PROJECT`/carpeta si difiere.

## 0. Requisitos
- La rama `multi-usuario` probada en dev (ya está).
- Ventana de unos minutos (la web/bot se reinician).

## 1. Backup (imprescindible)
```bash
cd /opt/puiky/instances/ricardozo
docker compose -p puiky-ricardozo -f docker-compose.prod.yml exec -T db \
  pg_dump -U puiky puiky | gzip > ~/puiky-backup-$(date +%F-%H%M).sql.gz
ls -lh ~/puiky-backup-*.sql.gz
```

## 2. Ensayo sobre una COPIA (no tocar la real todavía)
```bash
# Restaurar el backup en una BD de ensayo dentro del mismo Postgres
docker compose -p puiky-ricardozo -f docker-compose.prod.yml exec -T db \
  psql -U puiky -c "CREATE DATABASE puiky_ensayo"
zcat ~/puiky-backup-*.sql.gz | \
  docker compose -p puiky-ricardozo -f docker-compose.prod.yml exec -T db \
  psql -U puiky -d puiky_ensayo

# Traer el código nuevo y correr la migración contra la COPIA
git fetch origin && git checkout multi-usuario && git pull
docker compose -p puiky-ricardozo -f docker-compose.prod.yml build app
docker compose -p puiky-ricardozo -f docker-compose.prod.yml run --rm \
  -e POSTGRES_DB=puiky_ensayo app python -m app.migrate_to_multitenant ricardozo <TU_TELEGRAM_ID>
# Verificar (debe listar control en public y dominio en t_ricardozo, con datos)
docker compose -p puiky-ricardozo -f docker-compose.prod.yml run --rm \
  -e POSTGRES_DB=puiky_ensayo app python -m app.migrate_all
```
Si el ensayo se ve bien, borra la copia:
```bash
docker compose -p puiky-ricardozo -f docker-compose.prod.yml exec -T db \
  psql -U puiky -c "DROP DATABASE puiky_ensayo"
```

## 3. Migración REAL
```bash
# Parar los servicios vivos (la BD sigue arriba)
docker compose -p puiky-ricardozo -f docker-compose.prod.yml stop app bot scheduler web

# Convertir los datos reales (public -> t_ricardozo) y enlazar tu Telegram
docker compose -p puiky-ricardozo -f docker-compose.prod.yml run --rm \
  app python -m app.migrate_to_multitenant ricardozo <TU_TELEGRAM_ID>
```

## 4. Deploy del código nuevo
```bash
docker compose -p puiky-ricardozo -f docker-compose.prod.yml up -d --build
docker compose -p puiky-ricardozo -f docker-compose.prod.yml ps
```
El servicio `migrate` (ahora `migrate_all`) corre control + t_ricardozo (idempotente),
y app/bot/scheduler arrancan con el código multi-usuario.

## 5. Verificar
- Web `https://puiky.iconred.co`: entra con tu usuario → tus datos siguen ahí.
- Bot: escríbele → te reconoce (por `telegram_link`).

## 6. Alta de la familia
Por cada familiar (su bot ya no hace falta: es el mismo bot compartido):
```bash
./scripts/crear-usuario.sh mama     # pide usuario, contraseña y su ID de Telegram
```
Crea su schema + login + enlace de Telegram. Sin puerto, sin túnel, sin bot nuevos.

## Rollback
Si algo sale mal en el paso 3/4, restaurar el backup:
```bash
docker compose -p puiky-ricardozo -f docker-compose.prod.yml stop app bot scheduler web
docker compose -p puiky-ricardozo -f docker-compose.prod.yml exec -T db \
  psql -U puiky -c "DROP DATABASE puiky; CREATE DATABASE puiky"
zcat ~/puiky-backup-*.sql.gz | docker compose -p puiky-ricardozo \
  -f docker-compose.prod.yml exec -T db psql -U puiky -d puiky
git checkout main && docker compose -p puiky-ricardozo -f docker-compose.prod.yml up -d --build
```
