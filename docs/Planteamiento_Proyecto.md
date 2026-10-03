### 3.8 Parámetros, Distribuciones y Plan de Recolección de Datos

Para garantizar la fidelidad estocástica del gemelo digital y evitar las limitaciones de la distribución exponencial, el modelo adopta las siguientes distribuciones fundamentadas en la literatura logística:

**Tabla Técnica de Variables Aleatorias**

* **Tiempo de Preparación en Cocina ($T_{\text{cocina}}$):** Se modela mediante una distribución Log-Normal con $\mu_{\ln}=2.85$ y $\sigma_{\ln}=0.35$ (media física de $\approx 18.5\text{ min}$). Esta distribución garantiza tiempos estrictamente positivos y captura la asimetría hacia la derecha (*positive skewness*), reflejando que los procesos culinarios presentan una "cola larga" de demoras en platos complejos u horas pico.
* **Impaciencia y Abandono del Cliente ($T_{\text{canc}}$):** Se modela con una distribución Weibull con $k=2.4$ y $\lambda_w=40\text{ min}$. El parámetro de forma $k > 1$ define una tasa instantánea de riesgo creciente: el cliente tolera pacientemente los primeros minutos, pero su frustración escala exponencialmente al superar los 35-45 minutos.
* **Velocidad de Desplazamiento Urbano ($V_{\text{rep}}$):** Se define como una Normal Truncada en $[8, 25]\text{ km/h}$ con $\mu=18\text{ km/h}$ y $\sigma=3\text{ km/h}$. Representa la velocidad media de motocicletas sorteando congestión, acotando el rango para impedir velocidades negativas o irreales.
* **Distancia Cinemática Efectiva ($d_{\text{vial}}$):** Se utiliza la distancia ortogonal de Manhattan multiplicada por un factor de sinuosidad urbana $\tau = 1.25$. Esto incorpora un 25% de recorrido excedente para compensar el sentido de las vías, desvíos y curvas de la trama urbana.
* **Llegada de Pedidos y Oferta de Repartidores ($\lambda_{\text{pedidos}}(t)$ y $\lambda_{\text{login}}(t)$):** Modelados como Procesos de Poisson No Homogéneos (NHPP). La tasa de arribo varía dinámicamente, capturando la saturación severa en picos de almuerzo ($2.70\text{ ped/min}$) y cena ($3.30\text{ ped/min}$).

**Plan de Recolección de Datos**

1. **Entorno Simulado (SimPy):** Se integrará una clase `MetricsCollector` para capturar eventos estocásticos, calcular percentiles $p_{95}$ y $p_{99}$ con `numpy`, y exportar los datos a `datos/simulation_results.json`.
2. **Entorno Real (API REST):** Un *middleware* en FastAPI interceptará el tráfico HTTP inyectado por pruebas Locust. Se capturará latencia y uso de CPU/RAM (vía `psutil`), exportando en tiempo real a `datos/telemetry_log.csv`.

### 3.10 Diseño de Clases POO y Patrón Strategy

Para desacoplar la lógica de emparejamiento de las entidades del sistema, se implementa el patrón de diseño conductual *Strategy*. Esto permite conmutar dinámicamente entre la asignación voraz y el despacho sincronizado predictivo sin alterar el motor de simulación.

```mermaid
classDiagram
    class DispatchPolicy {
        <>
        +assign_order(order: Order, couriers: List~Courier~) Courier
    }

    class GreedyImmediatePolicy {
        +assign_order(order: Order, couriers: List~Courier~) Courier
    }

    class PredictiveSynchronizedPolicy {
        -buffer_minutes: float
        +calculate_eta(order: Order) float
        +assign_order(order: Order, couriers: List~Courier~) Courier
    }

    DispatchPolicy <|.. GreedyImmediatePolicy
    DispatchPolicy <|.. PredictiveSynchronizedPolicy
