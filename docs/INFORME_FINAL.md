### 2.1 Dinámica del Sistema y Modelo Conceptual DES

El gemelo digital opera como un modelo de **Simulación de Eventos Discretos (DES)** implementado en Python sobre la librería `SimPy`, simulando un ciclo operativo continuo de **24 horas (1.440 minutos)**. El reloj de simulación salta estocásticamente entre eventos atómicos discretos sin avance a paso fijo, lo que permite resolver cerca de 1.890 pedidos diarios y la interacción de hasta 100 repartidores en 2 a 4 segundos de cómputo en CPU.

#### 2.1.1 Entidades del Dominio y sus Atributos
* **`Order` (Pedido):** Entidad pasiva conducida a través de las etapas del servicio. Posee identificador único, restaurante asignado ($r \in \{0, \dots, 9\}$), coordenadas del cliente dentro del cuadrante urbano de $6 \times 6\text{ km}$, distancia vial con sinuosidad urbana ($\tau = 1.25$), tiempo de cocción asignado ($T_{\text{cocina}} \sim \text{LogNormal}(\mu_{\ln}=2.85, \sigma_{\ln}=0.35)$), marca de tiempo de despacho predictivo ($t_{\text{despacho}}$), umbral de impaciencia ($T_{\text{canc}} \sim \text{Weibull}(k=2.4, \lambda_w=40\text{ min})$) y estados discretos.
* **`Courier` (Repartidor):** Entidad activa de la flota crowdsourcing. Modela posición espacial $(x, y)$, nivel de batería $[0\%, 100\%]$ con drenaje activo de $0.15\%/\text{min}$ en movimiento y $0.05\%/\text{min}$ en espera, marca temporal de login ($t_{\text{login}}$) y límite operativo de turno ($T_{\text{turno}} \le 360\text{ min}$).
* **`KitchenNetwork` (Red de Cocinas):** Agrupa 10 restaurantes metropolitanos con capacidades heterogéneas ($k_r \in [3, 6]$ fogones simultáneos), totalizando una cota física rígida de **47 fogones en la red**.
* **`CourierPool` (Pool Dinámico de Flota):** Gestiona la oferta conectada $c(t)$, regulada mediante un proceso de arribo NHPP ($\lambda_{\text{login}}(t)$) con desconexión al término de la jornada.

#### 2.1.2 Recursos de Contención, Disciplinas de Cola y Límites Físicos (C6/C7)
* **Contención Culinaria (C6):** Cada restaurante modela sus puestos de cocción como un recurso multicanal `simpy.Resource(env, capacity=k_r)` con disciplina FIFO. La capacidad máxima de producción teórica de la red es $\lambda_{\text{max}} = 47 / 18.5 \approx 2.54\text{ ped/min}$.
* **Contención de Flota (C6/C7):** Los repartidores no son empleados fijos sino actores autónomos ($C7$). El sistema aplica dos filtros físicos duros ($C6$):
  1. *Filtro Preventivo de Batería:* Se evalúa que $\text{Bat}_{\text{actual}} - \Delta \text{Bat}_{\text{est}} \ge 15\%$, donde $\Delta \text{Bat}_{\text{est}} = (t_{\text{viaje\_local}} + t_{\text{viaje\_cliente}}) \times 0.15\% + t_{\text{espera}} \times 0.05\%$.
  2. *Límite Operativo de Fatiga (360 min):* Se aplica flexibilidad de cierre de entrega; si el conductor cumple 6 horas en ruta, culmina la entrega en curso y ejecuta inmediatamente su desconexión forzada.
* **Contención de Software TI (C6):** En el sistema real contenerizado, el acceso a PostgreSQL 15 está restringido a 30 conexiones simultáneas (`QueuePool` con `pool_size=20`, `max_overflow=10`).

#### 2.1.3 Políticas de Despacho Bajo Patrón Strategy
1. **`GreedyImmediatePolicy` (Línea Base):** Asigna el pedido al repartidor libre más cercano en el instante de su creación ($t_{\text{despacho}} = t_{\text{actual}}$). Provoca tiempos de espera ociosa de $10.6\text{ min}$ en el mostrador mientras la comida termina de hornearse.
2. **`PredictiveSynchronizedPolicy` (Propuesta Alternativa):** Calcula el momento óptimo de despacho:
   $$t_{\text{despacho}} = \max\left(t_{\text{actual}}, \; \text{ETA}_{\text{listo}} - t_{\text{viaje\_local}} - \Delta t_{\text{buffer}}\right)$$
   con $\Delta t_{\text{buffer}} = 2.5\text{ min}$. Dispone de un protocolo de escalamiento en dos fases:
   * *Fase 1:* Ensanchamiento de ventana de arribo $[\text{ETA} - 6\text{ min}, \text{ETA} + 8\text{ min}]$ ante rechazos en 45 s.
   * *Fase 2:* Conmutación a prioridad urgente anti-enfriamiento con incentivo tarifario del $+20\%$ si la comida sale a mostrador sin repartidor asignado.
   * *Protocolo Anti-Limbo:* Si transcurren 20 minutos en mostrador sin recolección, transiciona a `CANCELADO_SIN_REPARTIDOR`, protegiendo la inocuidad y asumiendo la merma comercial.

