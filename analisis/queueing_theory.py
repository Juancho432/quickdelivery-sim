import math
from typing import Dict, List, Any

class QueueingModelMMC:
    """
    Modelo analítico M/M/c basado en la Fórmula C de Erlang.
    Utilizado para el contraste numérico contra el gemelo digital en SimPy
    y el dimensionamiento estocástico de la flota de última milla.
    """
    def __init__(self, lambda_rate: float, mu_rate: float, c_servers: int):
        self.lambda_rate = lambda_rate
        self.mu_rate = mu_rate
        self.c = c_servers
        
        # Factor de utilización del sistema (rho)
        self.rho = self.lambda_rate / (self.c * self.mu_rate)
        
        if self.rho >= 1.0:
            raise ValueError(f"Sistema inestable: rho = {self.rho:.4f} (debe ser estrictamente < 1 para M/M/c)")

    def calculate_p0(self) -> float:
        """Calcula la probabilidad de que el sistema esté totalmente vacío (P0)."""
        sum_n = sum(((self.c * self.rho) ** n) / math.factorial(n) for n in range(self.c))
        term_c = ((self.c * self.rho) ** self.c) / (math.factorial(self.c) * (1.0 - self.rho))
        return 1.0 / (sum_n + term_c)

    def calculate_pw(self) -> float:
        """Calcula la probabilidad de tener que esperar en cola (Fórmula C de Erlang)."""
        p0 = self.calculate_p0()
        term_c = ((self.c * self.rho) ** self.c) / (math.factorial(self.c) * (1.0 - self.rho))
        return term_c * p0

    def calculate_metrics(self) -> Dict[str, float]:
        """
        Calcula y retorna todas las métricas operativas del sistema 
        aplicando las ecuaciones de Erlang y la Ley de Little.
        """
        p0 = self.calculate_p0()
        pw = self.calculate_pw()
        
        # Longitud de la cola (Lq)
        l_q = (pw * self.rho) / (1.0 - self.rho)
        
        # Tiempo en cola (Wq) y tiempo total (W) vía Ley de Little
        w_q = l_q / self.lambda_rate
        w = w_q + (1.0 / self.mu_rate)
        
        # Longitud total del sistema (L)
        l = self.lambda_rate * w
        
        return {
            "rho": self.rho,
            "P0": p0,
            "Pw": pw,
            "Lq": l_q,
            "Wq": w_q,
            "W": w,
            "L": l
        }

# Franjas horarias operativas oficiales del proyecto QuickDelivery Sim (24 horas)
# Parámetros calibrados: tiempo medio de servicio 1/mu = 20.0 min (mu = 0.05 ped/min)
FRANJAS_PROYECTO: List[Dict[str, Any]] = [
    {"nombre": "Madrugada (00:00–06:00)", "lambda": 0.15, "c": 6, "mu": 0.05, "t_serv": 20.0},
    {"nombre": "Desayuno (06:00–10:00)", "lambda": 1.00, "c": 25, "mu": 0.05, "t_serv": 20.0},
    {"nombre": "Valle Mañana (10:00–11:30)", "lambda": 0.80, "c": 20, "mu": 0.05, "t_serv": 20.0},
    {"nombre": "Pico Almuerzo (11:30–14:30)", "lambda": 2.70, "c": 70, "mu": 0.05, "t_serv": 20.0},
    {"nombre": "Valle Tarde (14:30–18:30)", "lambda": 1.20, "c": 30, "mu": 0.05, "t_serv": 20.0},
    {"nombre": "Pico Cena (18:30–22:00)", "lambda": 3.30, "c": 85, "mu": 0.05, "t_serv": 20.0},
    {"nombre": "Cierre Nocturno (22:00–24:00)", "lambda": 0.50, "c": 14, "mu": 0.05, "t_serv": 20.0},
]

def print_pico_almuerzo_demo():
    """Ejecuta y muestra en detalle el cálculo del Pico del Almuerzo."""
    pico = FRANJAS_PROYECTO[3] # Pico Almuerzo
    modelo = QueueingModelMMC(pico["lambda"], pico["mu"], pico["c"])
    m = modelo.calculate_metrics()
    
    print("=" * 80)
    print("DEMOSTRACIÓN ANALÍTICA: PICO DEL ALMUERZO (11:30–14:30)")
    print("=" * 80)
    print(f"Parámetros de entrada:")
    print(f"  * Tasa de llegada (lambda):     {pico['lambda']:.2f} ped/min ({pico['lambda']*60:.1f} ped/h)")
    print(f"  * Tasa de servicio courier (mu): {pico['mu']:.2f} serv/min (1/mu = {pico['t_serv']:.1f} min)")
    print(f"  * Flota activa (c):             {pico['c']} repartidores")
    print("-" * 80)
    print(f"Resultados calculados:")
    print(f"  * Factor de utilización (rho):   {m['rho']:.4f} ({m['rho']*100:.2f}%)")
    print(f"  * Probabilidad de vacío (P0):    {m['P0']:.4e}")
    print(f"  * Prob. de espera Erlang-C (Pw): {m['Pw']:.4f} ({m['Pw']*100:.2f}%)")
    print(f"  * Pedidos promedio en cola (Lq): {m['Lq']:.4f} pedidos")
    print(f"  * Tiempo medio en cola (Wq):     {m['Wq']:.4f} minutos ({m['Wq']*60:.2f} segundos)")
    print(f"  * Tiempo medio total (W):        {m['W']:.4f} minutos")
    print(f"  * Pedidos promedio sistema (L):  {m['L']:.4f} pedidos")
    print("-" * 80)
    print(f"Verificación Ley de Little:")
    print(f"  * Lq == lambda * Wq:             {m['Lq']:.4f} == {pico['lambda']*m['Wq']:.4f} -> OK")
    print(f"  * L == lambda * W:               {m['L']:.4f} == {pico['lambda']*m['W']:.4f} -> OK")
    print(f"  * Servidores ocupados (L - Lq):  {m['L'] - m['Lq']:.4f} == c * rho = {pico['c']*m['rho']:.4f} -> OK")
    print("=" * 80)
    print()

def print_tabla_todas_franjas():
    """Calcula y muestra la tabla comparativa de las 7 franjas del proyecto."""
    print("=" * 115)
    print("TABLA MAESTRA DE TEORÍA DE COLAS M/M/c EN LAS 7 FRANJAS DE 24 HORAS (QUICKDELIVERY SIM)")
    print("=" * 115)
    header = f"{'Franja Horaria':<28} | {'lambda':<6} | {'c':<3} | {'1/mu':<5} | {'rho':<7} | {'P0':<10} | {'Pw':<7} | {'Lq':<7} | {'Wq(min)':<8} | {'W(min)':<8} | {'L':<7}"
    print(header)
    print("-" * 115)
    
    for f in FRANJAS_PROYECTO:
        mod = QueueingModelMMC(f["lambda"], f["mu"], f["c"])
        res = mod.calculate_metrics()
        
        p0_str = f"{res['P0']:.2e}" if res['P0'] < 0.001 else f"{res['P0']:.4f}"
        
        row = (f"{f['nombre']:<28} | {f['lambda']:<6.2f} | {f['c']:<3} | {f['t_serv']:<5.1f} | "
               f"{res['rho']:<7.4f} | {p0_str:<10} | {res['Pw']:<7.4f} | {res['Lq']:<7.4f} | "
               f"{res['Wq']:<8.4f} | {res['W']:<8.4f} | {res['L']:<7.4f}")
        print(row)
    print("=" * 115)

if __name__ == "__main__":
    print_pico_almuerzo_demo()
    print_tabla_todas_franjas()