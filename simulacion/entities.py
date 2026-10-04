import simpy
import numpy as np
import math
from dataclasses import dataclass, field
from typing import Optional, List, Tuple

def get_kinematic_travel_time(x1: float, y1: float, x2: float, y2: float) -> float:
    """Calcula tiempo de viaje considerando sinuosidad urbana tau=1.25 y velocidad Normal Truncada."""
    dist_manhattan = abs(x2 - x1) + abs(y2 - y1)
    d_vial = 1.25 * dist_manhattan
    
    # Velocidad Normal Truncada [8, 25] km/h
    v_rep = -1
    while not (8 <= v_rep <= 25):
        v_rep = np.random.normal(18, 3)
    
    # Tiempo en minutos = (Distancia (km) / Velocidad (km/h)) * 60
    return (d_vial / v_rep) * 60.0

@dataclass
class Order:
    id: int
    rest_id: int
    t_creacion: float
    coords_cliente: Tuple[float, float]
    estado: str = "CREADO"
    t_listo: Optional[float] = None
    t_entregado: Optional[float] = None
    
class Courier:
    def __init__(self, env: simpy.Environment, c_id: int):
        self.env = env
        self.id = c_id
        self.estado = "LIBRE"
        self.coords = (np.random.uniform(0, 6), np.random.uniform(0, 6))
        # Batería inicial estocástica N(95, 5) truncada [70, 100]
        self.bateria = min(100.0, max(70.0, np.random.normal(95, 5)))
        self.t_login = env.now
    
    def check_battery_for_trip(self, t_viaje_local: float, t_espera: float, t_viaje_cliente: float) -> bool:
        """Filtro preventivo de batería: reserva >= 15% al terminar."""
        consumo_proyectado = (t_viaje_local + t_espera + t_viaje_cliente) * 0.15
        return (self.bateria - consumo_proyectado) >= 15.0
        
    def consume_battery(self, mins_en_movimiento: float):
        self.bateria -= (mins_en_movimiento * 0.15)

class KitchenNetwork:
    def __init__(self, env: simpy.Environment):
        self.env = env
        # 10 locales con capacidad aleatoria de 3 a 6 fogones
        self.restaurantes = []
        for i in range(10):
            k_r = np.random.randint(3, 7)
            fogon = simpy.Resource(env, capacity=k_r)
            self.restaurantes.append({'id': i, 'fogones': fogon})