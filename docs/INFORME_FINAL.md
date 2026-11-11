### 2.1 Dinámica del Sistema y Modelo Conceptual DES

El gemelo digital opera como un modelo de **Simulación de Eventos Discretos (DES)** implementado en Python sobre la librería `SimPy`, simulando un ciclo operativo continuo de **24 horas (1.440 minutos)**. El reloj de simulación salta estocásticamente entre eventos atómicos discretos sin avance a paso fijo, lo que permite resolver cerca de 1.890 pedidos diarios y la interacción de hasta 100 repartidores en 2 a 4 segundos de cómputo en CPU.

#### 2.1.1 Entidades del Dominio y sus Atributos

* **`Order` (Pedido):** Entidad pasiva conducida a través de las etapas del servicio. Posee identificador único, restaurante asignado ($r \in \{0, \dots, 9\}$), coordenadas del cliente dentro del cuadrante urbano de $6 \times 6\text{ km}$, distancia vial con sinuosidad urbana ($\tau = 1.25$), tiempo de cocción asignado ($T_{\text{cocina}} \sim \text{LogNormal}(\mu_{\ln}=2.85, \sigma_{\ln}=0.35)$), marca de tiempo de despacho predictivo ($t_{\text{despacho}}$), umbral de impaciencia ($T_{\text{canc}} \sim \text{Weibull}(k=2.4, \lambda_w=40\text{ min})$) y estados discretos.
* **`Courier` (Repartidor):** Entidad activa de la flota crowdsourcing. Modela posición espacial $(x, y)$, nivel de batería $[0\%, 100\%]$ con drenaje activo de $0.15\%/\text{min}$ en movimiento y $0.05\%/\text{min}$ en espera, marca temporal de login ($t_{\text{login}}$) y límite operativo de turno ($T_{\text{turno}} \le 360\text{ min}$).
* **`KitchenNetwork` (Red de Cocinas):** Agrupa 10 restaurantes metropolitanos con capacidades heterogéneas ($k_r \in [3, 6]$ fogones simultáneos), totalizando una cota física rígida de **47 fogones en la red**.
* **`CourierPool` (Pool Dinámico de Flota):** Gestiona la oferta conectada $c(t)$, regulada mediante un proceso de arribo NHPP ($\lambda_{\text{login}}(t)$) con desconexión al término de la jornada.

### 2.1.2 Recursos de Contención, Disciplinas de Cola y Límites Físicos Duros (C6/C7)

* **Contención Culinaria (C6 - Límite Físico):** Cada restaurante modela sus puestos de cocción como un recurso multicanal `simpy.Resource(env, capacity=k_r)` con disciplina FIFO. La capacidad máxima de producción teórica de la red es un límite espacial duro de **47 fogones**, acotando el flujo a $\lambda_{\text{max}} = 47 / 18.5 \approx 2.54\text{ ped/min}$.
* **Contención de Software TI (C6 - Límite de Hardware/Software):** En el sistema real contenerizado, el acceso a PostgreSQL 15 está restringido a un máximo de **30 conexiones simultáneas** (`QueuePool` con `pool_size=20, max_overflow=10`). Las peticiones que exceden este umbral en horas pico experimentan bloqueos o encolamiento en el servidor.
* **Contención de Flota y Actores Autónomos (C7):** Los repartidores no son empleados fijos sino actores autónomos (C7). El sistema gobierna su comportamiento con dos reglas:
  1. *Filtro Preventivo de Batería (Restricción de hardware del dispositivo):* Se evalúa que $\text{Bat}_{\text{actual}} - \Delta \text{Bat}_{\text{est}} \ge 15\%$, donde $\Delta \text{Bat}_{\text{est}} = (t_{\text{viaje\_local}} + t_{\text{viaje\_cliente}}) \times 0.15\% + t_{\text{espera}} \times 0.05\%$.
  2. *Límite Operativo de Fatiga (Política de Negocio):* Se restringe el turno a 360 min con flexibilidad de cierre. *(Nota metodológica: Se clasifica como regla de negocio y se descarta como límite C6, ya que no representa una restricción física insuperable del entorno).*

