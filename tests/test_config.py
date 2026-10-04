import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import unittest
from tests.base import TestQuickDeliveryAPIBase


class TestSystemConfiguration(TestQuickDeliveryAPIBase):
    """Pruebas del Endpoint E12 (GET y PUT /api/v1/config/) para control en tiempo real."""

    def test_get_config_positive(self):
        """Camino positivo E12a: Obtener parámetros operativos vigentes."""
        response = self.client.get("/api/v1/config/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("active_dispatch_policy", data)
        self.assertIn("buffer_delta_t_min", data)
        self.assertIn("max_shift_duration_min", data)
        self.assertIn("anti_limbo_max_counter_min", data)
        self.assertIn("urgency_bonus_multiplier", data)
        self.assertIn("min_battery_threshold_pct", data)

    def test_update_config_positive(self):
        """Camino positivo E12b: Actualizar dinámicamente la política y márgenes de holgura."""
        payload = {
            "active_dispatch_policy": "greedy",
            "buffer_delta_t_min": 3.5,
            "max_shift_duration_min": 300.0,
            "anti_limbo_max_counter_min": 15.0,
            "urgency_bonus_multiplier": 1.25,
            "min_battery_threshold_pct": 18.0
        }
        put_res = self.client.put("/api/v1/config/", json=payload)
        self.assertEqual(put_res.status_code, 200)
        data = put_res.json()
        self.assertEqual(data["active_dispatch_policy"], "greedy")
        self.assertEqual(data["buffer_delta_t_min"], 3.5)

        # Verificar que el cambio persiste en GET
        get_res = self.client.get("/api/v1/config/")
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.json()["active_dispatch_policy"], "greedy")

    def test_update_config_negative_out_of_bounds(self):
        """Camino negativo E12b: Intentar asignar parámetros fuera de rangos válidos de Pydantic."""
        # buffer_delta_t_min > 5.0
        invalid_payload_1 = {
            "active_dispatch_policy": "synchronized",
            "buffer_delta_t_min": 9.9,
            "max_shift_duration_min": 360.0,
            "anti_limbo_max_counter_min": 20.0,
            "urgency_bonus_multiplier": 1.20,
            "min_battery_threshold_pct": 15.0
        }
        res1 = self.client.put("/api/v1/config/", json=invalid_payload_1)
        self.assertEqual(res1.status_code, 422)

        # min_battery_threshold_pct > 30.0
        invalid_payload_2 = {
            "active_dispatch_policy": "synchronized",
            "buffer_delta_t_min": 2.0,
            "max_shift_duration_min": 360.0,
            "anti_limbo_max_counter_min": 20.0,
            "urgency_bonus_multiplier": 1.20,
            "min_battery_threshold_pct": 45.0
        }
        res2 = self.client.put("/api/v1/config/", json=invalid_payload_2)
        self.assertEqual(res2.status_code, 422)


if __name__ == "__main__":
    unittest.main()
