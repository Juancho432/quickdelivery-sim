import os
import time
import psutil
from datetime import datetime, timezone
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Ruta del archivo de registro en volumen persistente
DATA_DIR = os.getenv("DATA_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "datos"))
TELEMETRY_CSV_PATH = os.path.join(DATA_DIR, "telemetry_log.csv")
CSV_HEADER = "timestamp,method,path,status_code,latency_ms,cpu_percent,memory_mb\n"

# Variables en memoria para estadísticas agregadas del healthcheck
_recent_latencies = []
_process = psutil.Process()


def init_telemetry_file():
    """Inicializa el directorio y el archivo CSV con sus encabezados si no existen."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(TELEMETRY_CSV_PATH) or os.path.getsize(TELEMETRY_CSV_PATH) == 0:
        with open(TELEMETRY_CSV_PATH, "w", encoding="utf-8") as f:
            f.write(CSV_HEADER)


def record_metric(method: str, path: str, status_code: int, latency_ms: float, cpu_pct: float, mem_mb: float):
    """Escritura atómica de una línea de métricas en telemetry_log.csv."""
    iso_timestamp = datetime.now(timezone.utc).isoformat()
    line = f"{iso_timestamp},{method},{path},{status_code},{latency_ms:.2f},{cpu_pct:.1f},{mem_mb:.2f}\n"
    try:
        # Modo append con buffering=1 (line buffering) para atomicidad en POSIX/Windows
        with open(TELEMETRY_CSV_PATH, "a", buffering=1, encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        # Evitar que un error de I/O de telemetría tire la respuesta HTTP
        print(f"[Telemetry Error] No se pudo escribir métrica: {e}")


class TelemetryMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        init_telemetry_file()

    async def dispatch(self, request: Request, call_next) -> Response:
        # Ignorar solicitudes de favicon o docs para no ensuciar la telemetría del dominio si se desea
        # pero registrar todos los endpoints de api/v1
        start_time = time.perf_counter()
        
        response = await call_next(request)
        
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        
        # Muestreo de CPU y Memoria RSS en MB
        cpu_pct = psutil.cpu_percent(interval=None)
        mem_mb = _process.memory_info().rss / (1024.0 * 1024.0)

        # Registro en lista circular para diagnóstico de healthcheck (últimas 100 peticiones)
        _recent_latencies.append(duration_ms)
        if len(_recent_latencies) > 100:
            _recent_latencies.pop(0)

        # Escritura atómica inmediata en el CSV
        record_metric(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            latency_ms=duration_ms,
            cpu_pct=cpu_pct,
            mem_mb=mem_mb
        )

        return response


def get_telemetry_stats():
    """Devuelve estadísticas instantáneas para el endpoint de healthcheck."""
    avg_latency = sum(_recent_latencies) / len(_recent_latencies) if _recent_latencies else 0.0
    return {
        "cpu_percent": psutil.cpu_percent(interval=None),
        "memory_mb": _process.memory_info().rss / (1024.0 * 1024.0),
        "latency_avg_ms": round(avg_latency, 2)
    }
