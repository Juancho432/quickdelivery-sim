import numpy as np
import json
from pathlib import Path

class MetricsCollector:
    """
    Recolector de métricas estocásticas del gemelo digital.
    Captura eventos de SimPy, calcula percentiles (p95, p99) con NumPy
    y exporta los KPIs definidos en la Sección 3.9 del documento maestro.
    """
    def __init__(self):
        # "Bolsillos" para guardar los tiempos en minutos
        self.tiempos_ciclo_total = []
        self.tiempos_espera_repartidor = []
        self.tiempos_comida_mostrador = []
        
        # Contadores para calcular la tasa de cancelación
        self.total_pedidos = 0
        self.pedidos_cancelados = 0
        
        # Historial para el % de utilización de la flota (rho)
        self.utilizacion_flota = []

    def registrar_pedido_completado(self, t_creacion: float, t_listo: float, t_arribo_rep: float, t_entrega: float):
        """
        El orquestador de SimPy llamará a este método cada vez que un cliente reciba su comida.
        """
        self.total_pedidos += 1
        
        # 1. Tiempo de ciclo total (W_total)
        self.tiempos_ciclo_total.append(t_entrega - t_creacion)
        
        # 2. Espera del repartidor (T_espera_rest)
        # Si la comida no estaba lista, el repartidor esperó: t_listo - t_arribo_rep. Si ya estaba, esperó 0.
        espera_rep = max(0.0, t_listo - t_arribo_rep)
        self.tiempos_espera_repartidor.append(espera_rep)
        
        # 3. Enfriamiento en mostrador (T_mostrador)
        # Si el repartidor no había llegado, la comida esperó: t_arribo_rep - t_listo.
        espera_comida = max(0.0, t_arribo_rep - t_listo)
        self.tiempos_comida_mostrador.append(espera_comida)

    def registrar_cancelacion(self):
        """Registra un pedido que superó la impaciencia del cliente (curva Weibull)."""
        self.total_pedidos += 1
        self.pedidos_cancelados += 1

    def registrar_utilizacion_flota(self, porcentaje_utilizacion: float):
        """Registra instantáneas (ej. cada minuto) del % de motos ocupadas."""
        self.utilizacion_flota.append(porcentaje_utilizacion)

    def calcular_kpis(self) -> dict:
        """
        Toma todos los miles de datos crudos guardados en las listas
        y extrae los KPIs operativos utilizando NumPy.
        """
        if self.total_pedidos == 0:
            return {"error": "No se registraron datos en la simulación."}

        tasa_cancelacion = (self.pedidos_cancelados / self.total_pedidos) * 100

        # np.percentile y np.mean para evitar los sesgos de los promedios
        w_total_p95 = np.percentile(self.tiempos_ciclo_total, 95) if self.tiempos_ciclo_total else 0.0
        t_espera_rest_avg = np.mean(self.tiempos_espera_repartidor) if self.tiempos_espera_repartidor else 0.0
        t_mostrador_p95 = np.percentile(self.tiempos_comida_mostrador, 95) if self.tiempos_comida_mostrador else 0.0
        rho_rep_avg = np.mean(self.utilizacion_flota) if self.utilizacion_flota else 0.0

        return {
            "W_total_p95_min": round(w_total_p95, 2),
            "T_espera_rest_avg_min": round(t_espera_rest_avg, 2),
            "T_mostrador_p95_min": round(t_mostrador_p95, 2),
            "P_canc_porcentaje": round(tasa_cancelacion, 2),
            "Rho_rep_avg_porcentaje": round(rho_rep_avg, 2)
        }

    def exportar_json(self, ruta_archivo: str = "datos/simulation_results.json"):
        """Guarda los resultados matemáticos en el archivo JSON exigido por la rúbrica."""
        kpis = self.calcular_kpis()
        
        # Aseguramos que la carpeta "datos" exista antes de guardar
        Path(ruta_archivo).parent.mkdir(parents=True, exist_ok=True)
        
        with open(ruta_archivo, "w", encoding="utf-8") as f:
            json.dump(kpis, f, indent=4)
        
        print(f"Métricas extraídas exitosamente. Resultados guardados en: {ruta_archivo}")

if __name__ == "__main__":
    # Prueba unitaria para validar que numpy y el exportador funcionan
    recolector = MetricsCollector()
    
    # Simulamos 3 pedidos ingresando datos falsos de prueba
    recolector.registrar_pedido_completado(0, 15, 12, 30) # Repartidor esperó 3 min
    recolector.registrar_pedido_completado(10, 30, 35, 45) # Comida esperó 5 min
    recolector.registrar_cancelacion() # Cliente se hartó
    
    recolector.registrar_utilizacion_flota(80.5)
    recolector.registrar_utilizacion_flota(85.0)
    
    # Exportamos para ver si crea el archivo
    recolector.exportar_json()