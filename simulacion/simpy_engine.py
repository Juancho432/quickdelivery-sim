import simpy
import random
import numpy as np
from typing import Dict, Any, Optional, List

try:
    from simulacion.entities import Order, Courier, CourierPool, KitchenNetwork, get_kinematic_travel_time
    from simulacion.policies import DispatchPolicy, GreedyImmediatePolicy, PredictiveSynchronizedPolicy
    from simulacion.metrics import MetricsCollector
except ImportError:
    from entities import Order, Courier, CourierPool, KitchenNetwork, get_kinematic_travel_time
    from policies import DispatchPolicy, GreedyImmediatePolicy, PredictiveSynchronizedPolicy
    from metrics import MetricsCollector


def run_markovian_replica(
    lambda_rate: float = 2.70,
    mu_rate: float = 0.05,
    c_servers: int = 70,
    sim_time: Optional[float] = None,
    warmup_time: Optional[float] = None,
    seed: Optional[int] = None,
) -> Dict[str, float]:
    """
    Ejecuta una réplica canónica de simulación de eventos discretos M/M/c en SimPy.
    - Llegadas según proceso de Poisson homogéneo Exp(lambda_rate).
    - Tiempos de servicio exponenciales independientes Exp(mu_rate).
    - c_servers servidores idénticos en paralelo con disciplina FIFO estricta.
    - Acumula integrales de tiempo continuo para L, Lq, rho y P0, y promedios muestrales para Wq, W y Pw.
    """
    rho_teo = lambda_rate / (c_servers * mu_rate)
    if rho_teo >= 1.0:
        raise ValueError(f"Sistema M/M/c inestable: rho={rho_teo:.4f} >= 1.0")

    rng = np.random.default_rng(seed)

    # Ajustar horizonte para asegurar ~20.000 arribos en ventana estacionaria
    if sim_time is None:
        target_arrivals = 20000.0
        obs_duration = max(5000.0, target_arrivals / lambda_rate)
        warmup_duration = 0.15 * obs_duration
        total_time = warmup_duration + obs_duration
    else:
        total_time = float(sim_time)
        warmup_duration = float(warmup_time) if warmup_time is not None else 0.15 * total_time

    env = simpy.Environment()
    servers = simpy.Resource(env, capacity=c_servers)

    # Variables de estado para integración temporal exacta en [warmup_duration, total_time]
    state = {
        "n_system": 0,
        "last_event_time": 0.0,
        "area_L": 0.0,
        "area_Lq": 0.0,
        "area_busy": 0.0,
        "time_empty": 0.0,
    }

    wait_times: List[float] = []
    system_times: List[float] = []
    waited_flags: List[int] = []

    def _update_time_integrals(current_time: float):
        t_prev = state["last_event_time"]
        if current_time > warmup_duration:
            t_start = max(t_prev, warmup_duration)
            dt = current_time - t_start
            if dt > 0.0:
                n = state["n_system"]
                state["area_L"] += n * dt
                state["area_Lq"] += max(0, n - c_servers) * dt
                state["area_busy"] += min(n, c_servers) * dt
                if n == 0:
                    state["time_empty"] += dt
        state["last_event_time"] = current_time

    def _customer_process(t_arr: float):
        with servers.request() as req:
            yield req
            t_start_service = env.now
            w_q = t_start_service - t_arr

            service_time = float(rng.exponential(1.0 / mu_rate))
            if warmup_duration <= t_arr < total_time:
                wait_times.append(w_q)
                system_times.append(w_q + service_time)
                waited_flags.append(1 if w_q > 1e-9 else 0)

            yield env.timeout(service_time)

            t_dep = env.now
            if t_dep <= total_time:
                _update_time_integrals(t_dep)
                state["n_system"] -= 1

    def _arrival_generator():
        while True:
            interarrival = float(rng.exponential(1.0 / lambda_rate))
            yield env.timeout(interarrival)
            t_now = env.now
            if t_now >= total_time:
                break
            _update_time_integrals(t_now)
            state["n_system"] += 1
            env.process(_customer_process(t_now))

    env.process(_arrival_generator())
    env.run(until=total_time)
    _update_time_integrals(total_time)

    obs_window = total_time - warmup_duration
    rho_sim = state["area_busy"] / (c_servers * obs_window)
    p0_sim = state["time_empty"] / obs_window
    lq_sim = state["area_Lq"] / obs_window
    l_sim = state["area_L"] / obs_window
    wq_sim = float(np.mean(wait_times)) if wait_times else 0.0
    w_sim = float(np.mean(system_times)) if system_times else (1.0 / mu_rate)
    pw_sim = float(np.mean(waited_flags)) if waited_flags else 0.0

    return {
        "rho": rho_sim,
        "P0": p0_sim,
        "Pw": pw_sim,
        "Lq": lq_sim,
        "Wq": wq_sim,
        "W": w_sim,
        "L": l_sim,
        "n_samples": len(wait_times),
    }


