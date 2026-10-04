import os
import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import unittest
from tests.base import TestQuickDeliveryAPIBase
from sistema_real.map_renderer import render_cartesian_map, km_to_px
from sistema_real.api_client import DeliveryApiClient


class TestDashboardIntegration(TestQuickDeliveryAPIBase):
    """Pruebas de endpoints para el Dashboard y del Renderizador del Plano 2D."""

    def test_list_restaurants_endpoint(self):
        """Verifica que el endpoint GET /api/v1/restaurants/ devuelva los 10 locales del modelo."""
        res = self.client.get("/api/v1/restaurants/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(len(data), 10)
        self.assertIn("kitchen_capacity", data[0])
        self.assertIn("coord_x", data[0])
        self.assertIn("coord_y", data[0])

    def test_list_couriers_endpoint(self):
        """Verifica que el endpoint GET /api/v1/couriers/ devuelva la flota con GPS y batería."""
        res = self.client.get("/api/v1/couriers/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(len(data), 1)
        self.assertIn("battery_level", data[0])
        self.assertIn("current_coord_x", data[0])

    def test_orders_summary_stats_endpoint(self):
        """Verifica el cálculo de KPIs (totales, en curso, completadas, canceladas) para el pie chart."""
        res = self.client.get("/api/v1/orders/summary/stats")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("total_orders", data)
        self.assertIn("orders_in_progress", data)
        self.assertIn("orders_completed", data)
        self.assertIn("orders_cancelled", data)
        self.assertIn("connected_couriers", data)

    def test_map_renderer_without_selection(self):
        """El plano SVG renderiza todos los elementos con opacidad normal cuando no hay orden seleccionada."""
        restaurants = [{"id": 1, "coord_x": 2.0, "coord_y": 3.0, "name": "R1", "kitchen_capacity": 4}]
        couriers = [{"id": 1, "current_coord_x": 1.0, "current_coord_y": 1.0, "name": "C1", "battery_level": 90.0, "is_available": True, "is_active": True}]
        orders = [{"id": 10, "restaurant_id": 1, "delivery_coord_x": 4.0, "delivery_coord_y": 4.0, "customer_id": "CUST-1", "status": "EN_PREPARACION"}]

        svg = render_cartesian_map(restaurants, couriers, orders, selected_order_id=None)
        self.assertIn("viewBox=\"0 0 680 680\"", svg)
        self.assertIn("opacity=\"0.95\"", svg)
        self.assertIn("opacity=\"0.9\"", svg)

    def test_map_renderer_with_selection_adjusts_transparency(self):
        """El plano SVG reduce la opacidad a 0.15 para elementos ajenos y resalta los del pedido seleccionado."""
        restaurants = [
            {"id": 1, "coord_x": 2.0, "coord_y": 3.0, "name": "R1", "kitchen_capacity": 4},
            {"id": 2, "coord_x": 5.0, "coord_y": 5.0, "name": "R2", "kitchen_capacity": 3}
        ]
        couriers = [
            {"id": 1, "current_coord_x": 1.0, "current_coord_y": 1.0, "name": "C1", "battery_level": 90.0, "is_available": True, "is_active": True},
            {"id": 2, "current_coord_x": 4.5, "current_coord_y": 4.5, "name": "C2", "battery_level": 85.0, "is_available": True, "is_active": True}
        ]
        orders = [
            {"id": 10, "restaurant_id": 1, "delivery_coord_x": 4.0, "delivery_coord_y": 4.0, "courier_id": 1, "customer_id": "CUST-1", "status": "EN_TRANSITO_CLIENTE"},
            {"id": 11, "restaurant_id": 2, "delivery_coord_x": 1.0, "delivery_coord_y": 5.0, "courier_id": 2, "customer_id": "CUST-2", "status": "EN_PREPARACION"}
        ]

        svg = render_cartesian_map(restaurants, couriers, orders, selected_order_id=10)
        # Elementos no relacionados deben tener opacidad 0.15
        self.assertIn("opacity=\"0.15\"", svg)
        # Elementos seleccionados deben tener opacidad 1.0
        self.assertIn("opacity=\"1.0\"", svg)
        # Debe haber trazado de línea de trayectoria
        self.assertIn("<line ", svg)

    def test_km_to_px_bounds(self):
        """Verifica la conversión de límites de coordenadas [0, 6] km a píxeles SVG."""
        px_0, py_0 = km_to_px(0.0, 0.0)
        px_6, py_6 = km_to_px(6.0, 6.0)
        self.assertEqual(px_0, 55.0)
        self.assertEqual(py_0, 625.0)
        self.assertEqual(px_6, 635.0)
        self.assertEqual(py_6, 45.0)

    def test_map_renderer_with_layer_toggles(self):
        """Verifica que el filtrado por capas booleanas oculte o muestre únicamente los elementos seleccionados."""
        restaurants = [{"id": 1, "coord_x": 2.0, "coord_y": 3.0, "name": "Burger Station", "kitchen_capacity": 4}]
        couriers = [
            {"id": 1, "current_coord_x": 1.0, "current_coord_y": 1.0, "name": "C-Free", "battery_level": 90.0, "is_available": True, "is_active": True},
            {"id": 2, "current_coord_x": 4.5, "current_coord_y": 4.5, "name": "C-Busy", "battery_level": 85.0, "is_available": False, "is_active": True}
        ]
        orders = [{"id": 10, "restaurant_id": 1, "delivery_coord_x": 4.0, "delivery_coord_y": 4.0, "courier_id": 2, "customer_id": "CUST-99", "status": "EN_TRANSITO_CLIENTE"}]
        preview = (3.5, 3.5)

        # 1. Capa de restaurantes desactivada
        svg_no_rest = render_cartesian_map(restaurants, couriers, orders, preview_point=preview, layers={"restaurants": False, "customers": True, "couriers_free": True, "couriers_busy": True, "preview": True})
        self.assertNotIn("Burger Stati", svg_no_rest)
        self.assertIn("CUST-99", svg_no_rest)

        # 2. Solo 3 capas activas: Restaurantes, Clientes y Punto de Clic (Couriers apagados)
        svg_three_layers = render_cartesian_map(
            restaurants, couriers, orders, preview_point=preview,
            layers={"restaurants": True, "customers": True, "couriers_free": False, "couriers_busy": False, "preview": True}
        )
        self.assertIn("Burger Stati", svg_three_layers)
        self.assertIn("CUST-99", svg_three_layers)
        self.assertIn("Nuevo (3.50, 3.50)", svg_three_layers)
        self.assertNotIn("C-Free", svg_three_layers)
        self.assertNotIn("C-Busy", svg_three_layers)


if __name__ == "__main__":
    unittest.main()
