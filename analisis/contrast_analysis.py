import sys
from pathlib import Path
import numpy as np

# Agregar el directorio raíz al path para permitir importaciones entre carpetas
sys.path.append(str(Path(__file__).parent.parent))

from analisis.queueing_theory import QueueingModelMMC

# Modelo run_markovian_replica()
from simulacion.simpy_engine import run_markovian_replica

class ContrastAnalyzer:
    """
    Ejecuta el contraste estadístico entre el modelo matemático M/M/c 
    y el gemelo digital en SimPy bajo condiciones de frontera markovianas puras.
    """
    def __init__(self, lambda_rate=12.0, mu_rate=3.0, c_servers=5, num_replicas=30):
        self.lambda_rate = lambda_rate
        self.mu_rate = mu_rate
        self.c_servers = c_servers
        self.num_replicas = num_replicas
        
        # Instanciar el modelo matemático
        self.modelo_teorico = QueueingModelMMC(lambda_rate, mu_rate, c_servers)

    def ejecutar_contraste(self):
        # 1. Obtener la verdad teórica
        metricas_teoricas = self.modelo_teorico.calculate_metrics()
        
        # 2. Recolectar datos de la simulación
        resultados_simulacion = {"rho": [], "Lq": [], "Wq": [], "W": [], "L": []}
        
        print(f"Ejecutando {self.num_replicas} réplicas del motor SimPy...")
        
        for _ in range(self.num_replicas):
            # Llamamos a la función de SimPy de tu compañero. 
            # (Asume que devuelve un diccionario con las llaves rho, Lq, Wq, W, L)
            metricas_simpy = run_markovian_replica(self.lambda_rate, self.mu_rate, self.c_servers)
            
            for k in resultados_simulacion.keys():
                resultados_simulacion[k].append(metricas_simpy[k])
        
        # 3. Promediar los resultados estocásticos con NumPy
        metricas_promedio_simpy = {k: np.mean(v) for k, v in resultados_simulacion.items()}
        
        # 4. Calcular el error porcentual y mostrar la tabla comparativa
        print("\n--- Resultados del Contraste Analítico (M/M/c vs SimPy) ---")
        print(f"{'Métrica':<10} | {'Teórico M/M/c':<15} | {'Simulado (Prom)':<15} | {'Error (%)':<10}")
        print("-" * 60)
        
        for metrica in ["rho", "Lq", "Wq", "W", "L"]:
            val_teorico = metricas_teoricas[metrica]
            val_simulado = metricas_promedio_simpy[metrica]
            
            if val_teorico == 0:
                error_pct = 0.0
            else:
                error_pct = abs((val_simulado - val_teorico) / val_teorico) * 100
            
            alerta = "ALERTA (>5%)" if error_pct > 5.0 else "OK"
            print(f"{metrica:<10} | {val_teorico:<15.4f} | {val_simulado:<15.4f} | {error_pct:<7.2f}% {alerta}")

if __name__ == "__main__":
    try:
        analizador = ContrastAnalyzer(lambda_rate=12.0, mu_rate=3.0, c_servers=5, num_replicas=30)
        analizador.ejecutar_contraste()
    except ImportError as e:
        print(f"Aviso de Dependencia: {e}")
        print("El script espera que la rama de tu compañero esté fusionada para encontrar 'run_markovian_replica'.")