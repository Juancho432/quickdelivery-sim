### 3.8 Parámetros, Distribuciones y Plan de Recolección de Datos

Para garantizar la fidelidad estocástica del gemelo digital y evitar las limitaciones de la distribución exponencial plana, el modelo adopta las siguientes distribuciones:

**Tabla Técnica de Variables Aleatorias**

* **Tiempo de Preparación en Cocina ($T_{\text{cocina}}$):** Distribución Log-Normal con $\mu_{\ln}=2.85$ y $\sigma_{\ln}=0.35$ (media $\approx 18.5$ min). **Fuente:** DoorDash Engineering (2020) y Alnaggar et al. (2021). **Justificación:** Garantiza tiempos estrictamente positivos y captura la "cola larga" de demoras en platos complejos.
* **Impaciencia del Cliente ($T_{\text{canc}}$):** Distribución Weibull con $k=2.4$ y $\lambda_w=40$ min. **Fuente:** Bai et al. (2019). **Justificación:** El parámetro $k > 1$ modela una tasa de riesgo creciente, reflejando cómo la frustración humana se acelera tras superar los 35 minutos.
* **Velocidad de Desplazamiento ($V_{\text{rep}}$):** Normal Truncada en $[8, 25]$ km/h con $\mu=18$ km/h y $\sigma=3$ km/h. **Fuente:** Dablanc et al. (2018). **Justificación:** Representa la velocidad media en tráfico urbano, acotando el rango para impedir la generación de velocidades negativas.
* **Distancia Cinemática Efectiva ($d_{\text{vial}}$):** Distancia Manhattan con factor de sinuosidad $\tau = 1.25$. **Fuente:** Boeing (2019) y Ballou et al. (2002). **Justificación:** Incorpora un 25% de recorrido extra por el sentido de las vías y desvíos urbanos.
* **Llegada de Pedidos ($\lambda_{\text{pedidos}}(t)$):** Proceso de Poisson No Homogéneo (NHPP). **Fuente:** Deliverect Industry Insights (2023). **Justificación:** Captura la saturación severa en picos de almuerzo ($2.70$ ped/min) y cena ($3.30$ ped/min).

**Plan de Recolección de Datos para Entrega 2**

1. **Entorno Simulado (SimPy):** La clase `MetricsCollector` capturará eventos estocásticos y calculará percentiles $p_{95}$ y $p_{99}$ con `numpy`, exportando a `datos/simulation_results.json`.
2. **Entorno Real (API REST):** Mediante *middleware* en FastAPI y la librería `psutil`, se medirán las latencias de los endpoints, las tasas de llegada reales (pedidos procesados por segundo), y el uso de CPU/RAM.
3. **Escenario de Carga (Locust):** Las mediciones se realizarán inyectando un escenario de estrés concurrente simulando el "Pico de Cena" (más de 100 usuarios virtuales concurrentes emitiendo órdenes continuas durante 5 minutos), exportando la telemetría a `datos/telemetry_log.csv`.

### 3.10 Diseño Preliminar de Clases POO

El diseño arquitectónico del simulador desacopla las entidades del motor de eventos, utilizando el patrón *Strategy* para las políticas de decisión y estableciendo interfaces claras para la futura integración de los Módulos II, III y IV.

```mermaid
classDiagram
    %% Componentes Base (Módulo I)
    class Order {
        <>
        +status: str
        +created_at: float
    }
    class Courier {
        <>
        +battery: float
        +state: str
    }
    class KitchenNetwork {
        <>
        +stoves: simpy.Resource
    }
    
    %% Motor y Estadísticas
    class SimpyEngine {
        <>
        +env: simpy.Environment
        +run_24h()
    }
    class MetricsCollector {
        <>
        +calculate_percentiles()
    }

    %% Patrón Strategy para Políticas
    class DispatchPolicy {
        <>
        +assign_order(order, couriers)
    }
    class GreedyImmediatePolicy {
        +assign_order(order, couriers)
    }
    class PredictiveSynchronizedPolicy {
        +assign_order(order, couriers)
    }
    
    %% Conexiones Futuras Exigidas (Módulos II, III, IV)
    class RealDataSource {
        <>
        +fetch_latencies()
    }
    class BayesianEstimator {
        <>
        +calibrate_parameters()
    }
    class SurrogateModel {
        <>
        +predict_limits()
    }
    class MesaAgentBridge {
        <>
        +sync_autonomous_agents()
    }

    %% Relaciones
    DispatchPolicy <|.. GreedyImmediatePolicy
    DispatchPolicy <|.. PredictiveSynchronizedPolicy
    SimpyEngine --> Order : spawns
    SimpyEngine --> Courier : manages
    SimpyEngine --> KitchenNetwork : allocates
    SimpyEngine --> DispatchPolicy : executes
    SimpyEngine --> MetricsCollector : logs events
    
    %% Relaciones Futuras
    RealDataSource ..> SimpyEngine : injects empirical delays
    BayesianEstimator ..> SimpyEngine : updates priors
    SurrogateModel ..> SimpyEngine : bounds physical limits
    MesaAgentBridge ..> Courier : converts to ABM Agent
