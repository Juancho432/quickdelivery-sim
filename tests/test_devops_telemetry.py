import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import unittest
from tests.base import TestQuickDeliveryAPIBase


class TestDevOpsAndTelemetry(TestQuickDeliveryAPIBase):
    """Pruebas del Endpoint E13 y Middleware de Telemetría (Criterio R8)."""

    def test_healthcheck_positive(self):
        """Camino positivo E13: Verificar diagnóstico de salud, hardware y conexión a PostgreSQL."""
        response = self.client.get("/api/v1/telemetry/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["database"], "connected")
        self.assertGreaterEqual(data["cpu_percent"], 0.0)
        self.assertGreater(data["memory_mb"], 0.0)
        self.assertGreaterEqual(data["latency_avg_ms"], 0.0)
        self.assertGreaterEqual(data["uptime_seconds"], 0.0)

    def test_telemetry_middleware_latency_recording(self):
        """Camino positivo: Comprobar que el middleware registra las peticiones HTTP con psutil."""
        res1 = self.client.get("/api/v1/config/")
        self.assertEqual(res1.status_code, 200)
        
        health_res = self.client.get("/api/v1/telemetry/health")
        self.assertEqual(health_res.status_code, 200)
        health_data = health_res.json()
        self.assertIn("latency_avg_ms", health_data)


if __name__ == "__main__":
    unittest.main()
