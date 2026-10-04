import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import uuid
import unittest
from tests.base import TestQuickDeliveryAPIBase
from sistema_real.app.models import CourierModel


class TestEndToEndCompleteFlows(TestQuickDeliveryAPIBase):
    """
    Pruebas integrales de flujo completo (End-to-End) que abarcan
    la interacción coordinada de los 3 actores: Cliente, Restaurante (KDS) y Repartidor.
    """

    def test_end_to_end_successful_delivery_lifecycle(self):
        """Flujo E2E positivo completo: Creación -> Fin Cocina -> Oferta -> Aceptación -> Tracking -> Arribo -> Recogida -> Entrega."""
        uid = uuid.uuid4().hex[:6]

        # 1. Login de Repartidor
        login_res = self.client.post("/api/v1/couriers/login", json={
            "name": f"Courier-E2E-{uid}",
            "initial_coord_x": 1.0,
            "initial_coord_y": 1.0,
            "battery_level": 96.0
        })
        self.assertEqual(login_res.status_code, 201)
        courier_id = login_res.json()["courier_id"]

        # 2. Cliente realiza Pedido
        order_res = self.client.post("/api/v1/orders/", json={
            "customer_id": f"CUST-E2E-{uid}",
            "restaurant_id": 1,
            "delivery_coord_x": 3.0,
            "delivery_coord_y": 3.0
        })
        self.assertEqual(order_res.status_code, 201)
        order_id = order_res.json()["id"]

        # 3. KDS Restaurante marca pedido listo en mostrador
        ready_res = self.client.post(f"/api/v1/orders/{order_id}/ready")
        self.assertEqual(ready_res.status_code, 200)
        self.assertEqual(ready_res.json()["status"], "LISTO_EN_MOSTRADOR")

        # 4. Repartidor consulta ofertas JIT
        offers_res = self.client.get(f"/api/v1/couriers/{courier_id}/offers")
        self.assertEqual(offers_res.status_code, 200)
        offers = offers_res.json()
        target_offer = next((o for o in offers if o["order_id"] == order_id), None)
        self.assertIsNotNone(target_offer)

        # 5. Repartidor acepta la orden
        accept_res = self.client.post(f"/api/v1/orders/{order_id}/accept", json={"courier_id": courier_id})
        self.assertEqual(accept_res.status_code, 200)
        self.assertEqual(accept_res.json()["status"], "ASIGNADO")

        # 6. Cliente consulta rastreo GPS
        trk_res = self.client.get(f"/api/v1/orders/{order_id}/tracking")
        self.assertEqual(trk_res.status_code, 200)
        self.assertEqual(trk_res.json()["status"], "ASIGNADO")
        self.assertEqual(trk_res.json()["courier_id"], courier_id)
        self.assertIsNotNone(trk_res.json()["distancia_vial_restante_km"])

        # 7. Repartidor arriba al restaurante
        arr_res = self.client.patch(f"/api/v1/orders/{order_id}/status", json={
            "courier_id": courier_id,
            "new_status": "LlegadaARestaurante",
            "current_coord_x": 1.5,
            "current_coord_y": 2.0
        })
        self.assertEqual(arr_res.status_code, 200)

        # 8. Repartidor retira el pedido (pasa a tránsito al cliente)
        pickup_res = self.client.patch(f"/api/v1/orders/{order_id}/status", json={
            "courier_id": courier_id,
            "new_status": "EN_TRANSITO_CLIENTE",
            "current_coord_x": 1.5,
            "current_coord_y": 2.0
        })
        self.assertEqual(pickup_res.status_code, 200)
        self.assertEqual(pickup_res.json()["status"], "EN_TRANSITO_CLIENTE")
        self.assertIsNotNone(pickup_res.json()["t_recogida"])

        # 9. Repartidor entrega al cliente en destino
        deliv_res = self.client.patch(f"/api/v1/orders/{order_id}/status", json={
            "courier_id": courier_id,
            "new_status": "ENTREGADO",
            "current_coord_x": 3.0,
            "current_coord_y": 3.0
        })
        self.assertEqual(deliv_res.status_code, 200)
        self.assertEqual(deliv_res.json()["status"], "ENTREGADO")
        self.assertIsNotNone(deliv_res.json()["t_entregado"])

        # 10. Verificar que el repartidor está libre y disponible
        db = self.get_db()
        c_status = db.query(CourierModel).filter(CourierModel.id == courier_id).first()
        self.assertTrue(c_status.is_available)
        self.assertTrue(c_status.is_active)
        db.close()

    def test_end_to_end_transit_incident_lifecycle(self):
        """Flujo E2E de Contingencia: Accidente o siniestro en ruta (CANCELADO_INCIDENCIA_TRANSITO) libera al courier."""
        uid = uuid.uuid4().hex[:6]

        # Login courier
        c_res = self.client.post("/api/v1/couriers/login", json={
            "name": f"Courier-Inc-{uid}",
            "initial_coord_x": 2.0,
            "initial_coord_y": 2.0,
            "battery_level": 90.0
        })
        c_id = c_res.json()["courier_id"]

        # Crear orden y aceptar
        ord_res = self.client.post("/api/v1/orders/", json={
            "customer_id": f"CUST-INC-{uid}",
            "restaurant_id": 1,
            "delivery_coord_x": 3.0,
            "delivery_coord_y": 3.0
        })
        ord_id = ord_res.json()["id"]
        self.client.post(f"/api/v1/orders/{ord_id}/ready")
        self.client.post(f"/api/v1/orders/{ord_id}/accept", json={"courier_id": c_id})

        # Notificar incidencia en tránsito
        inc_res = self.client.patch(f"/api/v1/orders/{ord_id}/status", json={
            "courier_id": c_id,
            "new_status": "CANCELADO_INCIDENCIA_TRANSITO",
            "current_coord_x": 2.5,
            "current_coord_y": 2.5
        })
        self.assertEqual(inc_res.status_code, 200)
        self.assertEqual(inc_res.json()["status"], "CANCELADO_INCIDENCIA_TRANSITO")

        # Verificar que el repartidor vuelve a quedar disponible
        db = self.get_db()
        c_post = db.query(CourierModel).filter(CourierModel.id == c_id).first()
        self.assertTrue(c_post.is_available)
        db.close()

    def test_end_to_end_customer_cancel_frees_assigned_courier(self):
        """Flujo E2E: Cancelación del cliente cuando la orden ya estaba asignada libera al repartidor."""
        uid = uuid.uuid4().hex[:6]

        c_res = self.client.post("/api/v1/couriers/login", json={
            "name": f"Courier-FreeMe-{uid}",
            "initial_coord_x": 2.0,
            "initial_coord_y": 2.0,
            "battery_level": 85.0
        })
        c_id = c_res.json()["courier_id"]

        ord_res = self.client.post("/api/v1/orders/", json={
            "customer_id": f"CUST-CANCEL-ME-{uid}",
            "restaurant_id": 1,
            "delivery_coord_x": 3.0,
            "delivery_coord_y": 3.0
        })
        ord_id = ord_res.json()["id"]
        self.client.post(f"/api/v1/orders/{ord_id}/ready")
        self.client.post(f"/api/v1/orders/{ord_id}/accept", json={"courier_id": c_id})

        # Verificar que el courier está ocupado
        db = self.get_db()
        c_mid = db.query(CourierModel).filter(CourierModel.id == c_id).first()
        self.assertFalse(c_mid.is_available)
        db.close()

        # El cliente cancela la orden
        cancel_res = self.client.post(f"/api/v1/orders/{ord_id}/cancel", json={
            "reason": "TOO_SLOW"
        })
        self.assertEqual(cancel_res.status_code, 200)
        self.assertEqual(cancel_res.json()["status"], "CANCELADO_POR_CLIENTE")

        # Verificar que el courier quedó liberado automáticamente
        db = self.get_db()
        c_after = db.query(CourierModel).filter(CourierModel.id == c_id).first()
        self.assertTrue(c_after.is_available)
        db.close()


if __name__ == "__main__":
    unittest.main()