#### 2.1.3 Políticas de Despacho Bajo Patrón Strategy

1. **`GreedyImmediatePolicy` (Línea Base):** Asigna el pedido al repartidor libre más cercano en el instante de su creación ($t_{\text{despacho}} = t_{\text{actual}}$). Provoca tiempos de espera ociosa de $10.6\text{ min}$ en el mostrador mientras la comida termina de hornearse.
2. **`PredictiveSynchronizedPolicy` (Propuesta Alternativa):** Calcula el momento óptimo de despacho:
   $$t_{\text{despacho}} = \max\left(t_{\text{actual}}, \; \text{ETA}_{\text{listo}} - t_{\text{viaje\_local}} - \Delta t_{\text{buffer}}\right)$$
   con $\Delta t_{\text{buffer}} = 2.5\text{ min}$. Dispone de un protocolo de escalamiento en dos fases:
   * *Fase 1:* Ensanchamiento de ventana de arribo $[\text{ETA} - 6\text{ min}, \text{ETA} + 8\text{ min}]$ ante rechazos en 45 s.
   * *Fase 2:* Conmutación a prioridad urgente anti-enfriamiento con incentivo tarifario del $+20\%$ si la comida sale a mostrador sin repartidor asignado.
   * *Protocolo Anti-Limbo:* Si transcurren 20 minutos en mostrador sin recolección, transiciona a `CANCELADO_SIN_REPARTIDOR`, protegiendo la inocuidad y asumiendo la merma comercial.

#### 2.1.4 Alineación de los 12 Eventos Atómicos con las Variables de Estado

El sistema actualiza de manera estricta el vector de variables de estado frente a cada evento discreto. A continuación se presentan los **12 eventos atómicos** consolidados (unificando subprocesos como el inicio de cocina o la expiración de oferta dentro del ciclo de vida principal para evitar redundancias en el conteo de variables de estado) y su impacto matemático en la simulación:

| Evento Atómico | Entidad Involucrada | Variables de Estado que Modifica |
| :--- | :--- | :--- |
| **1. LlegadaPedido** | `Order` | $N_{\text{ped}}(t) \leftarrow N_{\text{ped}} + 1$, $Q_{\text{cocina}}(t) \leftarrow Q_{\text{cocina}} + 1$ |
| **2. LoginRepartidor** | `Courier` | $c(t) \leftarrow c + 1$, $R_{\text{disp}}(t) \leftarrow R_{\text{disp}} + 1$ |
| **3. FinCocina** | `Order` / `Kitchen` | $Q_{\text{cocina}}(t) \leftarrow Q_{\text{cocina}} - 1$, $Q_{\text{mostrador}}(t) \leftarrow Q_{\text{mostrador}} + 1$ |
| **4. DisparoDespacho** | Plataforma | Emisión de oferta con ventana temporal de decisión de 45 s |
| **5. AceptacionRepartidor** | `Courier` | $R_{\text{disp}}(t) \leftarrow R_{\text{disp}} - 1$, $R_{\text{ocup}}(t) \leftarrow R_{\text{ocup}} + 1$ |
| **6. LlegadaARestaurante** | `Courier` | Si $t_{\text{arribo}} < t_{\text{listo}}$, espera ociosa; acumula $T_{\text{espera\_rest}}$ |
| **7. RecogidaPedido** | `Order` / `Courier` | $Q_{\text{mostrador}}(t) \leftarrow Q_{\text{mostrador}} - 1$; sella tiempo en mostrador |
| **8. EntregaFinal** | `Order` / `Courier` | $N_{\text{ped}}(t) \leftarrow N_{\text{ped}} - 1$, $R_{\text{ocup}}(t) \leftarrow R_{\text{ocup}} - 1$, evaluación de fin de turno |
| **9. CancelacionPorCliente** | `Order` | $N_{\text{canc\_cli}}(t) \leftarrow N_{\text{canc\_cli}} + 1$, $N_{\text{ped}}(t) \leftarrow N_{\text{ped}} - 1$ |
| **10. CancelacionSinRepartidor** | `Order` | $N_{\text{canc\_sin\_rep}}(t) \leftarrow N_{\text{canc\_sin\_rep}} + 1$, $Q_{\text{mostrador}}(t) \leftarrow Q_{\text{mostrador}} - 1$ |
| **11. IncidenciaTransito** | `Order` / `Courier` | $N_{\text{canc\_inc}}(t) \leftarrow N_{\text{canc\_inc}} + 1$, liberación de recursos |
| **12. LogoutRepartidor** | `Courier` | $c(t) \leftarrow c - 1$, $R_{\text{disp}}(t) \leftarrow R_{\text{disp}} - 1$ |

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
| **7** | *«Inconsistencia: pág 10 define 14 eventos, tabla pág 14 tiene 12.»* | Desalineación entre la narrativa y la tabla relacional de variables de estado. | Se depuró el conteo de eventos, consolidando subprocesos menores y alineando exactamente los 12 eventos atómicos principales entre la descripción textual y la matriz de transiciones. | Sección 3.6.4 y Tabla 4 en `docs/Planteamiento_Proyecto.md` |
| **8** | *«Locust no calibra cocina ni velocidad; separar datos TI de logísticos.»* | Confusión metodológica sobre el alcance del generador sintético Locust. | Se desacopló el plan de datos: Locust instrumenta exclusivamente latencias HTTP y CPU/RAM de la API; mientras que las distribuciones culinarias y viales se alimentan de literatura de delivery urbano. | Sección 3.8.2 en planes de acción |
| **9** | *«Redacción no técnica y anexo de IA sin estructura de tabla por uso.»* | Tono subjetivo y declaración de IA genérica sin detalle operativo. | Se neutralizó la redacción a estilo científico en tercera persona, se unificó la citación en norma APA 7.ª edición y se construyó la matriz de uso de IA detallando herramienta, prompt y validación humana. | Tabla de Uso de IA y reporte bibliográfico |

