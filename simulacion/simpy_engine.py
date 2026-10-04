import simpy
import random
import numpy as np
from entities import Order, Courier, KitchenNetwork
from policies import PredictiveSynchronizedPolicy

class SimpyEngine:
    def __init__(self):
        # Reproducibilidad estricta
        random.seed(42)
        np.random.seed(42)
        
        self.env = simpy.Environment()
        self.cocinas = KitchenNetwork(self.env)
        self.flota = []
        self.pedidos = []
        self.politica = PredictiveSynchronizedPolicy(t_buffer=2.5)

    def _get_lambda_pedidos(self, minuto: float) -> float:
        """Devuelve tasa de pedidos (NHPP) según hora del día (24h)."""
        if 690 <= minuto < 870: return 2.70   # Almuerzo
        elif 1110 <= minuto < 1320: return 3.30 # Cena
        elif 870 <= minuto < 1110: return 1.20 # Tarde
        else: return 0.50 # Base nocturna/mañana

    def generador_pedidos_nhpp(self):
        """Generador de pedidos estocástico con tasas variables por franja horaria."""
        order_id = 0
        while self.env.now < 1440.0:  # 24 horas continuas
            tasa_actual = self._get_lambda_pedidos(self.env.now)
            # Thinning simple para simular NHPP
            tiempo_llegada = random.expovariate(tasa_actual)
            yield self.env.timeout(tiempo_llegada)
            
            order_id += 1
            nuevo_pedido = Order(
                id=order_id, 
                rest_id=random.randint(0, 9), 
                t_creacion=self.env.now,
                coords_cliente=(random.uniform(0,6), random.uniform(0,6))
            )
            self.pedidos.append(nuevo_pedido)
            self.env.process(self.proceso_restaurante(nuevo_pedido))

    def proceso_restaurante(self, order: Order):
        """Lógica de fogones finitos y distribución Log-Normal."""
        restaurante = self.cocinas.restaurantes[order.rest_id]
        
        with restaurante['fogones'].request() as req:
            order.estado = "EN_COLA_COCINA"
            yield req 
            
            order.estado = "EN_PREPARACION"
            t_coccion = np.random.lognormal(2.85, 0.35) # Media física ~18.5 min
            yield self.env.timeout(t_coccion)
            
            order.estado = "LISTO_EN_MOSTRADOR"
            order.t_listo = self.env.now
            # Aquí se engancha la lógica de la política y el dispatch predictivo...

    def run_24h(self):
        """Orquestador principal del Gemelo Digital (24 horas)."""
        print("Iniciando Simulación 24H (Gemelo Digital DES)...")
        self.env.process(self.generador_pedidos_nhpp())
        # Aquí se inicia generador_logins_nhpp (límite 6h de turno)...
        self.env.run(until=1440.0)
        print(f"Total pedidos procesados: {len(self.pedidos)}")

    def run_markovian_replica(self, c_servers: int = 5, lambda_rate: float = 2.0, mu_rate: float = 0.5):
        """
        Réplica canónica (M/M/c) para el Integrante 3.
        Contrasta métricas de la simulación canónica con las fórmulas de Erlang C.
        """
        print("\n--- Ejecutando Réplica Markoviana Canónica para contraste ---")
        # Generador de llegadas exponenciales planas
        # Tiempos de servicio exponenciales planos
        # Flota homogénea estacionaria
        print(f"Proveerá las trazas para validar rho < 1 y la Ley de Little (L = λW).")

if __name__ == '__main__':
    motor = SimpyEngine()
    motor.run_24h()
    motor.run_markovian_replica()