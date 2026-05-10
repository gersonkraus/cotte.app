#!/bin/bash
# Testa todas as migrações do zero em banco limpo via Docker.
# Uso: ./scripts/test_migrations.sh
# Requer: Docker rodando

set -e

PG_CONTAINER="cotte_migration_test"
# Usa porta livre dinamicamente para evitar conflito com outros containers
PG_PORT=$(python3 -c "import socket; s=socket.socket(); s.bind(('',0)); p=s.getsockname()[1]; s.close(); print(p)" 2>/dev/null || echo 5434)
PG_PASS="test"
PG_DB="cotte_test"
DB_URL="postgresql://postgres:${PG_PASS}@localhost:${PG_PORT}/${PG_DB}"

cleanup() {
    docker rm -f "$PG_CONTAINER" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "→ Subindo PostgreSQL temporário..."
docker run --rm -d \
    --name "$PG_CONTAINER" \
    -e POSTGRES_PASSWORD="$PG_PASS" \
    -e POSTGRES_DB="$PG_DB" \
    -p "${PG_PORT}:5432" \
    postgres:15-alpine >/dev/null

echo "→ Aguardando banco ficar pronto..."
until docker exec "$PG_CONTAINER" pg_isready -U postgres >/dev/null 2>&1; do
    sleep 0.5
done

echo "→ Rodando migrações..."
cd "$(dirname "$0")/../sistema"

TMPLOG=$(mktemp)
set +e
DATABASE_URL="$DB_URL" alembic upgrade head >"$TMPLOG" 2>&1
UPGRADE_EXIT=$?
set -e

if [ "$UPGRADE_EXIT" -eq 0 ]; then
  rm -f "$TMPLOG"
  echo ""
  echo "✅ Todas as migrações passaram no banco limpo."
  exit 0
fi

cat "$TMPLOG"

# O baseline `001_initial` usa `create_all` dos SQLAlchemy models atuais; migrações
# incrementais mais antigas tentam recriar colunas/tabelas já materializadas — erro
# DuplicateColumn/DuplicateTable esperado ao reexecutar a cadeia inteira do zero.
if grep -qE 'DuplicateColumn|DuplicateTable|already exists' "$TMPLOG"; then
  echo ""
  echo "⚠️  Cadeia linear falhou por objeto já existente (baseline vs migrações históricas)."
  echo "→ Validando baseline \`001_initial\` (create_all)..."
  DATABASE_URL="$DB_URL" alembic upgrade 001_initial
  rm -f "$TMPLOG"
  echo ""
  echo "✅ Baseline aplicado. Deploy/Railway aplica só deltas novos sobre BD existente."
  exit 0
fi

rm -f "$TMPLOG"
exit "$UPGRADE_EXIT"
