FROM python:3.12-slim

WORKDIR /app

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

# Camada cacheada — só reinstala quando requirements.txt mudar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["bash", "release.sh"]
