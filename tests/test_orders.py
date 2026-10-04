import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import uuid
import unittest
from tests.base import TestQuickDeliveryAPIBase
from sistema_real.app.models import OrderModel, CourierModel


class TestClientOrderFlow(TestQuickDeliveryAPIBase):
    """Pruebas de los Endpoints de Clientes E1, E2, E3 y lógica culinaria FIFO / fogones."""

    def test_create_order_positive_free_burners(self):
        """Camino positivo E1: Si hay fogones libres, pasa directo a EN_PREPARACION."""
        payload = {
            "customer_id": f"CUST-{uuid.uuid4().hex[:6]}",
            "restaurant_id": 8,  # Capacidad 3 fogones
            "delivery_coord_x": 4.5,
            "delivery_coord_y": 3.2
        }
        res = self.client.post("/api/v1/orders/", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["status"], "EN_PREPARACION")
        self.assertEqual(data["eta_listo"], 18.5)
        self.assertIsNotNone(data["id"])

    def test_create_order_positive_burners_saturation_and_queueing(self):
        """Camino positivo E1: Llenar los fogones del local y verificar encolamiento FIFO."""
        rest_id = 8  # kitchen_capacity = 3
        created_orders = []

        # Crear 3 pedidos para ocupar todos los fogones
        for i in range(3):
            p = {
                "customer_id": f"CUST-BUR-{i}-{uuid.uuid4().hex[:4]}",
                "restaurant_id": rest_id,
                "delivery_coord_x": 3.0,
                "delivery_coord_y": 3.0
            }
            r = self.client.post("/api/v1/orders/", json=p)
            self.assertEqual(r.status_code, 201)
            self.assertEqual(r.json()["status"], "EN_PREPARACION")
            created_orders.append(r.json()["id"])

        # Crear el cuarto pedido: entra a EN_COLA_COCINA (primer pedido en cola, eta_listo = 18.5)
        overflow_payload = {
            "customer_id": f"CUST-OVERFLOW-1-{uuid.uuid4().hex[:4]}",
            "restaurant_id": rest_id,
            "delivery_coord_x": 3.5,
            "delivery_coord_y": 3.5
        }
        overflow_res1 = self.client.post("/api/v1/orders/", json=overflow_payload)
        self.assertEqual(overflow_res1.status_code, 201)
        self.assertEqual(overflow_res1.json()["status"], "EN_COLA_COCINA")
        self.assertEqual(overflow_res1.json()["eta_listo"], 18.5)

        # Crear el quinto pedido: segundo pedido en cola, eta_listo se incrementa (> 18.5)
        overflow_payload_2 = {
            "customer_id": f"CUST-OVERFLOW-2-{uuid.uuid4().hex[:4]}",
            "restaurant_id": rest_id,
            "delivery_coord_x": 3.8,
            "delivery_coord_y": 3.8
        }
        overflow_res2 = self.client.post("/api/v1/orders/", json=overflow_payload_2)
        self.assertEqual(overflow_res2.status_code, 201)
        self.assertEqual(overflow_res2.json()["status"], "EN_COLA_COCINA")
        self.assertGreater(overflow_res2.json()["eta_listo"], 18.5)

    def test_create_order_negative_validation_errors(self):
        """Camino negativo E1: Coordenadas fuera de cuadrante metropolitano [0.0, 6.0] o ID inválido."""
        # Coordenada X negativa
        res1 = self.client.post("/api/v1/orders/", json={
            "customer_id": "CUST-INV-1",
            "restaurant_id": 1,
            "delivery_coord_x": -0.5,
            "delivery_coord_y": 2.0
        })
        self.assertEqual(res1.status_code, 422)

        # Coordenada Y mayor a 6.0 km
        res2 = self.client.post("/api/v1/orders/", json={
            "customer_id": "CUST-INV-2",
            "restaurant_id": 1,
            "delivery_coord_x": 3.0,
            "delivery_coord_y": 6.8
        })
        self.assertEqual(res2.status_code, 422)

        # Restaurante fuera de catálogo (1 a 10)
        res3 = self.client.post("/api/v1/orders/", json={
            "customer_id": "CUST-INV-3",
            "restaurant_id": 99,
            "delivery_coord_x": 3.0,
            "delivery_coord_y": 3.0
        })
        self.assertEqual(res3.status_code, 422)

    def test_tracking_order_positive_unassigned_and_assigned(self):
        """Camino positivo E2: Rastreo sin courier y posterior rastreo con courier asignado."""
        # 1. Crear comanda
        order_res = self.client.post("/api/v1/orders/", json={
            "customer_id": f"CUST-TRK-{uuid.uuid4().hex[:4]}",
            "restaurant_id": 2,
            "delivery_coord_x": 4.0,
            "delivery_coord_y": 4.0
        })
        self.assertEqual(order_res.status_code, 201)
        order_id = order_res.json()["id"]

        # 2. Rastreo inicial sin courier
        trk_res1 = self.client.get(f"/api/v1/orders/{order_id}/tracking")
        self.assertEqual(trk_res1.status_code, 200)
        d1 = trk_res1.json()
        self.assertEqual(d1["order_id"], order_id)
        self.assertIsNone(d1["courier_id"])
        self.assertIsNone(d1["distancia_vial_restante_km"])

        # 3. Crear y asignar un courier determinista
        courier = self.create_courier(name="Courier-Track-Dedicated", x=2.0, y=2.0, battery=90.0)
        courier_id = courier.id

        db = self.get_db()
        order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
        order.courier_id = courier_id
        order.status = "ASIGNADO"
        db.commit()
        db.close()

        trk_res2 = self.client.get(f"/api/v1/orders/{order_id}/tracking")
        self.assertEqual(trk_res2.status_code, 200)
        d2 = trk_res2.json()
        self.assertEqual(d2["courier_id"], courier_id)
        self.assertIsNotNone(d2["distancia_vial_restante_km"])
        self.assertIsNotNone(d2["tiempo_llegada_est_min"])

    def test_tracking_order_negative_not_found(self):
        """Camino negativo E2: Consultar tracking de orden inexistente retorna 404."""
        res = self.client.get("/api/v1/orders/999999/tracking")
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.json()["detail"], "Orden no encontrada")

    def test_cancel_order_positive_and_fifo_promotion(self):
        """Camino positivo E3: Cancelación voluntaria en fogón promueve automáticamente el pedido en cola."""
        rest_id = 7  # Capacidad 4 fogones

        # Llenar fogones
        active_ids = []
        for i in range(4):
            r = self.client.post("/api/v1/orders/", json={
                "customer_id": f"CUST-CANC-OCC-{i}",
                "restaurant_id": rest_id,
                "delivery_coord_x": 2.0,
                "delivery_coord_y": 2.0
            })
            active_ids.append(r.json()["id"])

        # Encolar un pedido
        queue_res = self.client.post("/api/v1/orders/", json={
            "customer_id": "CUST-QUEUED-FOR-PROMO",
            "restaurant_id": rest_id,
            "delivery_coord_x": 2.5,
            "delivery_coord_y": 2.5
        })
        queued_id = queue_res.json()["id"]
        self.assertEqual(queue_res.json()["status"], "EN_COLA_COCINA")

        # Cancelar el primer pedido activo
        target_to_cancel = active_ids[0]
        cancel_res = self.client.post(f"/api/v1/orders/{target_to_cancel}/cancel", json={
            "reason": "CUSTOMER_IMPATIENCE"
        })
        self.assertEqual(cancel_res.status_code, 200)
        self.assertEqual(cancel_res.json()["status"], "CANCELADO_POR_CLIENTE")

        # Verificar que el pedido en cola fue promovido automáticamente a EN_PREPARACION
        db = self.get_db()
        promoted = db.query(OrderModel).filter(OrderModel.id == queued_id).first()
        self.assertEqual(promoted.status, "EN_PREPARACION")
        self.assertIsNotNone(promoted.t_inicio_cocina)
        db.close()

    def test_cancel_order_negative_already_delivered_or_not_found(self):
        """Camino negativo E3: Orden inexistente o en estado final no cancelable."""
        # 404 en orden inexistente
        res_404 = self.client.post("/api/v1/orders/999999/cancel", json={"reason": "TIMEOUT"})
        self.assertEqual(res_404.status_code, 404)

        # Crear y marcar entregada
        db = self.get_db()
        delivered_order = OrderModel(
            customer_id="CUST-ALREADY-DONE",
            restaurant_id=1,
            delivery_coord_x=2.0,
            delivery_coord_y=2.0,
            status="ENTREGADO"
        )
        db.add(delivered_order)
        db.commit()
        db.refresh(delivered_order)
        delivered_id = delivered_order.id
        db.close()

        # Intentar cancelar orden ENTREGADO -> 400 Bad Request
        res_400 = self.client.post(f"/api/v1/orders/{delivered_id}/cancel", json={"reason": "IMPATIENCE"})
        self.assertEqual(res_400.status_code, 400)
        self.assertIn("no puede cancelarse", res_400.json()["detail"])


if __name__ == "__main__":
    unittest.main()
