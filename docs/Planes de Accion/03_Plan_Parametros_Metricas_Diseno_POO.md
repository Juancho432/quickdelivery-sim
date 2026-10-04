# PLAN DE ACCIÓN 03: PARÁMETROS, MÉTRICAS Y DISEÑO POO
## Módulos del Documento: 3.8 Parámetros, Distribuciones y Plan de Datos, 3.9 Métricas de Desempeño (KPIs), 3.10 Diseño de Clases POO (Paso 8)
## Criterios de Rúbrica Asociados: R6 (0.4), R7 (0.3), R9 (0.5 parcial)

---

### 1. Objetivos del Plan
Establecer las distribuciones de probabilidad rigurosamente fundamentadas para cada parámetro estocástico del modelo de pedidos a domicilio, formular el plan de telemetría y recolección para la Entrega 2, definir los 4 a 6 KPIs operacionales (incluyendo percentiles $p95/p99$), y diseñar la arquitectura orientada a objetos (POO) mediante patrones de diseño (Strategy) con puntos de extensión explícitos para los módulos futuros (Bayesiano, Subrogado y Multiagente).

---

### 2. Estructura y Contenidos Detallados por Sección

#### 2.1 Parámetros, Distribuciones y Plan de Datos (Sección 3.8 & Criterio R6)
* **Tabla de Parámetros de Entrada:**
  * *1. Tiempo entre llegadas de pedidos ($T_{arr}$):*
    * Distribución: Exponencial a trozos ($\text{Exp}(\lambda(t))$) en franjas horarias sobre 24h (NHPP).
    * Valores calibrados: Madrugada $0.15\text{ ped/min}$ ($\rho=6\%$), Desayuno $1.00\text{ ped/min}$ ($\rho=39\%$), Valle Mañana $0.80\text{ ped/min}$ ($\rho=31\%$), Pico Almuerzo $2.70\text{ ped/min}$ ($\rho=106\%$), Valle Tarde $1.20\text{ ped/min}$ ($\rho=47\%$), Pico Cena $3.30\text{ ped/min}$ ($\rho=130\%$, pico máximo diario), Cierre $0.50\text{ ped/min}$ ($\rho=20\%$). Total día: $\approx 1.890$ pedidos.
    * Justificación y Fuente: Alternancia realista entre períodos de holgura y sobrecarga transitoria en cocina frente a capacidad nominal de $2.54\text{ ped/min}$ (DoorDash Trends, 2023).
  * *2. Tiempo de preparación en cocina ($T_{coc}$):*
    * Distribución: Log-Normal ($\text{LogNormal}(\mu_{ln}=2.85, \sigma_{ln}=0.35)$), con media $\approx 18.5\text{ min}$ y desviación $\approx 6.8\text{ min}$.
    * Justificación y Fuente: Tareas culinarias humanas asimétricas estrictamente positivas (DoorDash Engineering, 2020).
  * *3. Distancia de viaje al cliente ($D_{km}$):*
    * Distribución: Gamma ($\text{Gamma}(\alpha=3.0, \beta=1.2)$), media $\approx 2.5\text{ km}$, rango $[0.8, 6.0]\text{ km}$.
    * Justificación y Fuente: Densidad espacial de zonas residenciales y restaurantes urbanos (OpenStreetMap Analytics, 2023).
  * *4. Velocidad efectiva de repartidor ($V_{rep}$):*
    * Distribución: Truncada Normal ($\mathcal{N}(\mu=18\text{ km/h}, \sigma=3\text{ km/h})$, truncada en $[8, 25]\text{ km/h}$).
    * Justificación: Velocidades de motocicletas y bicicletas con tráfico semafórico mixto (Dablanc et al., 2018).
  * *5. Paciencia máxima del cliente antes de cancelar ($T_{canc}$):*
    * Distribución: Weibull ($\text{Weibull}(k=2.4, \lambda_w=40\text{ min})$).
    * Justificación: Tasa de riesgo instantáneo de cancelación creciente con la demora (Bai et al., 2019).
  * *6. Permanencia máxima continua por repartidor ($T_{turno}$):*
    * Distribución: Truncada superiormente en $T_{max} = 6.0\text{ horas}$ ($360\text{ min}$).
    * Justificación: Límite por fatiga psicomotriz en conducción de dos ruedas (OIT/ILO, 2021; Gregory, 2021).
  * *7. Dinámica de arribo de repartidores ($\lambda_{\text{login}}(t)$ — NHPP de Flota):*
    * Distribución: NHPP correlacionado con demanda: Madrugada ($4-8\text{ couriers}$), Desayuno ($20-35$), Valle Mañana ($35-50$), Pico Almuerzo ($65-80$), Valle Tarde ($50-65$), Pico Cena ($80-100$), Cierre ($20-35$).
    * Justificación: Oferta descentralizada crowdsourcing atraída por incentivos tarifarios en picos.
  * *8. Drenaje de batería de smartphone:*
    * Tasas: $0.15\%/\text{min}$ en viaje activo con GPS a 1 Hz; $0.05\%/\text{min}$ en mostrador/espera. Filtro preventivo antes de ofertar: $\text{Bat}_{\text{actual}} - \Delta \text{Bat}_{\text{est}} \ge 15\%$ (Carroll & Heiser, 2010).
  * *9. Tiempo de enfriamiento en mostrador y merma térmica:*
    * Umbral de degradación: Si $t_{\text{mostrador}} > 6\text{ min}$, la tasa de riesgo de cancelación del cliente se acelera en $+50\%$. Si $t_{\text{mostrador}} \ge 20\text{ min}$, la orden transita a `CANCELADO_SIN_REPARTIDOR` (FDA Food Code, 2022).

