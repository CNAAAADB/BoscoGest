# Imagen base con Python
FROM python:3.11-slim

# Crear directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema necesarias para psycopg2
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    postgresql-client && \
    rm -rf /var/lib/apt/lists/*

# Copiar dependencias
COPY requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el código
COPY app/ ./app
COPY alembic.ini .
COPY alembic ./alembic

COPY start.sh ./start.sh
RUN chmod +x ./start.sh

# Exponer puerto
EXPOSE 8000

# Usar el script de arranque
CMD ["./start.sh"]