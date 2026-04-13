# Build stage — instalar dependências em /install
FROM python:3.12-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /tmpdeps

# Dependências do sistema necessárias (WeasyPrint + etc)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libglib2.0-0 \
    libgobject-2.0-0 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libharfbuzz0b \
    libgdk-pixbuf-2.0-0 \
    fontconfig \
    libffi-dev \
    shared-mime-info \
    libxml2 \
    libxslt1-dev \
    libpangoft2-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copiar apenas requirements para cache da camada
COPY requirements.txt .

# Instalar dependências para um diretório isolado
RUN pip install --no-cache-dir --disable-pip-version-check --target=/install -r requirements.txt

# Runtime stage
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Instalar libs de sistema necessárias no runtime (idem builder)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgobject-2.0-0 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libharfbuzz0b \
    libgdk-pixbuf-2.0-0 \
    fontconfig \
    shared-mime-info \
    libxml2 \
    libxslt1-dev \
    libpangoft2-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copiar só os pacotes Python instalados no builder
COPY --from=builder /install /install
ENV PYTHONPATH=/install:$PYTHONPATH

# Copiar apenas o código e arquivos necessários
# cotte-frontend/ é obrigatório: app.main monta StaticFiles em _BASE_DIR/cotte-frontend → /app/cotte-frontend
COPY app/ ./app/
COPY cotte-frontend/ ./cotte-frontend/
COPY alembic/ ./alembic/
COPY alembic.ini ./alembic.ini
COPY release.sh ./release.sh
COPY Procfile ./Procfile
COPY static/ ./static/
# Ajuste acima conforme arquivos realmente necessários

# Garantir permissão de execução
RUN chmod +x ./release.sh || true

EXPOSE 8000
CMD ["bash", "release.sh"]