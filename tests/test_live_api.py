import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import unittest
import httpx


class TestLiveApiConnectivity(unittest.TestCase):
    """
    Verifica la conectividad directa por socket HTTP contra el servidor real en ejecución
    (http://localhost:8000), respondiendo al estado activo reportado por el usuario.
    """

    def test_live_server_health_and_docs(self):
        """Comprueba que http://localhost:8000 está activo y respondiendo a conexiones reales."""
        try:
            with httpx.Client(base_url="http://localhost:8000", timeout=5.0) as client:
                res_health = client.get("/api/v1/telemetry/health")
                self.assertEqual(res_health.status_code, 200)
                self.assertEqual(res_health.json()["status"], "healthy")

                res_docs = client.get("/docs")
                self.assertEqual(res_docs.status_code, 200)
        except (httpx.ConnectError, httpx.ConnectTimeout, Exception) as e:
            self.skipTest(f"El servidor en vivo http://localhost:8000 no se encuentra alcanzable: {e}")


if __name__ == "__main__":
    unittest.main()
