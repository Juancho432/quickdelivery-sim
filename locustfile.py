import random
from locust import HttpUser, task, between, tag


class CustomerUser(HttpUser):
    """Simula el comportamiento del consumidor emitiendo pedidos, rastreando su entrega y cancelando esporádicamente."""
    weight = 5
    wait_time = between(1, 3)

    def on_start(self):
        self.customer_id = f"CUST-{random.randint(1000, 9999)}"
        self.active_order_id = None

    @task(3)
    def create_order(self):
        payload = {
            "customer_id": self.customer_id,
            "restaurant_id": random.randint(1, 10),
            "delivery_coord_x": round(random.uniform(0.5, 5.5), 2),
            "delivery_coord_y": round(random.uniform(0.5, 5.5), 2)
        }
        with self.client.post("/api/v1/orders/", json=payload, catch_response=True) as resp:
            if resp.status_code == 201:
                data = resp.json()
                self.active_order_id = data["id"]
                resp.success()
            else:
                resp.failure(f"Error al crear pedido: {resp.text}")

    @task(5)
    def track_order(self):
        if self.active_order_id:
            with self.client.get(f"/api/v1/orders/{self.active_order_id}/tracking", catch_response=True) as resp:
                if resp.status_code == 200:
                    resp.success()
                else:
                    resp.failure(f"Error en rastreo: {resp.text}")

    @task(1)
    def cancel_order_occasional(self):
        if self.active_order_id:
            payload = {"reason": "CUSTOMER_IMPATIENCE_WEIBULL"}
            with self.client.post(f"/api/v1/orders/{self.active_order_id}/cancel", json=payload, catch_response=True) as resp:
                if resp.status_code in [200, 400]:
                    self.active_order_id = None
                    resp.success()
                else:
                    resp.failure(f"Error en cancelacion: {resp.text}")


class RestaurantUser(HttpUser):
    """Simula la pantalla KDS de la cocina consultando comandas activas y notificando platos listos en mostrador."""
    weight = 2
    wait_time = between(2, 5)

    def on_start(self):
        self.restaurant_id = random.randint(1, 10)
        self.pending_order_id = None

    @task(4)
    def monitor_kds(self):
        with self.client.get(f"/api/v1/restaurants/{self.restaurant_id}/orders", catch_response=True) as resp:
            if resp.status_code == 200:
                orders = resp.json()
                cooking_orders = [o for o in orders if o["status"] == "EN_PREPARACION"]
                if cooking_orders:
                    self.pending_order_id = cooking_orders[0]["order_id"]
                resp.success()
            else:
                resp.failure(f"Error en consulta KDS: {resp.text}")

    @task(2)
    def mark_dish_ready(self):
        if self.pending_order_id:
            with self.client.post(f"/api/v1/orders/{self.pending_order_id}/ready", catch_response=True) as resp:
                if resp.status_code == 200:
                    self.pending_order_id = None
                    resp.success()
                elif resp.status_code == 404:
                    self.pending_order_id = None
                    resp.success()
                else:
                    resp.failure(f"Error en ready: {resp.text}")


class CourierUser(HttpUser):
    """Simula la flota de repartidores: conexión de turno, pings GPS (Pregunta 3), ofertas, aceptación y entrega."""
    weight = 3
    wait_time = between(1, 4)

    def on_start(self):
        self.courier_name = f"Courier-{random.randint(100, 999)}"
        self.courier_id = None
        self.assigned_order_id = None
        self.coord_x = round(random.uniform(1.0, 5.0), 2)
        self.coord_y = round(random.uniform(1.0, 5.0), 2)
        self.battery = round(random.uniform(85.0, 98.0), 1)

        # Login para iniciar turno de 6h
        login_payload = {
            "name": self.courier_name,
            "initial_coord_x": self.coord_x,
            "initial_coord_y": self.coord_y,
            "battery_level": self.battery
        }
        res = self.client.post("/api/v1/couriers/login", json=login_payload)
        if res.status_code == 201:
            self.courier_id = res.json()["courier_id"]

    @tag("ping_gps")
    @task(4)
    def report_location_ping(self):
        """Pings de telemetría GPS para evaluar Pregunta 3 (frecuencia de rastreo vs CPU/latencia)."""
        if self.courier_id:
            self.coord_x = round(min(5.9, max(0.1, self.coord_x + random.uniform(-0.1, 0.1))), 2)
            self.coord_y = round(min(5.9, max(0.1, self.coord_y + random.uniform(-0.1, 0.1))), 2)
            self.battery = max(5.0, self.battery - 0.05)
            payload = {
                "coord_x": self.coord_x,
                "coord_y": self.coord_y,
                "battery_level": round(self.battery, 1)
            }
            self.client.post(f"/api/v1/couriers/{self.courier_id}/location", json=payload)

    @task(4)
    def poll_qualified_offers(self):
        """Sondeo de ofertas calificadas Just-In-Time."""
        if self.courier_id and not self.assigned_order_id:
            with self.client.get(f"/api/v1/couriers/{self.courier_id}/offers", catch_response=True) as resp:
                if resp.status_code == 200:
                    offers = resp.json()
                    if offers:
                        self.candidate_order_id = offers[0]["order_id"]
                    resp.success()
                else:
                    resp.failure(f"Error al consultar ofertas: {resp.text}")

    @task(3)
    def accept_order_competition(self):
        """Compite por aceptar la comanda en ventana de 45 s."""
        if hasattr(self, "candidate_order_id") and self.candidate_order_id and not self.assigned_order_id:
            payload = {"courier_id": self.courier_id}
            with self.client.post(f"/api/v1/orders/{self.candidate_order_id}/accept", json=payload, catch_response=True) as resp:
                if resp.status_code == 200:
                    self.assigned_order_id = self.candidate_order_id
                    self.candidate_order_id = None
                    resp.success()
                elif resp.status_code == 409:
                    # Carrera concurrente ganada por otro repartidor (comportamiento esperado)
                    self.candidate_order_id = None
                    resp.success()
                else:
                    resp.failure(f"Error inesperado al aceptar orden: {resp.text}")

    @task(3)
    def update_delivery_progress(self):
        """Avanza los hitos del pedido: tránsito y entrega final."""
        if self.assigned_order_id and self.courier_id:
            # Hito 1: En tránsito al cliente
            payload_transit = {
                "courier_id": self.courier_id,
                "new_status": "EN_TRANSITO_CLIENTE",
                "current_coord_x": self.coord_x,
                "current_coord_y": self.coord_y
            }
            self.client.patch(f"/api/v1/orders/{self.assigned_order_id}/status", json=payload_transit)

            # Hito 2: Entrega final exitosa
            payload_delivered = {
                "courier_id": self.courier_id,
                "new_status": "ENTREGADO",
                "current_coord_x": self.coord_x,
                "current_coord_y": self.coord_y
            }
            with self.client.patch(f"/api/v1/orders/{self.assigned_order_id}/status", json=payload_delivered, catch_response=True) as resp:
                if resp.status_code == 200:
                    self.assigned_order_id = None
                    resp.success()
                else:
                    resp.failure(f"Error al culminar entrega: {resp.text}")

    @task(1)
    def check_platform_health(self):
        self.client.get("/api/v1/telemetry/health")
