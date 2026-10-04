import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import unittest
from datetime import timedelta
from tests.base import TestQuickDeliveryAPIBase
from sistema_real.app.models import OrderModel, CourierModel, utcnow
from sistema_real.app.config import system_config
from sistema_real.app.dispatch import calculate_vial_distance, calculate_travel_time_min


class TestBusinessLogicAndEdgeCases(TestQuickDeliveryAPIBase):
    """Pruebas de Reglas de Decisión Críticas (D-07 Anti-Limbo, D-08 Flexibilidad y Cinemática tau=1.25)."""

    def test_vial_kinematics_and_sinuosity_factor(self):
        """Validación de Cinemática Vial: Manhattan * 1.25 y velocidad media 18 km/h (D-11 Excl-4)."""
        x1, y1 = 1.0, 1.0
        x2, y2 = 3.0, 4.0
        # Manhattan pura = |3 - 1| + |4 - 1| = 2 + 3 = 5.0 km
        # Con tau = 1.25: 5.0 * 1.25 = 6.25 km
        dist = calculate_vial_distance(x1, y1, x2, y2)
        self.assertEqual(dist, 6.25)

        # Tiempo a 18 km/h: (6.25 / 18) * 60 = 20.83 min
        t_viaje = calculate_travel_time_min(dist, speed_kmh=18.0)
        self.assertEqual(t_viaje, 20.83)

    def test_anti_limbo_timeout_counter_d07(self):
        """Protocolo Anti-Limbo D-07: Cancela comanda si supera anti_limbo_max_counter_min en mostrador."""
        system_config.anti_limbo_max_counter_min = 0.001  # Relajar para simulación inmediata

        db = self.get_db()
        stale_order = OrderModel(
            customer_id="CUST-STALE-LIMBO",
            restaurant_id=1,
            delivery_coord_x=3.0,
            delivery_coord_y=3.0,
            status="LISTO_EN_MOSTRADOR",
            t_listo=utcnow() - timedelta(minutes=25)  # Lleva 25 min en mostrador
        )
        db.add(stale_order)
        db.commit()
        db.refresh(stale_order)
        stale_id = stale_order.id
        db.close()

        # Al consultar tracking, debe disparar check_anti_limbo_timeout y transicionar a CANCELADO_SIN_REPARTIDOR
        trk_res = self.client.get(f"/api/v1/orders/{stale_id}/tracking")
        self.assertEqual(trk_res.status_code, 200)
        self.assertEqual(trk_res.json()["status"], "CANCELADO_SIN_REPARTIDOR")

        # Verificar motivo en BD
        db = self.get_db()
        ord_db = db.query(OrderModel).filter(OrderModel.id == stale_id).first()
        self.assertEqual(ord_db.cancellation_reason, "COUNTER_TIMEOUT_20MIN")
        db.close()

    def test_courier_auto_logout_on_delivery_d08(self):
        """Regla D-08: Al entregar orden, si la batería cayó a < 15% o excedió turno de 6h, ejecuta logout."""
        tired_courier = self.create_courier(
            name="Courier-Tired-D08",
            x=2.0,
            y=2.0,
            battery=12.0,  # Menor a 15%
            is_active=True,
            is_available=True
        )
        c_id = tired_courier.id

        db = self.get_db()
        order = OrderModel(
            customer_id="CUST-TIRED-DELIVERY",
            restaurant_id=1,
            delivery_coord_x=2.5,
            delivery_coord_y=2.5,
            status="EN_TRANSITO_CLIENTE",
            courier_id=c_id
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        ord_id = order.id
        db.close()

        # Finalizar entrega
        res = self.client.patch(f"/api/v1/orders/{ord_id}/status", json={
            "courier_id": c_id,
            "new_status": "ENTREGADO",
            "current_coord_x": 2.5,
            "current_coord_y": 2.5
        })
        self.assertEqual(res.status_code, 200)

        # Verificar que el repartidor fue desconectado automáticamente
        db = self.get_db()
        courier_post = db.query(CourierModel).filter(CourierModel.id == c_id).first()
        self.assertFalse(courier_post.is_active)
        self.assertFalse(courier_post.is_available)
        db.close()


if __name__ == "__main__":
    unittest.main()
