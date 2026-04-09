#!/bin/bash
# Release script para Railway - aplica migrations antes de iniciar o app

# Garante que estamos no diretório do script (onde está o alembic.ini)
cd "$(dirname "$0")"

echo "🔄 Aplicando migrations do Alembic..."

# Aplica migrations pendentes (stamp head é automático se o banco já existir)
python3 -m alembic upgrade head
if [ $? -ne 0 ]; then
    echo "❌ Erro ao aplicar migrations"
    exit 1
fi

echo "✅ Migrations aplicadas com sucesso!"
echo "🚀 Iniciando aplicação..."

# Define porta padrão se $PORT não estiver definida
PORT=${PORT:-8000}

# Uvicorn só aplica X-Forwarded-Proto / Host dos proxies se o IP do cliente estiver
# em FORWARDED_ALLOW_IPS. O default do Uvicorn é 127.0.0.1 — atrás de Railway +
# Cloudflare o ASGI scope fica scheme=http, e redirects (ex. 307 trailing slash)
# devolvem Location: http://... → Mixed Content no browser.
# * = confiar em qualquer IP que fale com o container (típico PaaS só exposto ao LB).
export FORWARDED_ALLOW_IPS="${FORWARDED_ALLOW_IPS:-*}"
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips "$FORWARDED_ALLOW_IPS"
