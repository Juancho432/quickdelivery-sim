import math

class QueueingModelMMC:
    """
    Modelo analítico M/M/c basado en la Fórmula C de Erlang.
    Utilizado para el contraste numérico contra el gemelo digital en SimPy.
    """
    def __init__(self, lambda_rate: float, mu_rate: float, c_servers: int):
        self.lambda_rate = lambda_rate
        self.mu_rate = mu_rate
        self.c = c_servers
        
        # Factor de utilización del sistema (rho)
        self.rho = self.lambda_rate / (self.c * self.mu_rate)
        
        if self.rho >= 1.0:
            raise ValueError(f"Sistema inestable: rho = {self.rho:.2f} (debe ser estrictamente < 1 para M/M/c)")

    def calculate_p0(self) -> float:
        """Calcula la probabilidad de que el sistema esté totalmente vacío (P0)."""
        sum_n = sum(((self.c * self.rho) ** n) / math.factorial(n) for n in range(self.c))
        term_c = ((self.c * self.rho) ** self.c) / (math.factorial(self.c) * (1 - self.rho))
        return 1.0 / (sum_n + term_c)

    def calculate_pw(self) -> float:
        """Calcula la probabilidad de tener que esperar en cola (Fórmula C de Erlang)."""
        p0 = self.calculate_p0()
        return (((self.c * self.rho) ** self.c) / (math.factorial(self.c) * (1 - self.rho))) * p0

    def calculate_metrics(self) -> dict:
        """
        Calcula y retorna todas las métricas operativas del sistema 
        aplicando las ecuaciones de Erlang y la Ley de Little.
        """
        pw = self.calculate_pw()
        
        # Longitud de la cola (Lq)
        l_q = (pw * self.rho) / (1 - self.rho)
        
        # Tiempo en cola (Wq) y tiempo total (W) vía Ley de Little
        w_q = l_q / self.lambda_rate
        w = w_q + (1 / self.mu_rate)
        
        # Longitud total del sistema (L)
        l = self.lambda_rate * w
        
        return {
            "rho": self.rho,
            "P0": self.calculate_p0(),
            "Pw": pw,
            "Lq": l_q,
            "Wq": w_q,
            "W": w,
            "L": l
        }

if __name__ == "__main__":
    # Prueba rápida unitaria del modelo
    try:
        modelo = QueueingModelMMC(lambda_rate=2.0, mu_rate=0.5, c_servers=5)
        metricas = modelo.calculate_metrics()
        
        print("--- Contraste Analítico M/M/c ---")
        for k, v in metricas.items():
            print(f"{k}: {v:.4f}")
    except ValueError as e:
        print(f"Error de validación: {e}")