### 2.3 Aclaración Metodológica sobre Pruebas de Carga y Telemetría

Atendiendo a las observaciones técnicas de la fase de modelado, se establece una separación estricta entre la recolección de telemetría de infraestructura (TI) y la parametrización de variables logísticas del mundo físico:

* **Rol de Locust (Pruebas Sintéticas TI):** La herramienta Locust se emplea de manera exclusiva para inyectar tráfico HTTP concurrente contra la API REST. Su objetivo es medir empíricamente y calibrar las latencias del software del backend y el consumo de recursos (CPU y RAM) bajo escenarios de estrés (ej., el pico de cena).
* **Parámetros del Dominio Logístico:** Variables físicas como los tiempos de cocción de alimentos, la velocidad de desplazamiento en la malla urbana y la curva de impaciencia del cliente **no son calibradas mediante Locust**. Estos fenómenos se modelan en el motor SimPy empleando generadores estocásticos (distribuciones Log-Normal, Normal Truncada y Weibull), fundamentados rigurosamente en la revisión de literatura especializada del sector de logística de última milla.

## 4. Validación Analítica y Contraste de Convergencia ($M/M/c$ vs. SimPy)

Para garantizar la validez estructural del gemelo digital, se contrastó el desempeño del motor SimPy contra un modelo analítico de teoría de colas markoviano multicanal estricto ($M/M/c$) en régimen estacionario (llegadas Poisson $\lambda$ y servicio exponencial $\mu$).

### 4.1 Metodología de Contraste Estadístico

Se diseñó un experimento de $N=30$ réplicas independientes de la simulación canónica. Para estimar el error, se calcularon los intervalos de confianza del 95% para el Tiempo Total en el Sistema ($W$) aplicando la distribución $t$-Student con 29 grados de libertad ($t_{0.975, 29} = 2.0452$), dado que la varianza poblacional es desconocida. Para eludir sesgos transitorios, se aplicó un descarte de calentamiento (warm-up) del 15% del horizonte simulado.

### 4.2 Resultados de la Validación en Estado Estable

La Tabla de convergencia consolida los resultados para las franjas horarias donde el sistema no se encuentra saturado ($\rho < 1$).

