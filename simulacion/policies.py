from abc import ABC, abstractmethod
from typing import List, Optional
from entities import Order, Courier, get_kinematic_travel_time

class DispatchPolicy(ABC):
    @abstractmethod
    def assign_order(self, order: Order, couriers: List[Courier], env, eta_listo: float) -> Optional[Courier]:
        pass

class GreedyImmediatePolicy(DispatchPolicy):
    def assign_order(self, order: Order, couriers: List[Courier], env, eta_listo: float) -> Optional[Courier]:
        """Política base: asigna al instante al repartidor más cercano libre."""
        libres = [c for c in couriers if c.estado == "LIBRE"]
        if not libres: return None
        
        # Simula asignación voraz basada estrictamente en distancia
        best_courier = min(libres, key=lambda c: get_kinematic_travel_time(
            c.coords[0], c.coords[1], 3.0, 3.0)) # 3.0, 3.0 asume centro del restaurante
        return best_courier

class PredictiveSynchronizedPolicy(DispatchPolicy):
    def __init__(self, t_buffer: float = 2.5):
        self.t_buffer = t_buffer
        self.fase_escalamiento = 1
        
    def assign_order(self, order: Order, couriers: List[Courier], env, eta_listo: float) -> Optional[Courier]:
        """Sincroniza despacho: t_despacho = ETA_listo - t_viaje + t_buffer."""
        candidatos = [c for c in couriers if c.estado == "LIBRE" or c.estado == "VIAJANDO_AL_CLIENTE"]
        calificados = []
        
        # Margen de ventana de sincronización
        ventana_min = eta_listo - (self.fase_escalamiento * self.t_buffer) - 1.0
        ventana_max = eta_listo + (self.fase_escalamiento * self.t_buffer) + 3.0
        
        for c in candidatos:
            t_viaje_local = get_kinematic_travel_time(c.coords[0], c.coords[1], 3.0, 3.0)
            t_arribo = env.now + t_viaje_local
            
            if ventana_min <= t_arribo <= ventana_max:
                if c.check_battery_for_trip(t_viaje_local, 0, 10):  # 10 min promedio al cliente
                    calificados.append(c)
                    
        if not calificados:
            # Fase 1: Escalamiento de ventana (Ampliar ventana)
            self.fase_escalamiento = 2 
            return None
            
        # Fase 2 (Implícita): En caso de retornar al motor, el motor añadirá el bono urgente +20%
        return calificados[0] # El primero en aceptar (45s broadcast modelado)