#### 2.2 Métricas de Desempeño / KPIs (Sección 3.9 & Criterio R7)
Se formulan 6 métricas cuantificables vinculadas directamente a las preguntas de decisión:
1. **$W_{total\_p95}$ — Percentil 95 del Tiempo Total de Ciclo del Pedido:**
   * *Fórmula:* $P_{95}(\{ t_{entrega}^{(i)} - t_{arr}^{(i)} \})$
   * *Unidad:* Minutos ($min$).
   * *Umbral Aceptable:* $W_{total\_p95} \le 40\text{ min}$ en 24h.
   * *Pregunta que responde:* Calidad global percibida por el cliente y SLA en picos.
2. **$T_{espera\_rest}$ — Tiempo Promedio Ocioso del Repartidor en Restaurante:**
   * *Fórmula:* $T_{espera\_rest} = \frac{1}{N_{recogidos}} \sum_{i=1}^{N_{recogidos}} \max(0, t_{ready}^{(i)} - t_{arribo\_rep}^{(i)})$
   * *Unidad:* Minutos ($min$).
   * *Umbral Aceptable:* $T_{espera\_rest} \le 3.5\text{ min}$ (con política voraz actual es $\approx 16.2\text{ min}$).
   * *Pregunta que responde:* Pregunta de Decisión 1 (impacto de la sincronización cocina-despacho).
3. **$\rho_{rep}(t)$ — Utilización Efectiva de Repartidores Conectados:**
   * *Fórmula:* $\rho(t) = \frac{R_{ocup}(t)}{c(t)}$
   * *Unidad:* Porcentaje ($\%$).
   * *Umbral Aceptable:* $75\% \le \rho \le 85\%$ durante picos de almuerzo y cena.
   * *Pregunta que responde:* Pregunta de Decisión 2 (dimensionamiento de incentivos dinámicos).
4. **$P_{canc}$ — Tasa Global de Cancelación de Pedidos:**
   * *Fórmula:* $P_{canc} = \frac{N_{canc\_total}}{N_{ped\_total}} \times 100\%$ (desagregada en cliente, sin repartidor e incidencia).
   * *Unidad:* Porcentaje ($\%$).
   * *Umbral Aceptable:* $P_{canc} < 3.0\%$ en la jornada de 24h.
   * *Pregunta que responde:* Retención de ingresos, merma culinaria y satisfacción de clientes.
5. **$T_{\text{mostrador\_p95}}$ — Percentil 95 del Tiempo de Enfriamiento en Mostrador:**
   * *Fórmula:* $P_{95}(\{ t_{\text{recogida}}^{(i)} - t_{\text{ready}}^{(i)} \})$
   * *Unidad:* Minutos ($min$).
   * *Umbral Aceptable:* $T_{\text{mostrador\_p95}} \le 5.0\text{ min}$.
   * *Pregunta que responde:* Pregunta de Decisión 4 (calibración del buffer óptimo $\Delta t_{\text{buffer}}$).
