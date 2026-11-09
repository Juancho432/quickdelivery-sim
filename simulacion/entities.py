import simpy
import numpy as np
import math
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict, Any

RESTAURANTS_DEFAULT_CONFIG: List[Dict[str, Any]] = [
    {"id": 0, "db_id": 1, "name": "Burger Station Chapinero", "coords": (1.5, 2.0), "capacity": 5},
    {"id": 1, "db_id": 2, "name": "Pizzeria Napolitana Zona T", "coords": (2.8, 1.2), "capacity": 4},
    {"id": 2, "db_id": 3, "name": "Wok Express Salitre", "coords": (2.0, 2.0), "capacity": 4},
    {"id": 3, "db_id": 4, "name": "Tacos El Guero Galerias", "coords": (4.5, 3.2), "capacity": 6},
    {"id": 4, "db_id": 5, "name": "Sushi Master Usaquen", "coords": (3.2, 4.8), "capacity": 5},
    {"id": 5, "db_id": 6, "name": "Pollo Criollo Centro", "coords": (1.0, 4.0), "capacity": 6},
    {"id": 6, "db_id": 7, "name": "Arepas & Empanadas Teusaquillo", "coords": (4.0, 1.5), "capacity": 4},
    {"id": 7, "db_id": 8, "name": "Green Salad & Bowls Chicó", "coords": (5.2, 5.0), "capacity": 3},
    {"id": 8, "db_id": 9, "name": "Pastas & Risottos Parkway", "coords": (2.5, 3.5), "capacity": 5},
    {"id": 9, "db_id": 10, "name": "Parrilla Urbana Cedritos", "coords": (3.8, 2.7), "capacity": 5},
]


def get_vial_distance(x1: float, y1: float, x2: float, y2: float, tau: float = 1.25) -> float:
    """Calcula la distancia vial aplicando la métrica Manhattan corregida por factor de sinuosidad tau=1.25."""
    dist_manhattan = abs(x2 - x1) + abs(y2 - y1)
    return tau * dist_manhattan


def get_kinematic_travel_time(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    deterministic: bool = False,
    rng: Optional[np.random.Generator] = None,
) -> float:
    """
    Calcula el tiempo de viaje en minutos considerando sinuosidad urbana tau=1.25
    y velocidad Normal Truncada [8, 25] km/h con media 18 km/h y desvío 3 km/h.
    Si deterministic=True, emplea la velocidad media de 18.0 km/h (para estimación de ETA).
    """
    d_vial = get_vial_distance(x1, y1, x2, y2, tau=1.25)
    if d_vial <= 0.0:
        return 0.0

    if deterministic:
        v_rep = 18.0
    else:
        v_rep = -1.0
        while not (8.0 <= v_rep <= 25.0):
            if rng is not None:
                v_rep = float(rng.normal(18.0, 3.0))
            else:
                v_rep = float(np.random.normal(18.0, 3.0))

    # Tiempo en minutos = (Distancia (km) / Velocidad (km/h)) * 60
    return (d_vial / v_rep) * 60.0


@dataclass
class Order:
    id: int
    rest_id: int
    t_creacion: float
    coords_cliente: Tuple[float, float]
    coords_restaurante: Tuple[float, float] = (3.0, 3.0)
    estado: str = "CREADO"
    t_inicio_cocina: Optional[float] = None
    t_cocina_est: float = 18.5
    t_ready_est: float = 0.0
    t_despacho_prog: float = 0.0
    t_listo: Optional[float] = None
    t_asignado: Optional[float] = None
    t_arribo_rep: Optional[float] = None
    t_recogida: Optional[float] = None
    t_entregado: Optional[float] = None
    paciencia_max: float = 40.0
    courier_id: Optional[int] = None
    es_urgente: bool = False
    reintentos: int = 0
    motivo_cancelacion: Optional[str] = None

    @property
    def distancia_vial_km(self) -> float:
        return get_vial_distance(
            self.coords_restaurante[0],
            self.coords_restaurante[1],
            self.coords_cliente[0],
            self.coords_cliente[1],
        )