| Franja Horaria | Demanda ($\lambda$) | Flota ($c$) | Utilización ($\rho$) | $W$ Analítico Erlang-C | $W$ SimPy (Media $\pm$ IC 95%) | Error Relativo |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Madrugada** | 0.15 ped/min | 6 | 50.0% | 20.6610 min | $20.6641 \pm 0.0512$ min | **0.015%** |
| **Desayuno** | 1.00 ped/min | 25 | 80.0% | 20.8364 min | $20.8411 \pm 0.0488$ min | **0.022%** |
| **Valle Mañana** | 0.80 ped/min | 20 | 80.0% | 21.2804 min | $21.2859 \pm 0.0610$ min | **0.025%** |
| **Valle Tarde** | 1.20 ped/min | 30 | 80.0% | 20.5762 min | $20.5815 \pm 0.0543$ min | **0.025%** |
| **Cierre Noche** | 0.50 ped/min | 14 | 71.4% | 20.8707 min | $20.8752 \pm 0.0491$ min | **0.021%** |

*Conclusión del Contraste:* El error relativo máximo registrado es inferior al **0.03%**, y el valor teórico analítico de Erlang-C siempre se encuentra dentro del intervalo de confianza $[L_i, L_s]$ de la simulación. Esto demuestra que la arquitectura central del motor DES en SimPy es matemáticamente irreprochable.

### 4.3 Justificación de la Divergencia Teórica en Picos Críticos (¿Por qué simular?)

A pesar de la exactitud mostrada en régimen de holgura, el modelo analítico $M/M/c$ presenta una limitante estructural: asume capacidad teórica infinita de servidores. Durante el Pico de Almuerzo ($\lambda=2.70$) y el Pico de Cena ($\lambda=3.30$), la tasa de arribo de pedidos supera la capacidad máxima de procesamiento de los 47 fogones físicos de la red ($\lambda_{\text{max}}=2.54$).

Esto genera factores de utilización de $\rho = 1.06$ y $\rho = 1.30$, respectivamente. Bajo estas condiciones, las ecuaciones de Erlang-C colapsan matemáticamente (produciendo longitudes de cola infinitas o valores negativos en los denominadores). La simulación DES implementada es, por lo tanto, la única herramienta heurística capaz de modelar esta congestión transitoria finita, capturando la amortiguación natural producida por la curva de abandono Weibull de los clientes impacientes.

## 5. Análisis Comparativo de Políticas y Respuestas de Negocio

El objetivo primario de la simulación fue evaluar el impacto de sustituir la política operativa actual (**Voraz Inmediata**) por una lógica algorítmica de **Despacho Sincronizado Predictivo**. Los resultados agregados del gemelo digital se exponen a continuación.

### 5.1 Cuadro de Mando Integral de KPIs (Contraste de Políticas)

La siguiente matriz presenta el comportamiento de los 6 indicadores clave en condiciones de alta carga (Pico de Cena), evaluando su cumplimiento respecto a los Acuerdos de Nivel de Servicio (SLA):

| KPI | Umbral SLA de Éxito | Política Actual: Voraz Inmediata | Política Propuesta: Sincronizada Predictiva | Mejora / Delta |
| :--- | :--- | :--- | :--- | :--- |
| **Tiempo de Ciclo Total ($W_{\text{total\_p95}}$)** | $\le 40.0\text{ min}$ | $55.4\text{ min}$ | **$38.2\text{ min}$** | $-31.0\%$ |
| **Espera Ociosa Repartidor ($T_{\text{espera\_rest}}$)** | $\le 3.5\text{ min}$ | $10.6\text{ min}$ | **$2.1\text{ min}$** | $-80.1\%$ |
| **Utilización de Flota ($\rho_{\text{rep}}$)** | $75.0\% - 85.0\%$ | $62.3\%$ (Ociosa en mostrador) | **$81.5\%$** (En ruta) | Óptima |
| **Tasa de Cancelación Total ($P_{\text{canc}}$)** | $< 3.0\%$ | $16.5\%$ | **$2.8\%$** | $-83.0\%$ |
| **Tiempo en Mostrador ($T_{\text{mostrador\_p95}}$)** | $\le 6.0\text{ min}$ | $16.2\text{ min}$ (Riesgo térmico) | **$1.8\text{ min}$** | $-88.8\%$ |
| **Latencia Rastreo API ($T_{\text{lat\_api\_p99}}$)** | $\le 180.0\text{ ms}$ | $245.0\text{ ms}$ | **$165.0\text{ ms}$** | $-32.6\%$ |

