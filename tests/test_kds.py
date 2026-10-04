import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import uuid
import unittest
from tests.base import TestQuickDeliveryAPIBase


class TestKitchenKDSFlow(TestQuickDeliveryAPIBase):
    """Pruebas de los Endpoints de KDS E4 y E5 (Exclusión 2 y Promoción FIFO D-09)."""

    def test_get_kds_orders_positive_and_exclusion_2(self):
        """Camino positivo E4: Pantalla KDS no expone recetas ni ingredientes (Exclusión 2 D-11)."""
        rest_id = 3
        # Crear comanda
        self.client.post("/api/v1/orders/", json={
            "customer_id": f"CUST-KDS-{uuid.uuid4().hex[:4]}",
            "restaurant_id": rest_id,
            "delivery_coord_x": 1.5,
            "delivery_coord_y": 2.5
        })

        kds_res = self.client.get(f"/api/v1/restaurants/{rest_id}/orders")
        self.assertEqual(kds_res.status_code, 200)
        items = kds_res.json()
        self.assertIsInstance(items, list)
        self.assertGreater(len(items), 0)

        # Verificar campos exactos y ausencia de ingredientes/recetas
        for order in items:
            self.assertIn("order_id", order)
            self.assertIn("restaurant_id", order)
            self.assertIn("status", order)
            self.assertIn("tiempo_espera_cola_min", order)
            self.assertIn("eta_listo", order)
            self.assertNotIn("recipes", order)
            self.assertNotIn("ingredients", order)
            self.assertNotIn("dishes", order)

    def test_get_kds_orders_with_status_filter(self):
        """Camino positivo E4: Filtrar comandas por estado específico."""
        rest_id = 3
        filter_res = self.client.get(f"/api/v1/restaurants/{rest_id}/orders?status_filter=EN_PREPARACION")
        self.assertEqual(filter_res.status_code, 200)
        for order in filter_res.json():
            self.assertEqual(order["status"], "EN_PREPARACION")

    def test_mark_order_ready_positive_and_fifo_promotion(self):
        """Camino positivo E5: Fin de cocción pasa a LISTO_EN_MOSTRADOR, activa bono urgente y promueve FIFO."""
        rest_id = 2  # Capacidad 4
        order_res = self.client.post("/api/v1/orders/", json={
            "customer_id": f"CUST-RDY-{uuid.uuid4().hex[:4]}",
            "restaurant_id": rest_id,
            "delivery_coord_x": 2.5,
            "delivery_coord_y": 3.0
        })
        order_id = order_res.json()["id"]

        ready_res = self.client.post(f"/api/v1/orders/{order_id}/ready")
        self.assertEqual(ready_res.status_code, 200)
        data = ready_res.json()
        self.assertEqual(data["status"], "LISTO_EN_MOSTRADOR")
        self.assertTrue(data["is_urgent"])
        self.assertIsNotNone(data["t_listo"])

    def test_mark_order_ready_negative_not_found(self):
        """Camino negativo E5: Intentar marcar lista una orden inexistente retorna 404."""
        res = self.client.post("/api/v1/orders/999999/ready")
        self.assertEqual(res.status_code, 404)


if __name__ == "__main__":
    unittest.main()
