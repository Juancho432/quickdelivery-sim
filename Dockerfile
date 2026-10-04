FROM python:3.11-slim

# Evitar escritura de bytecode y habilitar salida estándar sin buffer para logs inmediatos
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias mínimas del sistema para compilar psutil y psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias Python con versiones fijadas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente completo del proyecto
COPY . .
RUN mkdir -p /app/datos

# Crear usuario sin privilegios root para buenas prácticas de seguridad en contenedores
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Healthcheck interno del contenedor
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/telemetry/health || exit 1

# Servidor ASGI Uvicorn multi-worker para alta concurrencia
CMD ["uvicorn", "sistema_real.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