class SimpyEngine:
    """
    Motor de Simulación de Eventos Discretos (DES) de 24 horas para QuickDelivery Sim.
    Conecta el generador NHPP de órdenes, la red de 10 cocinas (47 fogones),
    el pool dinámico de repartidores (CourierPool) y las políticas de despacho (Strategy).
    """

    def __init__(
        self,
        policy: Optional[DispatchPolicy] = None,
        policy_name: str = "greedy",
        t_buffer: float = 2.5,
        seed: int = 42,
    ):
        self.seed = seed
        random.seed(seed)
        np.random.seed(seed)
        self.rng = np.random.default_rng(seed)

        self.env = simpy.Environment()
        self.cocinas = KitchenNetwork(self.env)
        self.pool_repartidores = CourierPool(self.env)
        self.flota = self.pool_repartidores.couriers
        self.pedidos: List[Order] = []
        self.metrics = MetricsCollector()

        if policy is not None:
            self.politica = policy
        elif policy_name.lower() in ("greedy", "voraz"):
            self.politica = GreedyImmediatePolicy()
        else:
            self.politica = PredictiveSynchronizedPolicy(t_buffer=t_buffer)

        # Sembrar flota nocturna inicial c(0) = 6 repartidores en t = 0.0
        for _ in range(6):
            coords = (float(self.rng.uniform(0.5, 5.5)), float(self.rng.uniform(0.5, 5.5)))
            bat = float(min(100.0, max(70.0, self.rng.normal(95.0, 5.0))))
            self.pool_repartidores.add_courier(coords=coords, bateria_inicial=bat)

    def _get_lambda_pedidos(self, minuto: float) -> float:
        """Devuelve la tasa de llegada de pedidos (ped/min) en las 7 franjas horarias de 24h (Tabla 5)."""
        if 0 <= minuto < 360:
            return 0.15       # Madrugada (00:00–06:00)
        elif 360 <= minuto < 600:
            return 1.00       # Desayuno (06:00–10:00)
        elif 600 <= minuto < 690:
            return 0.80       # Valle Mañana (10:00–11:30)
        elif 690 <= minuto < 870:
            return 2.70       # Pico Almuerzo (11:30–14:30)
        elif 870 <= minuto < 1110:
            return 1.20       # Valle Tarde (14:30–18:30)
        elif 1110 <= minuto < 1320:
            return 3.30       # Pico Cena (18:30–22:00)
        else:
            return 0.50       # Cierre Nocturno (22:00–24:00)

    def _get_target_fleet(self, minuto: float) -> int:
        """Oferta conectada de referencia c(t) por franja horaria acorde con la Tabla 5."""
        if 0 <= minuto < 360:
            return 6
        elif 360 <= minuto < 600:
            return 25
        elif 600 <= minuto < 690:
            return 20
        elif 690 <= minuto < 870:
            return 70
        elif 870 <= minuto < 1110:
            return 30
        elif 1110 <= minuto < 1320:
            return 85
        else:
            return 14

    def _get_lambda_logins(self, minuto: float) -> float:
        """Tasa de nuevos logins NHPP de repartidores (couriers/min) según franja horaria."""
        if 0 <= minuto < 360:
            return 0.02
        elif 360 <= minuto < 600:
            return 0.12
        elif 600 <= minuto < 690:
            return 0.10
        elif 690 <= minuto < 870:
            return 0.35
        elif 870 <= minuto < 1110:
            return 0.15
        elif 1110 <= minuto < 1320:
            return 0.45
        else:
            return 0.05

    def generador_logins_nhpp(self):
        """
        Proceso NHPP de conexión de repartidores (LoginRepartidor) y ajuste de flota por franja,
        respetando las desconexiones por turno de 6 horas o agotamiento de batería (<15%).
        """
        while self.env.now < 1440.0:
            self.pool_repartidores.purge_expired_idle_couriers()
            conectados = len(self.pool_repartidores.connected_couriers)
            meta_flota = self._get_target_fleet(self.env.now)
            tasa_login = self._get_lambda_logins(self.env.now)

            # Si sobran repartidores libres tras terminar un pico, algunos se desconectan voluntariamente
            if conectados > meta_flota:
                libres = self.pool_repartidores.available_couriers
                exceso = conectados - meta_flota
                for c in libres[:exceso]:
                    c.estado = "DESCONECTADO"
                conectados = len(self.pool_repartidores.connected_couriers)

            if conectados < meta_flota:
                deficit = meta_flota - conectados
                tasa_efectiva = max(tasa_login, deficit * 0.50)
            else:
                tasa_efectiva = tasa_login * 0.10

            dt = float(self.rng.exponential(1.0 / max(0.05, tasa_efectiva)))
            # Limitar el paso de revisión a máximo 2.0 min para reaccionar puntualmente a cambios de franja
            if dt > 2.0:
                yield self.env.timeout(2.0)
                continue

            yield self.env.timeout(dt)
            if self.env.now >= 1440.0:
                break

            if len(self.pool_repartidores.connected_couriers) < meta_flota:
                coords = (float(self.rng.uniform(0.5, 5.5)), float(self.rng.uniform(0.5, 5.5)))
                bat = float(min(100.0, max(70.0, self.rng.normal(95.0, 5.0))))
                self.pool_repartidores.add_courier(coords=coords, bateria_inicial=bat)

    def monitor_utilizacion_flota(self):
        """Muestrea cada minuto la utilización de la flota conectada para el colector de métricas."""
        while self.env.now < 1440.0:
            yield self.env.timeout(1.0)
            self.pool_repartidores.purge_expired_idle_couriers()
            conectados = self.pool_repartidores.connected_couriers
            if conectados:
                util_pct = self.pool_repartidores.get_utilization_pct()
                self.metrics.registrar_utilizacion_flota(util_pct)

    def generador_pedidos_nhpp(self):
        """Generador estocástico de órdenes según proceso NHPP en las 7 franjas de 24 horas."""
        order_id = 0
        while self.env.now < 1440.0:
            tasa_actual = self._get_lambda_pedidos(self.env.now)
            tiempo_llegada = float(self.rng.exponential(1.0 / tasa_actual))
            yield self.env.timeout(tiempo_llegada)
            if self.env.now >= 1440.0:
                break

            order_id += 1
            rest_id = int(self.rng.integers(0, 10))
            rest_coords = self.cocinas.restaurantes[rest_id]["coords"]
            t_coccion_propia = float(self.rng.lognormal(2.85, 0.35))
            # Paciencia del cliente ante espera excesiva: tiempo normal de cocción + Weibull(k=2.4, escala=40 min)
            paciencia = t_coccion_propia + float(40.0 * self.rng.weibull(2.4))
            eta_listo = self.cocinas.estimate_ready_time(rest_id, self.env.now, t_coccion_propia)

            # Coordenadas del cliente en el radio de cobertura urbana del restaurante (acotado al cuadrante [0, 6] km)
            cx = float(np.clip(rest_coords[0] + self.rng.uniform(-2.0, 2.0), 0.0, 6.0))
            cy = float(np.clip(rest_coords[1] + self.rng.uniform(-2.0, 2.0), 0.0, 6.0))

            nuevo_pedido = Order(
                id=order_id,
                rest_id=rest_id,
                t_creacion=float(self.env.now),
                coords_cliente=(cx, cy),
                coords_restaurante=rest_coords,
                t_cocina_est=t_coccion_propia,
                t_ready_est=eta_listo,
                paciencia_max=paciencia,
            )
            self.pedidos.append(nuevo_pedido)
            self.env.process(self.ciclo_vida_pedido(nuevo_pedido))

    def _proceso_coccion(
        self,
        order: Order,
        evento_comida_lista: simpy.Event,
        evento_orden_cancelada: simpy.Event,
    ):
        """
        Subproceso de preparación culinaria en los fogones finitos del restaurante.
        Si el cliente cancela mientras espera en la cola de cocina, abandona la cola sin ocupar fogón.
        """
        restaurante = self.cocinas.restaurantes[order.rest_id]
        with restaurante["fogones"].request() as req:
            if order.estado == "CREADO":
                order.estado = "EN_COLA_COCINA"

            resultado = yield req | evento_orden_cancelada
            if evento_orden_cancelada in resultado or order.estado.startswith("CANCELADO"):
                return

            order.t_inicio_cocina = float(self.env.now)
            if order.courier_id is None:
                order.estado = "EN_PREPARACION"

            # Actualiza ETA_listo real al entrar al fogón
            order.t_ready_est = float(self.env.now) + order.t_cocina_est

            res_coc = yield self.env.timeout(order.t_cocina_est) | evento_orden_cancelada
            if evento_orden_cancelada in res_coc or order.estado.startswith("CANCELADO"):
                return

            order.t_listo = float(self.env.now)
            if order.courier_id is None:
                order.estado = "LISTO_EN_MOSTRADOR"
                order.es_urgente = True
            if not evento_comida_lista.triggered:
                evento_comida_lista.succeed()

    def _vigilar_paciencia_y_limbo(
        self,
        order: Order,
        evento_recogida: simpy.Event,
        evento_orden_cancelada: simpy.Event,
    ):
        """
        Monitorea la paciencia Weibull del cliente antes de la recogida y el límite de 20 min en mostrador.
        """
        res = yield self.env.timeout(order.paciencia_max) | evento_recogida
        if not evento_recogida.triggered and not order.estado.startswith("CANCELADO"):
            order.estado = "CANCELADO_POR_CLIENTE"
            order.motivo_cancelacion = "IMPACIENCIA_WEIBULL"
            if not evento_orden_cancelada.triggered:
                evento_orden_cancelada.succeed()

    def ciclo_vida_pedido(self, order: Order):
        """
        Orquesta el flujo completo de una orden conectando la cocina, la política de despacho,
        el pool de repartidores, la espera en mostrador y el tránsito de entrega.
        """
        evento_comida_lista = self.env.event()
        evento_recogida = self.env.event()
        evento_orden_cancelada = self.env.event()

        self.env.process(self._proceso_coccion(order, evento_comida_lista, evento_orden_cancelada))
        self.env.process(self._vigilar_paciencia_y_limbo(order, evento_recogida, evento_orden_cancelada))

        # 1. Determinar el instante de disparo del despacho según la política (Voraz vs Sincronizada)
        while True:
            t_despacho = self.politica.calculate_target_dispatch_time(
                order, self.pool_repartidores.available_couriers, self.env.now, order.t_ready_est
            )
            order.t_despacho_prog = t_despacho
            # Si la política es sincronizada y el pedido sigue en cola esperando fogón, posterga el despacho
            if isinstance(self.politica, PredictiveSynchronizedPolicy) and order.t_inicio_cocina is None:
                espera_paso = max(1.0, t_despacho - self.env.now)
            else:
                espera_paso = max(0.0, t_despacho - self.env.now)

            if espera_paso <= 0.0:
                break

            res_esp = yield self.env.timeout(espera_paso) | evento_orden_cancelada | evento_comida_lista
            if evento_orden_cancelada in res_esp or order.estado.startswith("CANCELADO"):
                self.metrics.registrar_cancelacion()
                return
            if evento_comida_lista in res_esp:
                break
            # Si ya entró a fogón y alcanzó t_despacho, sale del bucle para despachar
            if order.t_inicio_cocina is not None and self.env.now >= order.t_despacho_prog - 1e-6:
                break

        # 2. Búsqueda y asignación de repartidor del CourierPool (ciclos de 45s = 0.75 min)
        courier_asignado: Optional[Courier] = None
        while courier_asignado is None:
            if evento_orden_cancelada.triggered or order.estado.startswith("CANCELADO"):
                self.metrics.registrar_cancelacion()
                return

            if order.t_listo is not None and (self.env.now - order.t_listo) >= 20.0:
                order.estado = "CANCELADO_SIN_REPARTIDOR"
                order.motivo_cancelacion = "LIMBO_MOSTRADOR_20MIN"
                if not evento_orden_cancelada.triggered:
                    evento_orden_cancelada.succeed()
                self.metrics.registrar_cancelacion()
                return

            candidato = self.politica.assign_order(
                order,
                self.pool_repartidores.available_couriers,
                self.env,
                order.t_ready_est,
            )
            if candidato is not None:
                courier_asignado = candidato
                courier_asignado.estado = "VIAJANDO_A_LOCAL"
                courier_asignado.pedido_actual = order
                order.courier_id = courier_asignado.id
                order.t_asignado = float(self.env.now)
                order.estado = "ASIGNADO"
                break

            order.reintentos += 1
            res_retry = yield self.env.timeout(0.75) | evento_orden_cancelada
            if evento_orden_cancelada in res_retry:
                self.metrics.registrar_cancelacion()
                return

        # 3. Desplazamiento del repartidor hacia el restaurante (LlegadaARestaurante)
        t_inicio_servicio_rep = float(self.env.now)
        rx, ry = order.coords_restaurante
        t_viaje_local = get_kinematic_travel_time(
            courier_asignado.coords[0], courier_asignado.coords[1], rx, ry, rng=self.rng
        )
        res_viaje = yield self.env.timeout(t_viaje_local) | evento_orden_cancelada
        if evento_orden_cancelada in res_viaje or order.estado.startswith("CANCELADO"):
            t_parcial = float(self.env.now) - t_inicio_servicio_rep
            courier_asignado.consume_battery(mins_en_movimiento=t_parcial)
            courier_asignado.tiempo_en_servicio += t_parcial
            if courier_asignado.evaluate_post_delivery():
                self.pool_repartidores.notify_availability()
            self.metrics.registrar_cancelacion()
            return

        courier_asignado.consume_battery(mins_en_movimiento=t_viaje_local)
        courier_asignado.coords = (rx, ry)
        order.t_arribo_rep = float(self.env.now)
        courier_asignado.estado = "EN_MOSTRADOR"

        # 4. Sincronización en mostrador: si la comida aún no ha salido de cocina, el repartidor espera ocioso
        if not evento_comida_lista.triggered:
            t_inicio_espera_rest = float(self.env.now)
            res_mostrador = yield evento_comida_lista | evento_orden_cancelada
            t_espera_ociosa = float(self.env.now) - t_inicio_espera_rest
            courier_asignado.consume_battery(mins_en_reposo=t_espera_ociosa)
            courier_asignado.tiempo_espera_rest += t_espera_ociosa

            if evento_orden_cancelada in res_mostrador or order.estado.startswith("CANCELADO"):
                courier_asignado.tiempo_en_servicio += float(self.env.now) - t_inicio_servicio_rep
                if courier_asignado.evaluate_post_delivery():
                    self.pool_repartidores.notify_availability()
                self.metrics.registrar_cancelacion()
                return

        if order.t_listo is None:
            order.t_listo = float(self.env.now)

        # Evaluar enfriamiento en mostrador (> 6.0 min incrementa riesgo de abandono +50%)
        t_mostrador = max(0.0, order.t_arribo_rep - order.t_listo)
        if t_mostrador >= 20.0:
            order.estado = "CANCELADO_SIN_REPARTIDOR"
            order.motivo_cancelacion = "LIMBO_MOSTRADOR_20MIN"
            if not evento_orden_cancelada.triggered:
                evento_orden_cancelada.succeed()
            courier_asignado.tiempo_en_servicio += float(self.env.now) - t_inicio_servicio_rep
            if courier_asignado.evaluate_post_delivery():
                self.pool_repartidores.notify_availability()
            self.metrics.registrar_cancelacion()
            return

        if t_mostrador > 6.0 and (self.env.now - order.t_creacion) >= (order.paciencia_max / 1.25):
            order.estado = "CANCELADO_POR_CLIENTE"
            order.motivo_cancelacion = "IMPACIENCIA_COMIDA_FRIA"
            if not evento_orden_cancelada.triggered:
                evento_orden_cancelada.succeed()
            courier_asignado.tiempo_en_servicio += float(self.env.now) - t_inicio_servicio_rep
            if courier_asignado.evaluate_post_delivery():
                self.pool_repartidores.notify_availability()
            self.metrics.registrar_cancelacion()
            return

        # 5. Recogida del pedido y tránsito hacia el domicilio del cliente (RecogidaPedido -> EntregaFinal)
        if not evento_recogida.triggered:
            evento_recogida.succeed()
        order.t_recogida = float(self.env.now)
        order.estado = "EN_TRANSITO_CLIENTE"
        courier_asignado.estado = "VIAJANDO_AL_CLIENTE"

        cx, cy = order.coords_cliente
        t_viaje_cliente = get_kinematic_travel_time(rx, ry, cx, cy, rng=self.rng)
        yield self.env.timeout(t_viaje_cliente)

        courier_asignado.consume_battery(mins_en_movimiento=t_viaje_cliente)
        courier_asignado.coords = (cx, cy)

        # 6. Entrega Final Exitosa
        order.t_entregado = float(self.env.now)
        order.estado = "ENTREGADO"
        courier_asignado.pedidos_completados += 1
        courier_asignado.tiempo_en_servicio += float(self.env.now) - t_inicio_servicio_rep

        self.metrics.registrar_pedido_completado(
            t_creacion=order.t_creacion,
            t_listo=order.t_listo,
            t_arribo_rep=order.t_arribo_rep,
            t_entrega=order.t_entregado,
        )

        # Evaluar continuidad de turno (<6h) y nivel de batería (>=15%)
        sigue_activo = courier_asignado.evaluate_post_delivery()
        if sigue_activo:
            self.pool_repartidores.notify_availability()

    def run_24h(self, export_path: Optional[str] = "datos/simulation_results.json") -> Dict[str, Any]:
        """Ejecuta la simulación continua de 24 horas (1.440 minutos) y retorna los KPIs."""
        nombre_pol = self.politica.__class__.__name__
        print(f"Iniciando Simulación 24H (Gemelo Digital DES) — Política: {nombre_pol}...")
        self.env.process(self.generador_pedidos_nhpp())
        self.env.process(self.generador_logins_nhpp())
        self.env.process(self.monitor_utilizacion_flota())

        # Drenaje adicional de 90 min tras el minuto 1440 para concluir órdenes en curso al cierre
        self.env.run(until=1530.0)

        kpis = self.metrics.calcular_kpis()
        entregados = sum(1 for p in self.pedidos if p.estado == "ENTREGADO")
        cancelados = sum(1 for p in self.pedidos if p.estado.startswith("CANCELADO"))
        kpis["politica"] = nombre_pol
        kpis["total_ordenes_generadas"] = len(self.pedidos)
        kpis["ordenes_entregadas"] = entregados
        kpis["ordenes_canceladas"] = cancelados
        kpis["repartidores_totales_conectados_dia"] = len(self.pool_repartidores.couriers)

        if export_path:
            self.metrics.exportar_json(export_path)

        print(
            f"[{nombre_pol}] Total pedidos: {len(self.pedidos)} | "
            f"Entregados: {entregados} | Cancelados: {cancelados} | "
            f"T_espera_rest promedio: {kpis['T_espera_rest_avg_min']:.2f} min | "
            f"W_total_p95: {kpis['W_total_p95_min']:.2f} min | "
            f"P_canc: {kpis['P_canc_porcentaje']:.2f}%"
        )
        return kpis

    def run_markovian_replica(
        self,
        c_servers: int = 70,
        lambda_rate: float = 2.70,
        mu_rate: float = 0.05,
        seed: Optional[int] = None,
    ) -> Dict[str, float]:
        """Método de instancia que delega en la réplica canónica M/M/c."""
        return run_markovian_replica(
            lambda_rate=lambda_rate,
            mu_rate=mu_rate,
            c_servers=c_servers,
            seed=seed if seed is not None else self.seed,
        )


if __name__ == "__main__":
    # 1. Ejecutar política Voraz Inmediata conectada al CourierPool
    motor_voraz = SimpyEngine(policy_name="greedy", seed=42)
    kpis_voraz = motor_voraz.run_24h(export_path="datos/simulation_results.json")

    # 2. Ejecutar política Sincronizada Predictiva conectada al CourierPool para comparar
    motor_sync = SimpyEngine(policy_name="synchronized", t_buffer=2.5, seed=42)
    kpis_sync = motor_sync.run_24h(export_path=None)

    # 3. Demostración rápida de una réplica M/M/c en Pico Almuerzo
    res_mmc = motor_voraz.run_markovian_replica(c_servers=70, lambda_rate=2.70, mu_rate=0.05, seed=42)
    print(
        f"\n[Réplica M/M/c Pico Almuerzo] rho={res_mmc['rho']:.4f}, "
        f"Wq={res_mmc['Wq']:.4f} min, W={res_mmc['W']:.4f} min, L={res_mmc['L']:.4f}"
    )
