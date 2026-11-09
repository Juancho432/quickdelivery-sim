from abc import ABC, abstractmethod
from typing import List, Optional
try:
    from simulacion.entities import Order, Courier, get_kinematic_travel_time
except ImportError:
    from entities import Order, Courier, get_kinematic_travel_time


class DispatchPolicy(ABC):
    """Interfaz base Strategy para las políticas de asignación de repartidores."""

    @abstractmethod
    def calculate_target_dispatch_time(
        self, order: Order, couriers: List[Courier], env_now: float, eta_listo: float
    ) -> float:
        """Retorna el instante (minuto de simulación) en el que debe dispararse la búsqueda de repartidor."""
        pass

    @abstractmethod
    def assign_order(
        self, order: Order, couriers: List[Courier], env, eta_listo: float
    ) -> Optional[Courier]:
        """Evalúa los repartidores disponibles en el pool y selecciona el candidato óptimo."""
        pass


class GreedyImmediatePolicy(DispatchPolicy):
    """
    Política Actual (Línea Base): Asignación Voraz Inmediata.
    Despacha al repartidor libre más cercano en el instante en que se crea la orden,
    sin sincronizar con el tiempo estimado de salida de cocina (ETA_listo).
    """

    def calculate_target_dispatch_time(
        self, order: Order, couriers: List[Courier], env_now: float, eta_listo: float
    ) -> float:
        # En la política voraz el despacho se solicita de forma inmediata (t_despacho = t_actual)
        return env_now

    def assign_order(
        self, order: Order, couriers: List[Courier], env, eta_listo: float
    ) -> Optional[Courier]:
        rx, ry = order.coords_restaurante
        cx, cy = order.coords_cliente
        t_viaje_cliente_est = get_kinematic_travel_time(rx, ry, cx, cy, deterministic=True)

        candidatos_aptos: List[tuple[float, Courier]] = []
        for c in couriers:
            if c.estado != "LIBRE" or c.is_shift_expired(env.now):
                continue
            t_viaje_local_est = get_kinematic_travel_time(
                c.coords[0], c.coords[1], rx, ry, deterministic=True
            )
            t_espera_est = max(0.0, eta_listo - (env.now + t_viaje_local_est))
            if c.check_battery_for_trip(t_viaje_local_est, t_espera_est, t_viaje_cliente_est):
                candidatos_aptos.append((t_viaje_local_est, c))

        if not candidatos_aptos:
            return None

        # Selecciona al repartidor más cercano al restaurante
        candidatos_aptos.sort(key=lambda item: item[0])
        return candidatos_aptos[0][1]


class PredictiveSynchronizedPolicy(DispatchPolicy):
    """
    Política Alternativa: Despacho Sincronizado Predictivo (Just-in-Time).
    Posterga la asignación hasta t_despacho = ETA_listo - t_viaje_est + t_buffer
    para minimizar el tiempo ocioso del repartidor en el mostrador del restaurante.
    """

    def __init__(self, t_buffer: float = 2.5):
        self.t_buffer = t_buffer
        self.fase_escalamiento = 1

    def calculate_target_dispatch_time(
        self, order: Order, couriers: List[Courier], env_now: float, eta_listo: float
    ) -> float:
        rx, ry = order.coords_restaurante
        libres = [c for c in couriers if c.estado == "LIBRE" and not c.is_shift_expired(env_now)]
        if libres:
            tiempos = [
                get_kinematic_travel_time(c.coords[0], c.coords[1], rx, ry, deterministic=True)
                for c in libres
            ]
            t_viaje_ref = float(min(tiempos))
        else:
            # Tiempo medio de aproximación al restaurante (~5.0 min según Sección 3.7.2)
            t_viaje_ref = 5.0

        # Despachar de modo que el repartidor arribe ~t_buffer minutos antes de ETA_listo
        t_despacho = eta_listo - t_viaje_ref - self.t_buffer
        return max(env_now, t_despacho)

    def assign_order(
        self, order: Order, couriers: List[Courier], env, eta_listo: float
    ) -> Optional[Courier]:
        rx, ry = order.coords_restaurante
        cx, cy = order.coords_cliente
        t_viaje_cliente_est = get_kinematic_travel_time(rx, ry, cx, cy, deterministic=True)

        # Si el pedido ya está listo en mostrador (Fase 2: Urgente), asigna al más cercano de inmediato
        if order.t_listo is not None or env.now >= eta_listo:
            order.es_urgente = True
            aptos_urgentes = []
            for c in couriers:
                if c.estado != "LIBRE" or c.is_shift_expired(env.now):
                    continue
                t_local = get_kinematic_travel_time(c.coords[0], c.coords[1], rx, ry, deterministic=True)
                if c.check_battery_for_trip(t_local, 0.0, t_viaje_cliente_est):
                    aptos_urgentes.append((t_local, c))
            if aptos_urgentes:
                aptos_urgentes.sort(key=lambda item: item[0])
                return aptos_urgentes[0][1]
            return None

        # Fase 1: Selección sincronizada por cercanía del arribo al ETA_listo
        factor = 1 if order.reintentos == 0 else 2
        ventana_min = eta_listo - (factor * self.t_buffer) - 1.0
        ventana_max = eta_listo + (factor * self.t_buffer) + 3.0

        calificados: List[tuple[float, Courier]] = []
        todos_aptos: List[tuple[float, Courier]] = []

        for c in couriers:
            if c.estado != "LIBRE" or c.is_shift_expired(env.now):
                continue
            t_viaje_local = get_kinematic_travel_time(
                c.coords[0], c.coords[1], rx, ry, deterministic=True
            )
            t_arribo = env.now + t_viaje_local
            t_espera_est = max(0.0, eta_listo - t_arribo)

            if not c.check_battery_for_trip(t_viaje_local, t_espera_est, t_viaje_cliente_est):
                continue

            desvio_eta = abs(t_arribo - eta_listo)
            todos_aptos.append((desvio_eta, c))
            if ventana_min <= t_arribo <= ventana_max:
                calificados.append((desvio_eta, c))

        if calificados:
            calificados.sort(key=lambda item: item[0])
            return calificados[0][1]

        # Si ya se expandió la ventana (reintento >= 1) y hay couriers aptos, toma el de menor desvío al ETA
        if order.reintentos >= 1 and todos_aptos:
            todos_aptos.sort(key=lambda item: item[0])
            return todos_aptos[0][1]

        self.fase_escalamiento = 2
        return None