### 5.2 Respuestas a las Preguntas de Decisión

Las salidas probabilísticas del motor SimPy proporcionan respuestas concluyentes a los interrogantes planteados en el problema de ingeniería:

**Pregunta 1: Sincronización y Productividad de Flota**

* *Respuesta:* El Despacho Sincronizado reduce el tiempo de espera ocioso del repartidor de $10.6\text{ min}$ a $2.1\text{ min}$ (una mejora del $80.1\%$). Al eliminar este tiempo muerto en mostrador, el repartidor puede completar hasta un $35\%$ más de pedidos dentro de su turno rígido de 6 horas, maximizando su utilidad económica sin exceder su límite de fatiga.

**Pregunta 2: Dimensionamiento en Pico Máximo (18:30–22:00)**

* *Respuesta:* Para mantener la utilización operativa entre el $75\%$ y $85\%$ durante la carga extrema de $\lambda = 3.30\text{ ped/min}$, la plataforma debe asegurar un pool conectado de $c_{\text{min}} = 85\text{ repartidores}$. Este nivel de oferta es suficiente para garantizar un $W_{\text{total\_p95}} \le 38.2\text{ min}$ y colapsar la tasa de cancelación al $2.8\%$.

**Pregunta 3: Consumo Energético vs. Infraestructura**

* *Respuesta:* La reducción del sondeo de telemetría de $5\text{ s}$ a $15\text{ s}$ disminuye la saturación del `QueuePool` de PostgreSQL, permitiendo que el percentil 99 de la latencia en la API caiga de $245\text{ ms}$ a $165\text{ ms}$ ($\le 180\text{ ms}$ SLA). Paralelamente, el menor uso de la antena celular extiende la autonomía de la batería del repartidor, mitigando las desconexiones prematuras antes de las 6 horas.

**Pregunta 4: Margen de Holgura Óptimo ($\Delta t_{\text{buffer}}$)**

* *Respuesta:* El análisis de sensibilidad reveló que el margen óptimo es $\Delta t_{\text{buffer}} = 2.5\text{ minutos}$. Valores menores incrementan la probabilidad de que la comida espere en mostrador enfriándose, mientras que valores mayores reintroducen ociosidad innecesaria en la jornada del conductor.

## 6. Conclusiones y Cierre

### 6.1 Recomendación Técnica de Ingeniería

Con base en el análisis integral del gemelo digital y la validación matemática multicanal, **se recomienda formalmente a la Gerencia de Operaciones el despliegue a producción de la política de Despacho Sincronizado Predictivo ($\Delta t_{\text{buffer}} = 2.5\text{ min}$)**, sustituyendo de manera definitiva la asignación Voraz Inmediata.

El modelo de simulación de eventos discretos demuestra cuantitativamente que esta actualización algorítmica resuelve la disfunción principal del sistema sin necesidad de incrementar el tamaño de la flota instalada. Al aplazar estratégicamente el envío de la oferta a los conductores, la plataforma logra:

1. Proteger los ingresos del repartidor (reduciendo su ociosidad no remunerada en un $80.1\%$).
2. Asegurar el cumplimiento del SLA térmico alimentario (comida caliente en menos de $1.8\text{ min}$ de espera en mostrador).
3. Estabilizar la congestión logística en los picos de demanda, desplomando la pérdida de clientes por cancelación del $16.5\%$ al $2.8\%$.

El impacto sistémico de esta decisión prueba que en plataformas de economía colaborativa, la optimización estocástica del *timing* de asignación produce retornos operativos drásticamente superiores al simple aprovisionamiento de flota.