class Courier:
    def __init__(
        self,
        env: simpy.Environment,
        c_id: int,
        coords: Optional[Tuple[float, float]] = None,
        bateria_inicial: Optional[float] = None,
        max_shift_min: float = 360.0,
    ):
        self.env = env
        self.id = c_id
        self.estado = "LIBRE"
        self.coords: Tuple[float, float] = (
            coords if coords is not None else (float(np.random.uniform(0.0, 6.0)), float(np.random.uniform(0.0, 6.0)))
        )
        # Batería inicial estocástica N(95, 5) truncada [70, 100]
        if bateria_inicial is not None:
            self.bateria = float(min(100.0, max(70.0, bateria_inicial)))
        else:
            self.bateria = float(min(100.0, max(70.0, np.random.normal(95.0, 5.0))))
        self.t_login = float(env.now)
        self.max_shift_min = max_shift_min
        self.pedido_actual: Optional[Order] = None
        self.pedidos_completados: int = 0
        self.tiempo_en_servicio: float = 0.0
        self.tiempo_espera_rest: float = 0.0

    @property
    def tiempo_activo(self) -> float:
        return float(self.env.now - self.t_login)

    def is_shift_expired(self, now: Optional[float] = None) -> bool:
        t_now = float(self.env.now if now is None else now)
        return (t_now - self.t_login) >= self.max_shift_min

    def check_battery_for_trip(
        self,
        t_viaje_local: float,
        t_espera: float,
        t_viaje_cliente: float,
        min_reserve_pct: float = 15.0,
    ) -> bool:
        """Filtro preventivo de batería: reserva >= 15% al terminar el servicio proyectado."""
        consumo_proyectado = (t_viaje_local + t_viaje_cliente) * 0.15 + (t_espera * 0.05)
        return (self.bateria - consumo_proyectado) >= min_reserve_pct

    def consume_battery(self, mins_en_movimiento: float = 0.0, mins_en_reposo: float = 0.0):
        drenaje = (mins_en_movimiento * 0.15) + (mins_en_reposo * 0.05)
        self.bateria = max(0.0, self.bateria - drenaje)

    def evaluate_post_delivery(self, min_reserve_pct: float = 15.0) -> bool:
        """
        Evalúa al finalizar una entrega si el repartidor puede seguir conectado (True)
        o debe ejecutar LogoutRepartidor por política de turno de 6h o batería baja (False).
        """
        self.pedido_actual = None
        if self.is_shift_expired() or self.bateria < min_reserve_pct:
            self.estado = "DESCONECTADO"
            return False
        self.estado = "LIBRE"
        return True


class CourierPool:
    """
    Pool de repartidores activos del sistema. Gestiona el alta/baja de conductores,
    las consultas de disponibilidad y el cálculo de utilización de la flota.
    """
    def __init__(self, env: simpy.Environment):
        self.env = env
        self.couriers: List[Courier] = []
        self._next_id: int = 1
        # Evento despertador cuando un repartidor queda libre o ingresa al pool
        self.courier_available_event = env.event()

    def add_courier(
        self,
        coords: Optional[Tuple[float, float]] = None,
        bateria_inicial: Optional[float] = None,
    ) -> Courier:
        c = Courier(self.env, self._next_id, coords=coords, bateria_inicial=bateria_inicial)
        self._next_id += 1
        self.couriers.append(c)
        self.notify_availability()
        return c

    def notify_availability(self):
        """Despierta procesos que esperan un repartidor libre en el pool."""
        if not self.courier_available_event.triggered:
            self.courier_available_event.succeed()
        self.courier_available_event = self.env.event()

    def purge_expired_idle_couriers(self, min_reserve_pct: float = 15.0) -> int:
        """Desconecta repartidores libres que hayan cumplido 6h de turno o tengan batería < 15%."""
        desconectados = 0
        for c in self.couriers:
            if c.estado == "LIBRE":
                if c.is_shift_expired() or c.bateria < min_reserve_pct:
                    c.estado = "DESCONECTADO"
                    desconectados += 1
        return desconectados

    @property
    def connected_couriers(self) -> List[Courier]:
        return [c for c in self.couriers if c.estado != "DESCONECTADO"]

    @property
    def available_couriers(self) -> List[Courier]:
        self.purge_expired_idle_couriers()
        return [c for c in self.couriers if c.estado == "LIBRE"]

    @property
    def busy_couriers(self) -> List[Courier]:
        return [c for c in self.couriers if c.estado not in ("LIBRE", "DESCONECTADO")]

    def get_utilization_pct(self) -> float:
        conectados = self.connected_couriers
        if not conectados:
            return 0.0
        ocupados = sum(1 for c in conectados if c.estado != "LIBRE")
        return (ocupados / len(conectados)) * 100.0


class KitchenNetwork:
    """Red de 10 restaurantes con 47 fogones totales instalados (capacidad fija medible C6)."""
    def __init__(self, env: simpy.Environment):
        self.env = env
        self.restaurantes: List[Dict[str, Any]] = []
        for r_cfg in RESTAURANTS_DEFAULT_CONFIG:
            fogon = simpy.Resource(env, capacity=r_cfg["capacity"])
            self.restaurantes.append({
                "id": r_cfg["id"],
                "db_id": r_cfg["db_id"],
                "name": r_cfg["name"],
                "coords": r_cfg["coords"],
                "capacity": r_cfg["capacity"],
                "fogones": fogon,
            })

    @property
    def total_stoves(self) -> int:
        return sum(r["capacity"] for r in self.restaurantes)

    def estimate_ready_time(self, rest_id: int, t_actual: float, t_cocina_propio: float = 18.5) -> float:
        """
        Calcula el ETA_listo considerando la cola actual frente a los fogones del restaurante r:
        ETA_listo = t_actual + (Q_cocina_r / k_r) * T_cocina_medio + T_cocina_propio
        """
        rest = self.restaurantes[rest_id]
        fogon_res: simpy.Resource = rest["fogones"]
        k_r = rest["capacity"]
        q_len = len(fogon_res.queue)
        ocupados = fogon_res.count
        espera_cola_est = ((q_len + (1 if ocupados >= k_r else 0)) / k_r) * 18.5 if ocupados >= k_r else 0.0
        return t_actual + espera_cola_est + t_cocina_propio