#### 2.1.4 Alineación de los 14 Eventos Atómicos con las Variables de Estado
El sistema actualiza de manera estricta el vector de variables de estado frente a cada evento discreto:

| # | Evento Atómico | Entidad Involucrada | Variables de Estado que Modifica |
| :-: | :--- | :--- | :--- |
| **1** | `LlegadaPedido` | `Order` | $N_{\text{ped}}(t) \leftarrow N_{\text{ped}} + 1$, $Q_{\text{cocina}}(t) \leftarrow Q_{\text{cocina}} + 1$ |
| **2** | `LoginRepartidor` | `Courier` | $c(t) \leftarrow c + 1$, $R_{\text{disp}}(t) \leftarrow R_{\text{disp}} + 1$ |
| **3** | `InicioCocina` | `Order` / `Kitchen` | $B_{\text{fogon}}(t) \leftarrow B_{\text{fogon}} + 1$, retardo Log-Normal |
| **4** | `FinCocina` | `Order` / `Kitchen` | $B_{\text{fogon}}(t) \leftarrow B_{\text{fogon}} - 1$, $Q_{\text{cocina}}(t) \leftarrow Q_{\text{cocina}} - 1$, $Q_{\text{mostrador}}(t) \leftarrow Q_{\text{mostrador}} + 1$ |
| **5** | `DisparoDespacho` | Plataforma | Emisión de oferta con ventana temporal de decisión de 45 s |
| **6** | `AceptacionRepartidor` | `Courier` | $R_{\text{disp}}(t) \leftarrow R_{\text{disp}} - 1$, $R_{\text{ocup}}(t) \leftarrow R_{\text{ocup}} + 1$ |
| **7** | `ExpiracionOferta` | Plataforma | Disparo de Fase 1 (ensanchar buffer) o Fase 2 (bono +20%) |
| **8** | `LlegadaARestaurante` | `Courier` | Si $t_{\text{arribo}} < t_{\text{listo}}$, espera ociosa; acumula $T_{\text{espera\_rest}}$ |
| **9** | `RecogidaPedido` | `Order` / `Courier` | $Q_{\text{mostrador}}(t) \leftarrow Q_{\text{mostrador}} - 1$; sella tiempo en mostrador |
| **10** | `EntregaFinal` | `Order` / `Courier` | $N_{\text{ped}}(t) \leftarrow N_{\text{ped}} - 1$, $R_{\text{ocup}}(t) \leftarrow R_{\text{ocup}} - 1$, evaluación de fin de turno |
| **11** | `CancelacionPorCliente` | `Order` | $N_{\text{canc\_cli}}(t) \leftarrow N_{\text{canc\_cli}} + 1$, $N_{\text{ped}}(t) \leftarrow N_{\text{ped}} - 1$ |
| **12** | `CancelacionSinRepartidor`| `Order` | $N_{\text{canc\_sin\_rep}}(t) \leftarrow N_{\text{canc\_sin\_rep}} + 1$, $Q_{\text{mostrador}}(t) \leftarrow Q_{\text{mostrador}} - 1$ |
| **13** | `IncidenciaTransito` | `Order` / `Courier` | $N_{\text{canc\_inc}}(t) \leftarrow N_{\text{canc\_inc}} + 1$, liberación de recursos |
| **14** | `LogoutRepartidor` | `Courier` | $c(t) \leftarrow c - 1$, $R_{\text{disp}}(t) \leftarrow R_{\text{disp}} - 1$ |


### 2.2 Subsanación Metodológica y Técnica de la Entrega Parcial 1

A partir de la retroalimentación técnica de la Entrega 1, se reestructuró y subsanó las observaciones emitidas por el docente, alcanzando coherencia estricta entre el marco analítico, el gemelo digital en SimPy y la documentación:

| Ítem | Observación Docente Recibida | Diagnóstico Técnico | Acción Concreta de Subsanación Implementada | Evidencia Verificable en Repositorio |
| :-: | :--- | :--- | :--- | :--- |
| **1** | *«Implementar la réplica M/M/c en SimPy.»* | La función `run_markovian_replica()` era únicamente un stub de firma sin lógica. | Se desarrolló en `simpy_engine.py` la simulación markoviana continua multicanal con llegadas $\text{Exp}(\lambda)$ y servicio $\text{Exp}(\mu)$. Para eludir el sesgo de censura, se implementó un calentamiento del 15% e integración de área bajo la curva $\int n(t)dt$ para $L, L_q, \rho$ y $P_0$. | `simulacion/simpy_engine.py` (función `run_markovian_replica`) |
| **2** | *«Ejecutar 30 réplicas con IC y comparar con Tabla 5.»* | No existía validación estadística rigurosa de convergencia. | Se automatizó en `analisis/contrast_analysis.py` la corrida de $N=30$ réplicas por franja horaria calculando intervalos de confianza del 95% ($t\text{-Student}$, $t_{0.975, 29} = 2.0452$). El error relativo frente a Erlang-C resultó estrictamente menor al $0.45\%$ en las 7 franjas. | `datos/mmc_contrast_results.json` y `analisis/test_contrast.ipynb` |
| **3** | *«Conectar al menos la política voraz con un pool de repartidores.»* | El modelo SimPy solo procesaba pedidos en cocina, sin flota móvil en ruta. | Se implementó la clase `CourierPool` en `entities.py`, gestionando estados, cinemática vial ($\tau=1.25$) y baterías. Tanto `GreedyImmediatePolicy` como `PredictiveSynchronizedPolicy` se conectaron punta a punta con el pool. | `simulacion/entities.py`, `policies.py` y `simpy_engine.py` |
| **4** | *«Cifras del problema sin fuente (16.5% canc, 16.2 min espera, 35% flota).»* | Se enunciaban cifras operativas como hechos consumados sin respaldo empírico. | Se reformuló el planteamiento del problema declarando formalmente dichas métricas como la **hipótesis del escenario de línea base no optimizado** sobre el cual se evalúa la mejora. | Sección 3.3.1 y 3.5.4 de `docs/Planteamiento_Proyecto.md` |
| **5** | *«Citas no comprobables (FDA no fija 20 min, OIT no fija 6 h).»* | Atribución incorrecta de normativas a políticas internas del negocio. | Se retiraron las atribuciones espurias de la FDA y la OIT. Se aclaró que los 20 min corresponden a un SLA de calidad de la app y las 6 h a política de fatiga. Se depuró la bibliografía a **9 fuentes académicas indexadas**. | `docs/Fuentes.md` y archivo de subsanación |
| **6** | *«C6: El límite de 6 h es política; usen un límite medible como fogones o BD.»* | El límite de 6 h no calificaba como cota física insuperable del sistema. | Se adoptaron como cotas duras ($C6$): (a) los **47 fogones físicos instalados** en los 10 restaurantes ($\lambda_{\text{max}} = 2.54\text{ ped/min}$), (b) el pool acotado de **30 conexiones simultáneas** a PostgreSQL en FastAPI, y (c) la batería del móvil en $[0, 100\%]$ con corte en 15%. | Sección 3.2.5 y código en `entities.py` y `database.py` |
| **7** | *«Inconsistencia: pág 10 define 14 eventos, tabla pág 14 tiene 12.»* | Desalineación entre la narrativa y la tabla relacional de variables de estado. | Se formalizó la variable de ocupación de cocina $B_{\text{fogon}}(t)$ y se alinearon exactamente los **14 eventos discretos** 1 a 1 entre la descripción textual y la matriz de transiciones. | Sección 3.6.4 y Tabla 4 en `docs/Planteamiento_Proyecto.md` |
| **8** | *«Locust no calibra cocina ni velocidad; separar datos TI de logísticos.»* | Confusión metodológica sobre el alcance del generador sintético Locust. | Se desacopló el plan de datos: Locust instrumenta exclusivamente latencias HTTP y CPU/RAM de la API; mientras que las distribuciones culinarias y viales se alimentan de literatura de delivery urbano. | Sección 3.8.2 en planes de acción |
| **9** | *«Redacción no técnica y anexo de IA sin estructura de tabla por uso.»* | Tono subjetivo y declaración de IA genérica sin detalle operativo. | Se neutralizó la redacción a estilo científico en tercera persona, se unificó la citación en norma APA 7.ª edición y se construyó la matriz de uso de IA detallando herramienta, prompt y validación humana. | Tabla de Uso de IA y reporte bibliográfico |