6. **$T_{lat\_api\_p99}$ — Percentil 99 de Latencia del Endpoint de Rastreo:**
   * *Fórmula:* $P_{99}(\{ t_{resp\_tracking}^{(j)} \})$
   * *Unidad:* Milisegundos ($ms$).
   * *Umbral Aceptable:* $T_{lat\_api\_p99} \le 180\text{ ms}$ bajo alta concurrencia.
   * *Pregunta que responde:* Pregunta de Decisión 3 (límite físico duro de infraestructura de software).
   * *Evidencia Empírica Obtenida:* Validado en las corridas de Locust y registrado en `datos/telemetry_log.csv` y `datos/locust_stats_stats.csv`, donde el percentil $p99$ se mantiene en valores sub-milimétricos / $< 20\text{ ms}$ en red local con $0.00\%$ errores.

#### 2.3 Diseño Preliminar de Clases POO (Sección 3.10 & Criterio R9)
* **Arquitectura de Dominio y Patrón Strategy (Exclusivo Opción 1):**
  * Clase Abstracta / Interfaz: `DispatchPolicy` con método `evaluate_dispatch(order, available_couriers, env_time) -> Optional[Courier]`.
  * Implementaciones concretas del patrón Strategy:
    * `GreedyImmediatePolicy`: Política actual de línea base. Despacha al repartidor libre más cercano inmediatamente tras la emisión del pedido, ignorando el estado de cocción del restaurante.
    * `PredictiveSynchronizedPolicy`: Política alternativa propuesta. Programa la oferta para $t_{\text{despacho}} = t_{\text{ready\_est}} - t_{\text{viaje}} + \Delta t_{\text{buffer}}$, emite broadcast a couriers con batería $\ge 15\%$, y ejecuta escalamiento dinámico en dos fases (ampliación de ventana $[-6, +8]\text{ min}$ y conmutación urgente con bono +20% si la comida sale a mostrador).
* **Componentes Nucleares del Diagrama de Clases (Mermaid `classDiagram`):**
  * `Order`: Entidad con atributos $id$, timestamps, estados (11 estados), tiempos de mostrador y flags de urgencia.
  * `Courier`: Recurso con posición $(x,y)$, estado (`IDLE`, `OFFER_RECEIVED`, `TRANSIT_KITCHEN`, `WAITING_COUNTER`, `TRANSIT_CLIENT`), batería, tiempo acumulado de turno y filtro preventivo.
  * `Kitchen`: Recurso multi-servidor (`simpy.Resource(capacity=k_r)`) con $k_r \in [3, 6]$ fogones por restaurante.
  * `CourierPool`: Contenedor y gestor del recurso finito SimPy para la flota variable.
  * `SimulationEngine`: Orquestador principal del entorno SimPy (`simpy.Environment`) gobernando la jornada continua de 24 horas.
  * `MetricsCollector`: Observador que registra eventos, calcula estadísticas agregadas y genera percentiles ($p95, p99$).
* **Puntos de Extensión Explícitos para Módulos Futuros:**
  * *Módulo II (Telemetría & Datos Reales):* Interfaz `ITelemetryDataSource` para alimentar el simulador con trazas reales de Locust y latencias medidas en la API REST de FastAPI.
  * *Módulo III (Estimación Bayesiana & PINN):* Clase `BayesianParamCalibrator` (PyMC) que inyecta distribuciones a posteriori en `SimulationEngine`, y clase `SurrogateLatencyPredictor` que predice tiempos respetando cotas físicas de CPU.
  * *Módulo IV (Multiagente Mesa):* Adaptador `MesaAgentBridge` donde cada `Courier` y cliente se modelan como agentes autónomos con funciones de recompensa, reglas de impaciencia y aprendizaje por refuerzo.

---

### 3. Criterios de Aceptación y Verificación
- [ ] Ninguna distribución de tiempo continuo es asignada como exponencial de forma arbitraria sin justificación formal.
- [ ] El plan de datos detalla herramientas reales (Locust, psutil, middleware) y tipos de carga.
- [ ] Se especifican exactamente 6 métricas cuantificables y al menos dos son percentiles ($p95$ y $p99$).
- [ ] El diagrama de clases implementa formalmente el patrón Strategy para las dos políticas de la Opción 1 (Voraz vs. Sincronizada).
- [ ] Se explicitan los puntos de conexión futuros para Módulos II, III y IV.

