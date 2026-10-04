import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import uuid
import unittest
from tests.base import TestQuickDeliveryAPIBase
from sistema_real.app.models import CourierModel, TrackingRecordModel


class TestCourierLifecycleAndDispatch(TestQuickDeliveryAPIBase):
    """Pruebas completas del ciclo de vida del repartidor (E6 a E11), filtros de batería y asignación atómica."""

    def test_courier_login_positive(self):
        """Camino positivo E6: Registro e inicio de turno de repartidor (NHPP)."""
        payload = {
            "name": f"Courier-Test-{uuid.uuid4().hex[:4]}",
            "initial_coord_x": 2.5,
            "initial_coord_y": 3.5,
            "battery_level": 98.0
        }
        res = self.client.post("/api/v1/couriers/login", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertIn("courier_id", data)
        self.assertEqual(data["battery_level"], 98.0)
        self.assertIn("shift_start_time", data)

    def test_courier_login_negative_invalid_coordinates(self):
        """Camino negativo E6: Coordenadas iniciales fuera de rango [0.0, 6.0]."""
        payload = {
            "name": "Courier-Fail",
            "initial_coord_x": 7.0,
            "initial_coord_y": 2.0,
            "battery_level": 95.0
        }
        res = self.client.post("/api/v1/couriers/login", json=payload)
        self.assertEqual(res.status_code, 422)

    def test_courier_location_update_positive(self):
        """Camino positivo E7: Envío de telemetría periódica GPS y registro en BD."""
        courier = self.create_courier(name="Courier-GPS", x=1.0, y=1.0, battery=90.0)
        c_id = courier.id

        update_payload = {"coord_x": 1.8, "coord_y": 2.2, "battery_level": 89.5}
        res = self.client.post(f"/api/v1/couriers/{c_id}/location", json=update_payload)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "updated")

        # Verificar persistencia en base de datos
        db = self.get_db()
        rec = db.query(TrackingRecordModel).filter(TrackingRecordModel.courier_id == c_id).first()
        self.assertIsNotNone(rec)
        self.assertEqual(rec.coord_x, 1.8)
        self.assertEqual(rec.battery_level, 89.5)
        db.close()

    def test_courier_location_update_negative_not_found_or_inactive(self):
        """Camino negativo E7: Courier inexistente o inactivo tras logout."""
        # Courier inexistente
        res1 = self.client.post("/api/v1/couriers/999999/location", json={"coord_x": 2.0, "coord_y": 2.0, "battery_level": 80.0})
        self.assertEqual(res1.status_code, 404)

        # Courier inactivo
        inactive_courier = self.create_courier(name="Courier-Dead", x=2.0, y=2.0, is_active=False)
        dead_id = inactive_courier.id

        res2 = self.client.post(f"/api/v1/couriers/{dead_id}/location", json={"coord_x": 2.0, "coord_y": 2.0, "battery_level": 80.0})
        self.assertEqual(res2.status_code, 404)

    def test_courier_offers_positive_and_bonus_calculation(self):
        """Camino positivo E8: Ofertas JIT con cinemática vial y bono urgente (+20%) para comanda lista."""
        courier = self.create_courier(name="Courier-Offers", x=1.5, y=2.0, battery=90.0)
        c_id = courier.id

        # Crear y marcar lista una comanda en restaurante 1
        ord_res = self.client.post("/api/v1/orders/", json={
            "customer_id": f"CUST-OFFER-{uuid.uuid4().hex[:4]}",
            "restaurant_id": 1,
            "delivery_coord_x": 3.0,
            "delivery_coord_y": 3.0
        })
        ord_id = ord_res.json()["id"]
        self.client.post(f"/api/v1/orders/{ord_id}/ready")

        offers_res = self.client.get(f"/api/v1/couriers/{c_id}/offers")
        self.assertEqual(offers_res.status_code, 200)
        offers = offers_res.json()
        self.assertGreater(len(offers), 0)

        found_offer = next((o for o in offers if o["order_id"] == ord_id), None)
        self.assertIsNotNone(found_offer)
        self.assertTrue(found_offer["is_urgent"])
        self.assertGreater(found_offer["tarifa_propuesta"], 2.50)
        self.assertEqual(found_offer["segundos_restantes_oferta"], 45.0)

    def test_courier_offers_negative_low_battery_exclusion(self):
        """Camino negativo E8: Repartidor con batería crítica (< 15%) queda excluido de ofertas (D-08)."""
        low_bat_courier = self.create_courier(name="Courier-LowBat", x=1.0, y=1.0, battery=14.0)
        c_id = low_bat_courier.id

        offers_res = self.client.get(f"/api/v1/couriers/{c_id}/offers")
        self.assertEqual(offers_res.status_code, 200)
        self.assertEqual(offers_res.json(), [])

    def test_accept_order_atomic_positive_and_negative_race_condition(self):
        """Camino positivo y negativo E9: Asignación atómica y resolución de carreras concurrentes (409 Conflict)."""
        c1 = self.create_courier(name="Courier-Racer-1", x=2.0, y=2.0, battery=80.0)
        c2 = self.create_courier(name="Courier-Racer-2", x=2.0, y=2.0, battery=80.0)
        c1_id, c2_id = c1.id, c2.id

        order_res = self.client.post("/api/v1/orders/", json={
            "customer_id": f"CUST-RACE-{uuid.uuid4().hex[:4]}",
            "restaurant_id": 4,
            "delivery_coord_x": 4.0,
            "delivery_coord_y": 4.0
        })
        order_id = order_res.json()["id"]

        # Primer repartidor acepta -> Éxito 200
        accept1 = self.client.post(f"/api/v1/orders/{order_id}/accept", json={"courier_id": c1_id})
        self.assertEqual(accept1.status_code, 200)
        self.assertEqual(accept1.json()["status"], "ASIGNADO")
        self.assertEqual(accept1.json()["courier_id"], c1_id)

        # Segundo repartidor intenta aceptar la misma orden -> 409 Conflict
        accept2 = self.client.post(f"/api/v1/orders/{order_id}/accept", json={"courier_id": c2_id})
        self.assertEqual(accept2.status_code, 409)
        self.assertIn("ya fue asignada", accept2.json()["detail"])

    def test_accept_order_negative_unavailable_courier(self):
        """Camino negativo E9: Courier ocupado o inactivo no puede aceptar órdenes."""
        busy_courier = self.create_courier(name="Courier-Busy", x=2.0, y=2.0, is_available=False)
        busy_id = busy_courier.id

        ord_res = self.client.post("/api/v1/orders/", json={
            "customer_id": "CUST-BUSY-TEST",
            "restaurant_id": 5,
            "delivery_coord_x": 3.0,
            "delivery_coord_y": 3.0
        })
        ord_id = ord_res.json()["id"]

        res = self.client.post(f"/api/v1/orders/{ord_id}/accept", json={"courier_id": busy_id})
        self.assertEqual(res.status_code, 400)
        self.assertIn("no está disponible", res.json()["detail"])

    def test_order_status_transitions_positive_full_cycle(self):
        """Camino positivo E10: Transición completa de hitos (LlegadaARestaurante -> EN_TRANSITO_CLIENTE -> ENTREGADO)."""
        courier = self.create_courier(name="Courier-Milestones", x=2.0, y=2.0, battery=90.0)
        c_id = courier.id

        order_res = self.client.post("/api/v1/orders/", json={
            "customer_id": f"CUST-CYCLE-{uuid.uuid4().hex[:4]}",
            "restaurant_id": 1,
            "delivery_coord_x": 3.0,
            "delivery_coord_y": 3.0
        })
        ord_id = order_res.json()["id"]
        self.client.post(f"/api/v1/orders/{ord_id}/ready")
        self.client.post(f"/api/v1/orders/{ord_id}/accept", json={"courier_id": c_id})

        # Hito 1: LlegadaARestaurante
        h1 = self.client.patch(f"/api/v1/orders/{ord_id}/status", json={
            "courier_id": c_id,
            "new_status": "LlegadaARestaurante",
            "current_coord_x": 1.5,
            "current_coord_y": 2.0
        })
        self.assertEqual(h1.status_code, 200)

        # Hito 2: EN_TRANSITO_CLIENTE (Recogida física)
        h2 = self.client.patch(f"/api/v1/orders/{ord_id}/status", json={
            "courier_id": c_id,
            "new_status": "EN_TRANSITO_CLIENTE",
            "current_coord_x": 1.5,
            "current_coord_y": 2.0
        })
        self.assertEqual(h2.status_code, 200)
        self.assertEqual(h2.json()["status"], "EN_TRANSITO_CLIENTE")
        self.assertIsNotNone(h2.json()["t_recogida"])

        # Hito 3: ENTREGADO (Culminación exitosa)
        h3 = self.client.patch(f"/api/v1/orders/{ord_id}/status", json={
            "courier_id": c_id,
            "new_status": "ENTREGADO",
            "current_coord_x": 3.0,
            "current_coord_y": 3.0
        })
        self.assertEqual(h3.status_code, 200)
        self.assertEqual(h3.json()["status"], "ENTREGADO")
        self.assertIsNotNone(h3.json()["t_entregado"])

        # Verificar que el repartidor quedó libre nuevamente
        db = self.get_db()
        c_check = db.query(CourierModel).filter(CourierModel.id == c_id).first()
        self.assertTrue(c_check.is_available)
        db.close()

    def test_order_status_transitions_negative_unauthorized_and_invalid(self):
        """Camino negativo E10: Repartidor no asignado (403) y estado inventado (400)."""
        c_legit = self.create_courier(name="Courier-Legit", x=2.0, y=2.0)
        c_intruder = self.create_courier(name="Courier-Intruder", x=2.0, y=2.0)
        legit_id, intruder_id = c_legit.id, c_intruder.id

        order_res = self.client.post("/api/v1/orders/", json={
            "customer_id": "CUST-SECURITY-TEST",
            "restaurant_id": 1,
            "delivery_coord_x": 2.5,
            "delivery_coord_y": 2.5
        })
        ord_id = order_res.json()["id"]
        self.client.post(f"/api/v1/orders/{ord_id}/accept", json={"courier_id": legit_id})

        # Repartidor no autorizado intenta cambiar el estado -> 403 Forbidden
        res_403 = self.client.patch(f"/api/v1/orders/{ord_id}/status", json={
            "courier_id": intruder_id,
            "new_status": "EN_TRANSITO_CLIENTE"
        })
        self.assertEqual(res_403.status_code, 403)

        # Estado no válido -> 400 Bad Request
        res_400 = self.client.patch(f"/api/v1/orders/{ord_id}/status", json={
            "courier_id": legit_id,
            "new_status": "ESTADO_INVENTADO"
        })
        self.assertEqual(res_400.status_code, 400)

    def test_courier_logout_positive_and_negative(self):
        """Camino positivo y negativo E11: Cierre formal de turno y manejo de 404."""
        courier = self.create_courier(name="Courier-ToLogout", x=2.0, y=2.0)
        c_id = courier.id

        # Logout exitoso
        res = self.client.post(f"/api/v1/couriers/{c_id}/logout")
        self.assertEqual(res.status_code, 200)

        db = self.get_db()
        c_after = db.query(CourierModel).filter(CourierModel.id == c_id).first()
        self.assertFalse(c_after.is_active)
        self.assertFalse(c_after.is_available)
        db.close()

        # Logout inexistente -> 404
        res_404 = self.client.post("/api/v1/couriers/999999/logout")
        self.assertEqual(res_404.status_code, 404)


if __name__ == "__main__":
    unittest.main()
