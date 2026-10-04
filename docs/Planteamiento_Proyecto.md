# PROYECTO DE AULA — ENTREGA PARCIAL 1
## Planteamiento del Proyecto: Gemelo Digital y Simulación Estocástica de una Plataforma de Pedidos a Domicilio (*QuickDelivery Sim*)

---

## 3.1 Identificación

* **Nombre del Proyecto:**  
  *Gemelo Digital y Simulación Estocástica para la Optimización de Despacho Sincronizado y Retención de Flota Abierta en Plataformas de Pedidos a Domicilio (QuickDelivery Sim)*.
* **Integrantes del Grupo:**
  1. **Integrante 1 (Líder de Modelado y Simulación Estocástica):**  
     * Código: `20241001` — Correo: `integrante1@universidad.edu.co`  
     * *Rol:* Modelado conceptual DES, formalización matemática de procesos y eventos en SimPy, balance de flujos culinarios y vehiculares, e implementación de políticas de despacho sincronizado bajo patrón Strategy.
  2. **Integrante 2 (Líder de Infraestructura y DevOps):**  
     * Código: `20241002` — Correo: `integrante2@universidad.edu.co`  
     * *Rol:* Desarrollo de la API REST real mínima en FastAPI, persistencia con PostgreSQL 15, contenedorización con Docker y Docker Compose, instrumentación del middleware de telemetría (CPU/RAM/latencias) y pruebas de carga sintética con Locust.
  3. **Integrante 3 (Líder de Análisis de Datos, Modelos Matemáticos y Calibración):**  
     * Código: `20241003` — Correo: `integrante3@universidad.edu.co`  
     * *Rol:* Formulación analítica de teoría de colas ($M/M/c$), deducción de Erlang-C y Ley de Little, análisis y sustentación de disparidad frente al simulador, caracterización estadística de parámetros, plan de recolección de datos, cálculo de KPIs operacionales (percentiles $p95/p99$), diseño de clases POO (patrón Strategy) y gestión de riesgos.
* **Enlace al Repositorio de Control de Versiones:**  
  `https://github.com/grupo-modelos/quickdelivery-sim` *(o enlace respectivo asignado por el equipo)*

---

## 3.2 Descripción del Sistema Objeto de Estudio

### 3.2.1 Contexto de Negocio, Actores y Toma de Decisiones
El sistema objeto de estudio es una **plataforma de comercio electrónico y entrega rápida de última milla** (estilo *Rappi*, *DiDi Food* o *Uber Eats*) que opera en un entorno urbano continuo de 24 horas. La plataforma actúa como un orquestador digital que interconecta tres actores independientes:
1. **Los Clientes:** Consumidores que consultan catálogos gastronómicos, emiten pedidos en ráfagas estocásticas a lo largo del día, monitorean la trayectoria del repartidor en un mapa interactivo (rastreo en tiempo real) y presentan umbrales finitos de impaciencia, pudiendo cancelar su orden si la demora estimada supera su tolerancia máxima.
2. **Los Restaurantes Asociados:** Locales comerciales que reciben órdenes validadas, cuentan con capacidades finitas de cocción (fogones o estaciones de preparación simultáneas) y operan con tiempos de cocción variables según la complejidad del menú.
3. **Los Repartidores Autónomos (*Crowdsourcing / Flota Abierta*):** Conductores de motocicletas y bicicletas que no están contratados bajo jornadas laborales rígidas, sino que deciden de forma autónoma cuándo conectarse (*login*) y desconectarse (*logout*). Durante su jornada, reciben ofertas de viaje con una ventana de 45 segundos para aceptar o rechazar, trasladándose hacia el local para recoger el pedido y luego hasta el domicilio del cliente.

**¿Quién toma la decisión de ingeniería?**  
La decisión es adoptada por el **Gerente de Operaciones Logísticas** y el **Líder de Ingeniería de Plataforma**. Su objetivo no es manipular de forma coercitiva a los repartidores independientes, sino diseñar la **política algorítmica de software en el motor de despacho** y el **esquema de incentivos dinámicos** que maximice la productividad por hora de la flota disponible, reduzca el tiempo total de permanencia del cliente en el sistema y minimice las cancelaciones sin incurrir en costos excesivos de compensación.

---

### 3.2.2 Comportamiento del Flujo y Cuellos de Botella (Qué fluye, qué espera y qué se satura)
* **Qué Fluye:**  
  Fluyen **órdenes de pedido** (entidades de información que transitan a estados físicos: desde paquetes digitales HTTP, comandas en cocina, hasta bolsas térmicas de comida en tránsito vehicular) y **señales de telemetría de rastreo** (posicionamiento GPS a 1 Hz y reportes de estado).
* **Qué Espera (Colas de Contención):**
  * *Cola de Cocina:* Los pedidos esperan frente a los fogones si la capacidad de la cocina $k$ está saturada.
  * *Cola de Despacho:* Los pedidos cocinados (o en cocción) esperan en la plataforma hasta que un repartidor libre acepte el viaje.
  * *Cola en Mostrador de Recogida:* Si el repartidor llega antes de que la cocina termine, el repartidor **espera ocioso en el restaurante**, consumiendo su valiosa ventana de conexión de 6 horas y drenando la batería de su dispositivo móvil.
* **Qué se Satura:**  
  * *En horas pico (Almuerzo 11:30–14:30 y Cena 18:30–22:00):* Se satura la disponibilidad de repartidores libres en el radio urbano, se congestionan las cocinas y se sobrecargan las conexiones simultáneas en el servidor de rastreo por consultas continuas de estado.

---

### 3.2.3 Arquitectura del Sistema Real Mínimo
El sistema real mínimo desplegable se compone de microservicios desacoplados y contenerizados con Docker, garantizando telemetría en tiempo real:

```mermaid
flowchart TD
    subgraph CLIENT_ZONE["Clientes, Restaurantes y Repartidores (Apps / KDS / Web)"]
        CLI["Cliente\n(HTTP Client / App)"]
        REST["Restaurante\n(KDS / Tablet de Cocina)"]
        REP["Repartidor Autónomo\n(App GPS / Telemetry)"]
    end

    subgraph INGRESS_LAYER["Capa de Entrada y Ruteo"]
        GW["Reverse Proxy / API Gateway\n(Nginx / Uvicorn: 8000)"]
    end

    subgraph CORE_SERVICES["Servicios Núcleo (FastAPI en Contenedor)"]
        API_ORD["Servicio de Pedidos\n(Order Management)"]
        DISP_ENG["Motor de Despacho y Asignación\n(Dispatch Engine)"]
        TRACK_SRV["Servicio de Rastreo y Telemetría\n(Tracking Service)"]
        TEL_MID["Middleware de Telemetría\n(CPU, RAM, Latency Logger)"]
    end

    subgraph DATA_LAYER["Almacén de Estado y Persistencia"]
        DB[(Base de Datos Relacional Persistente\nPostgreSQL 15 / postgres:15-alpine)]
        LOG_CSV[("Archivo de Telemetría\ndatos/telemetry_log.csv")]
    end

    CLI -->|POST /api/v1/orders/| GW
    REST -->|POST /api/v1/orders/{id}/ready| GW
    REP -->|POST /api/v1/dispatch/assign/| GW
    CLI -->|GET /api/v1/orders/{id}/tracking| GW
    GW --> API_ORD
    GW --> DISP_ENG
    GW --> TRACK_SRV

    API_ORD <--> DB
    DISP_ENG <--> DB
    TRACK_SRV <--> DB

    CORE_SERVICES -.-> TEL_MID
    TEL_MID -.->|Registro continuo| LOG_CSV
```

* **Componentes Principales:**
  1. **API REST de Ingestión (`Order Management`):** Recibe las órdenes y valida la información del pedido.
  2. **Motor de Despacho (`Dispatch Engine`):** Evalúa la cola de pedidos pendientes frente a los repartidores libres, ejecutando la política activa (Voraz Inmediata vs. Despacho Sincronizado).
  3. **Servicio de Rastreo (`Tracking Service`):** Registra el avance cinemático de los repartidores y sirve las coordenadas GPS a los clientes.
  4. **Base de Datos / Almacén de Estado (`State Store`):** Mantiene el ciclo de vida de los pedidos y el estado de la flota (`DISPONIBLE`, `VIAJANDO_A_LOCAL`, `EN_MOSTRADOR`, `EN_TRANSITO_CLIENTE`, `DESCONECTADO`).
  5. **Middleware de Telemetría:** Captura instantáneamente el tiempo de procesamiento por endpoint ($ms$) y el consumo de CPU y memoria RAM mediante `psutil`.

---

### 3.2.4 Clasificación Taxonómica del Modelo de Simulación
El modelo de gemelo digital implementado se clasifica rigurosamente en las cuatro dimensiones fundamentales de la taxonomía de modelos:

1. **Discreto vs. Continuo $\rightarrow$ DISCRETO:**  
   *Justificación:* El estado del sistema (número de pedidos en espera, repartidores ocupados, nivel de inventario en cocina) no cambia de forma continua a través de ecuaciones diferenciales suaves, sino que salta instantáneamente en instantes discretos del tiempo marcados por la ocurrencia de eventos específicos (`LlegadaPedido`, `FinCocina`, `AceptacionRepartidor`, `EntregaFinal`).
2. **Estático vs. Dinámico $\rightarrow$ DINÁMICO:**  
   *Justificación:* El tiempo es una variable fundamental explícita del modelo; el sistema evoluciona a lo largo de un horizonte continuo de 24 horas ($1.440\text{ minutos}$), donde el estado en cualquier instante $t_{k+1}$ depende de las acumulaciones históricas y estados de cola transitorios alcanzados en $t_k$.
3. **Determinista vs. Estocástico $\rightarrow$ ESTOCÁSTICO:**  
   *Justificación:* Las variables de entrada no son constantes ni predecibles con exactitud; los tiempos entre llegadas de órdenes ($\text{Exp}(\lambda(t))$), tiempos de cocción ($\text{LogNormal}$), traslados vehiculares ($\text{Normal Truncada}$) y la impaciencia de cancelación ($\text{Weibull}$) son variables aleatorias modeladas mediante distribuciones de probabilidad.
4. **Empírico vs. Mecanístico $\rightarrow$ MECANÍSTICO:**  
   *Justificación:* El modelo representa explícitamente las leyes de balance de flujo, las restricciones de capacidad física de las cocinas y los mecanismos causales de colas y despacho de repartidores, complementándose con parámetros empíricos calibrados a partir de telemetría de campo.

---

### 3.2.5 Tabla de Cumplimiento de Criterios de Elegibilidad (C1 a C7)

| Criterio | Exigencia del PDF | Cómo se Cumple y Evidencia en este Proyecto |
| :--- | :--- | :--- |
| **C1: Contención por recursos finitos** | Sistema TI o de software con colas y recursos limitados. | **Flota finita y variable de repartidores conectados** ($c(t)$), capacidad finita de estaciones de cocina en restaurantes ($k$) y número acotado de workers en el servidor HTTP de la API REST. |
| **C2: Sistema real mínimo desplegable** | API REST en contenedor con al menos 2 servicios y 3 endpoints propios. | **API FastAPI contenerizada en Docker Compose** con base de datos **PostgreSQL 15 (`postgres:15-alpine`)** persistente y endpoints propios del dominio: `POST /api/v1/orders/`, `POST /api/v1/orders/{id}/ready`, `POST /api/v1/dispatch/assign/`, `GET /api/v1/orders/{id}/tracking`. |
| **C3: $\ge 3$ etapas de servicio y regla de prioridad** | Red de colas con al menos 3 etapas y reglas de prioridad o tipología (C3). | **3 Etapas de Servicio en Serie:** (1) Recepción y Validación del Pedido, (2) Preparación en Cocina y Asignación de Repartidor, (3) Tránsito y Entrega con Rastreo. <br>**Regla de Prioridad Explícita:** Disciplina de prioridad dinámica anti-abandono (los pedidos reasignados tras rechazo de un repartidor o con mayor tiempo acumulado en cocina reciben prioridad estricta sobre nuevas órdenes entrantes, evitando la cancelación del cliente). |
| **C4: Variable de decisión controlable** | Política o regla de control clara (política actual vs. alternativa). | **Política de Despacho:** *Política Actual:* Asignación Voraz Inmediata (empareja al instante). vs. *Política Alternativa:* Despacho Sincronizado Predictivo ($t_{\text{despacho}} = t_{\text{ready\_est}} - t_{\text{viaje}}$). |
| **C5: Llegadas no estacionarias** | Picos, estacionalidad o ráfagas que justifiquen análisis dinámico. | **Jornada continua de 24 horas con demanda horaria modulada (NHPP, $\approx 1.890\text{ ped/día}$):** Madrugada ($0.15\text{ ped/min}$), Desayuno ($1.00\text{ ped/min}$), Valle ($0.80\text{ ped/min}$), **Pico Almuerzo ($2.70\text{ ped/min}$, $\rho=106\%$)**, Tarde ($1.20\text{ ped/min}$), **Pico Cena ($3.30\text{ ped/min}$, $\rho=130\%$, pico máximo diario)**, Cierre ($0.50\text{ ped/min}$). |
| **C6: Límite físico o duro medible** | Cota física insuperable que condiciona el comportamiento. | **Límite de 6 horas de conexión continua por repartidor** por fatiga psicomotriz (OIT/ILO, 2021) y **autonomía de batería de smartphone** (4 a 6 horas bajo tracking GPS a 1 Hz, Carroll & Heiser, 2010). |
| **C7: Actores autónomos para ABM (Mesa)** | Actores con comportamiento adaptativo y toma de decisiones. | **Repartidores:** Aceptan/rechazan ofertas (timeout 45s), deciden login/logout y monitorean batería. <br>**Clientes:** Monitorean el rastreo en tiempo real y cancelan por impaciencia si la demora excede su umbral. |

---

## 3.3 Problema y Preguntas de Decisión

### 3.3.1 Enunciado del Problema (1 Párrafo)
> *"En un ecosistema urbano donde la flota de repartidores opera bajo economía colaborativa (crowdsourcing) con conexiones voluntarias acotadas a un máximo de 6 horas continuas por fatiga psicomotriz y agotamiento de batería de sus dispositivos, la plataforma enfrenta un severo déficit de oferta en los picos de almuerzo (11:30–14:30) y cena (18:30–22:00), elevando el percentil 95 del tiempo de ciclo total ($W_{total\_p95}$) a más de 55 minutos y las cancelaciones de clientes insatisfechos al 16.5%. La causa raíz es la política actual de asignación voraz inmediata, la cual despacha al repartidor al instante en que el cliente emite la orden; esto provoca que los repartidores pasen un promedio de 16.2 minutos inactivos en el mostrador del restaurante esperando que la cocina termine el pedido (demora que se agrava en los picos por la saturación de los fogones). Este tiempo muerto reduce drásticamente sus ingresos por hora y drena la batería de sus dispositivos por emisiones continuas de rastreo GPS en reposo, provocando desconexiones prematuras de la aplicación que reducen hasta el 35% de la flota disponible en el momento de mayor congestión. La gerencia de operaciones requiere comparar la política actual frente a un despacho diferido sincronizado con el tiempo estimado de preparación (ETA de cocina) para maximizar la productividad por hora de los repartidores y retener la oferta activa durante las horas pico."*

### 3.3.2 Preguntas de Decisión Cuantitativas (Política Actual vs. Alternativas)
1. **Pregunta de Decisión 1 (Sincronización y Productividad de Flota):**  
   *¿En qué porcentaje se reduce el tiempo promedio de espera ociosa del repartidor en el restaurante ($T_{espera\_rest}$, meta: $\le 3.5\text{ min}$) y cuál es el incremento en el número promedio de pedidos completados por repartidor dentro de su permanencia máxima de 6 horas al sustituir la asignación voraz inmediata por una política de despacho sincronizado predictivo ($t_{\text{despacho}} = t_{\text{ready}} - t_{\text{viaje}}$) durante los picos de almuerzo y cena?*
2. **Pregunta de Decisión 2 (Dimensionamiento y Nivel de Servicio en Pico Máximo):**  
   *¿Cuál es el número mínimo de repartidores activos conectados por hora ($c_{min}(t) \in [75, 95]$) que la plataforma debe incentivar en el pico de cena (18:30–22:00, $3.30\text{ ped/min}$) para mantener la utilización del sistema ($\rho$) entre el 75% y el 85%, logrando que el percentil 95 del tiempo total de entrega no supere los 40 minutos ($W_{total\_p95} \le 40\text{ min}$) y la tasa de cancelación sea inferior al 3% ($P_{canc} < 3\%$)?*
3. **Pregunta de Decisión 3 (Frecuencia de Rastreo, Consumo Energético e Infraestructura):**  
   *¿Cómo influye modificar la frecuencia de actualización del socket de telemetría de rastreo (sondeo cada 5 s vs. cada 15 s) sobre la tasa de descarga de batería del repartidor en sus 6 horas de conexión y sobre la latencia en el percentil 99 ($T_{lat\_api\_p99} \le 180\text{ ms}$) del microservicio de seguimiento bajo carga extrema?*
4. **Pregunta de Decisión 4 (Ventana de Holgura y Compensación Cocina–Despacho):**  
   *¿Cuál es el margen de holgura temporal óptimo ($\Delta t_{buffer} \in [0, 5]\text{ minutos}$) en la regla de despacho sincronizado ($t_{\text{despacho}} = t_{\text{ready}} - t_{\text{viaje}} + \Delta t_{buffer}$) que minimiza conjuntamente el tiempo de espera del repartidor en el local y el tiempo en que la comida terminada permanece enfriándose en el mostrador sin elevar la tasa de cancelación de los clientes?*

---

## 3.4 Objetivos del Proyecto

### 3.4.1 Objetivo General
Desarrollar un gemelo digital estocástico basado en simulación de eventos discretos (DES) y modelado multiagente (ABM) para una plataforma de pedidos a domicilio en un ciclo operativo continuo de 24 horas, que permita evaluar cuantitativamente políticas de despacho sincronizado y retención de flota abierta, optimizando el percentil 95 del tiempo de ciclo total ($W_{total\_p95}$) y minimizando la tasa de cancelación de clientes bajo condiciones de alta congestión.

### 3.4.2 Objetivos Específicos (Verificables a lo Largo del Semestre)
1. **Para la Entrega 1 (Semanas 1–7):**  
   *Formalizar el modelo conceptual DES del flujo de pedidos, cocina, asignación y rastreo; formular analíticamente el subsistema de despacho mediante teoría de colas ($M/M/c$) verificando la Ley de Little; implementar un prototipo ejecutable en SimPy versión 0 con semilla fija; y desplegar la API REST mínima reproducible en Docker Compose con registro de telemetría base (CPU, RAM y latencia).*
2. **Para la Entrega 2 (Semanas 8–12):**  
   *Someter la API REST a pruebas de carga sintética con perfiles concurrentes en Locust; recolectar telemetría real y calibrar las distribuciones de tiempos de cocina y viaje mediante pruebas Kolmogorov-Smirnov; aplicar estimación bayesiana de parámetros estocásticos mediante PyMC; y construir un modelo subrogado con restricciones físicas duras (PINN o regresor acotado) que prediga latencias y consumo de recursos bajo sobrecarga.*
3. **Para la Entrega Final (Semanas 13–16):**  
   *Desarrollar un modelo multiagente con el framework Mesa que reproduzca la autonomía de decisión de los repartidores (conexión, aceptación/rechazo y agotamiento de batería) y clientes (impaciencia y abandono); acoplar bidireccionalmente el simulador con la API del sistema real; y entrenar un agente de decisión inteligente (aprendizaje por refuerzo o heurística adaptativa) que resuelva la política de despacho sincronizado en tiempo real durante la sustentación en vivo.*

---

## 3.5 Alcance, Delimitación y Supuestos Iniciales

### 3.5.1 Alcance del Modelo: Inclusiones y Exclusiones Justificadas
* **Componentes Dentro del Alcance (Modelados Explícitamente):**
  * *Ingreso de Órdenes:* Generación de pedidos según el proceso de Poisson no homogéneo a lo largo de las 24 horas.
  * *Capacidad y Tiempos de Cocina:* Cola de preparación en restaurante modelada como un recurso multi-servidor finito con tiempos de servicio Log-Normales.
  * *Motor de Asignación y Despacho:* Implementación intercambiable de la política actual voraz y la política alternativa sincronizada basada en predicción de tiempos de preparación.
  * *Cinemática de Tránsito Urbano y Rastreo:* Desplazamiento estocástico del repartidor hacia el restaurante y hacia el cliente, gobernado por distancias de ruta y velocidades efectivas urbanas.
  * *Dinámica de Flota Abierta:* Conexión y desconexión estocástica de repartidores con restricción física dura de 6 horas máximas de permanencia y drenaje de batería.
  * *Comportamiento del Cliente:* Cancelación estocástica de pedidos si el tiempo de espera acumulado supera su función de impaciencia.
* **Componentes Fuera del Alcance (Exclusiones con Justificación Técnica):**
  * *Pasarela de Pagos Externa:* Se asume que el pago bancario o con tarjeta de crédito se procesa de forma síncrona y exitosa en $< 1\text{ s}$ en el momento de crear la orden. *Razón:* Las demoras de la pasarela bancaria externa son ajenas a la logística de despacho y no influyen en la contención de repartidores en calle.
  * *Auditoría Contable y Facturación Electrónica:* Se excluyen los procesos de emisión de factura tributaria y liquidación de impuestos. *Razón:* Son procesos asíncronos en segundo plano que no consumen recursos del camino crítico de despacho ni afectan los tiempos de entrega.
  * *Enrutamiento Vial a Nivel de Micro-Tráfico (GIS Complejo / Semáforos Individuales):* No se simula la física individual de cada intersección semafórica o giro en U. *Razón:* Se utiliza una distancia de ruta urbana basada en distancia Manhattan corregida por el **factor de sinuosidad vial ($\tau = 1.25$)** y velocidad media urbana validada en literatura ($18\text{ km/h} \pm 4\text{ km/h}$), evitando una explosión computacional innecesaria para el propósito del gemelo digital.
  * *Desagregación del Menú por Tipo y Cantidad de Platos:* No se modelan las distribuciones individuales de platos específicos (ej. entradas, postres, bebidas o número de ítems desagregados por orden). Cada pedido se trata como una unidad agregada de producción culinaria cuyo tiempo total de cocción en fogón sigue una distribución Log-Normal ($\mu \approx 18.5\text{ min}$). *Razón:* El desglose interno de recetas y porciones pertenece a sistemas de gestión interna de restaurantes (POS) y no altera la dinámica macroscópica de colas de asignación y despacho de última milla, evitando una sobreparametrización innecesaria.

---

### 3.5.2 Especificación del Espacio Geográfico (GPS) y Capacidad de Cocina (Fogones)

#### A. Modelado del Espacio Urbano y Distancias Viales ($\tau = 1.25$)
Para lograr un equilibrio entre realismo geográfico y alta eficiencia computacional en SimPy y la API REST, el sistema delimita un clúster metropolitano de **$6\text{ km} \times 6\text{ km}$** anclado a un datum GPS real $(\text{lat}_0 = 4.6534, \text{lon}_0 = -74.0560)$:
* **Métrica de Distancia Vial con Sinuosidad Urbana:**  
  Los vehículos de reparto en ciudades consolidadas no se desplazan en línea recta euclidiana ni en una cuadrícula ortogonal perfecta. La literatura formal en ingeniería de transporte y redes viales urbanas (**Ballou et al., 2002; Levinson & El-Geneidy, 2009; Boscoe et al., 2012; Boeing, 2019**) demuestra empíricamente que la relación entre la distancia real sobre red de calles ($d_{\text{red}}$) y la distancia ortogonal Manhattan ($d_{\text{manhattan}} = |x_2 - x_1| + |y_2 - y_1|$) sigue un **índice de sinuosidad (*circuity factor*) $\tau$ comprendido típicamente entre $1.20$ y $1.28$** para tramas urbanas metropolitanas regulares a semirregulares. Se adopta el estándar de:
  $$d_{\text{vial}} = \tau \times \left( |x_{\text{destino}} - x_{\text{origen}}| + |y_{\text{destino}} - y_{\text{origen}}| \right) \quad \text{con } \tau = 1.25$$
  *(Fuente comprobable: Ballou, R. H., Rahardja, H., & Sakai, N., 2002, "Selected Properties of Manhattan and Euclidean Distances as Approximations for Network Distances", Computers & Operations Research, 29(8), 983–1001; Levinson, D., & El-Geneidy, A., 2009, "The circuity of urban travel", Transportation Research Part A, 43(8), 701-713).*
* **Cinemática y Telemetría de Rastreo:**  
  La velocidad del repartidor se modela como $V_{\text{rep}} \sim \mathcal{N}(18\text{ km/h}, 3\text{ km/h})$ truncada en $[8, 25]\text{ km/h}$. Durante el viaje, la posición instantánea se interpola de forma lineal continua y se proyecta a coordenadas GPS reales para alimentar el endpoint `GET /api/v1/orders/{id}/tracking`, mientras la batería se drena a razón de $0.15\%/\text{min}$ en movimiento con GPS activo a 1 Hz y $0.05\%/\text{min}$ en mostrador de espera (Carroll & Heiser, 2010).

#### B. Modelado de Cocina y Capacidad Finita de Fogones ($k_r$)
La oferta culinaria de la plataforma se compone de una red de **$M = 10\text{ restaurantes}$** fijos distribuidos en el plano $(x_r, y_r)$:
* Cada restaurante $r \in \{1, \dots, 10\}$ cuenta con un recurso finito heterogéneo de puestos de cocción simultáneos (fogones, hornos o planchas) modelado en SimPy como:
  $$\text{restaurante}[r].\text{fogones} = \text{simpy.Resource}(env, \text{capacity}=k_r) \quad \text{con } k_r \in [3, 6]$$
  Totalizando **$47\text{ fogones en toda la red}$** (promedio $4.7$ fogones/restaurante). Con un tiempo medio de cocción de $18.5\text{ min}$, la capacidad nominal máxima sostenible de la red culinaria es $\lambda_{\text{cocina\_max}} = \frac{47}{18.5} \approx \mathbf{2.54\text{ ped/min}}$.
* **Dinámica de Contención y Cola de Cocina:**  
  Cuando entra una orden para el restaurante $r$, solicita $1$ puesto en sus fogones. Si todos los $k_r$ puestos están ocupados, el pedido entra en la **Cola de Espera de Cocina** (disciplina FIFO). Una vez asignado el fogón, el tiempo de preparación sigue una distribución $T_{\text{cocina}} \sim \text{LogNormal}(\mu_{ln}=2.85, \sigma_{ln}=0.35)$ (media $\approx 18.5\text{ min}$). Al finalizar, la orden pasa al mostrador de empaque y el fogón se libera de inmediato para el siguiente pedido.
* **Vínculo con el Despacho Sincronizado:**  
  El motor de despacho inteligente estima la hora en que la comida estará lista:
  $$\text{ETA}_{\text{listo}} = t_{\text{actual}} + (Q_{\text{cocina\_r}} \times \bar{T}_{\text{cocina}}) + T_{\text{preparacion\_est}}$$
  Y envía la oferta al repartidor en el momento exacto:
  $$t_{\text{despacho}} = \text{ETA}_{\text{listo}} - t_{\text{viaje\_repartidor}} + \Delta t_{\text{buffer}}$$
  eliminando el tiempo ocioso del repartidor en el local ($T_{\text{espera\_rest}} \to 0$).

---

### 3.5.3 Horizonte Temporal, Unidad de Medida y Condiciones Iniciales
* **Horizonte de Simulación:**  
  Una jornada continua de **24 horas de operación ($1.440\text{ minutos} = 86.400\text{ segundos}$)**, permitiendo capturar el ciclo diurno completo con sus dos valles y sus dos picos de demanda.
* **Unidad de Tiempo del Modelo:**  
  *Minutos* en la simulación estocástica DES (con resolución de decimales en segundos) y *milisegundos* en las mediciones de latencia de la API real.
* **Condiciones Iniciales del Sistema:**  
  * El sistema inicia en $t = 0.0$ (00:00 h, medianoche).
  * *Estado Inicial de Colas:* Sistema vacío y ocioso en cuanto a pedidos pendientes ($Q_{asig}(0) = 0$, $Q_{cocina}(0) = 0$).
  * *Flota Inicial de Guardia Nocturna:* Se inicializa una oferta base de $c(0) = 6$ repartidores conectados en la zona urbana para atender la demanda residual de la madrugada ($0.15\text{ ped/min}$).
  * *Período de Calentamiento (*Warm-up*):* No se descartan datos de calentamiento ya que la madrugada representa el estado natural de transición y arranque operativo real de las plataformas de delivery antes del pico de desayuno.

---

### 3.5.4 Tabla de Supuestos Iniciales

| # | Supuesto Inicial | Justificación | Fuente / Evidencia Empírica Comprobable | Impacto en el Modelo si Resulta Falso |
| :-: | :--- | :--- | :--- | :--- |
| **S1** | **Permanencia máxima de 6 horas por repartidor ($T_{\text{max}} = 360\text{ min}$).** | La fatiga psicomotriz en conducción urbana de motocicletas incrementa el riesgo de colisión tras 6h; las baterías de smartphone con GPS continuo a 1 Hz duran entre 4.5 y 6 horas. | Organización Internacional del Trabajo (OIT / ILO, 2021); Gregory (2021); Carroll & Heiser (2010); Battery University. | Si los repartidores trabajaran turnos ilimitados, se sobrestimaría la disponibilidad de flota activa en horas pico y se eliminaría el límite físico del gemelo. |
| **S2** | **Tiempos de preparación en cocina siguen distribución Log-Normal ($\mu \approx 18.5\text{ min}$).** | Procesos culinarios humanos son estrictamente positivos y asimétricos hacia la derecha; platos elaborados generan colas largas en picos. | Alnaggar et al. (2021, *Transp. Res. Part E*); DoorDash Engineering (2020). | Asumir distribución Exponencial subestimaría drásticamente la variabilidad de cocción, distorsionando la sincronización de despacho. |
| **S3** | **El pico de cena (18:30–22:00) es superior en volumen al pico de almuerzo.** | En almuerzo los trabajadores tienen alternativas presenciales (comedores, comida casera, pausas rígidas); en la cena predomina el descanso en el hogar, pedidos grupales y ocio digital. | Deliverect Industry Report (2023); Statista Digital Market Insights (2023); DoorDash Trend Reports (2023). | Si los picos fueran idénticos, se desajustaría el dimensionamiento de incentivos dinámicos nocturnos, provocando colapso de colas en la cena. |
| **S4** | **Los clientes cancelan el pedido si la espera excede su paciencia máxima ($\approx 35-45\text{ min}$).** | El comportamiento de los consumidores presenta una tasa de riesgo instantánea de cancelación acelerada conforme la demora se aleja del compromiso inicial. | Bai et al. (2019, *M&SOM*); Deliverect Consumer Survey (2023). | Si los clientes tuvieran paciencia infinita, las colas de pedidos tenderían al infinito durante los picos ($\rho > 1$), ocultando la pérdida real de ventas. |
| **S5** | **Velocidad media efectiva urbana de $18\text{ km/h} \pm 4\text{ km/h}$.** | Refleja la cinemática real de motos y bicicletas en arterias metropolitanas con semáforos, pasos peatonales y tráfico moderado. | Dablanc et al. (2018, *City Logistics*); OpenStreetMap Mobility Analytics (2023). | Si la velocidad fuera notablemente mayor, se subestimarían los tiempos de viaje a domicilio y la tasa de consumo de batería por trayecto. |
| **S6** | **Timeout de respuesta de repartidor fijado en 45 segundos.** | Ventana estándar otorgada por las interfaces de usuario móviles de reparto para evitar el bloqueo prolongado de órdenes sin asignar. | Parámetros operacionales estándar de Rappi, DiDi Food y Uber Eats Partner Guidelines (2023). | Un timeout más largo incrementaría innecesariamente el tiempo de espera en cola de asignación ($W_q$) de pedidos rechazados. |
| **S7** | **Factor de sinuosidad vial urbana $\tau = 1.25$ sobre distancia Manhattan.** | La red vial metropolitana no es una cuadrícula geométrica perfecta; desvíos por sentidos de vías y giros elevan la distancia real en un 25% respecto a la métrica ortogonal. | **Ballou, Rahardja, & Sakai (2002)**, *Computers & Operations Research*, 29(8), 983–1001; **Levinson & El-Geneidy (2009)**, *Transportation Research Part A*, 43(8), 701-713; **Boeing (2019)**, *Applied Network Science*, 4(1), 67. | Usar distancia euclidiana o Manhattan pura ($\tau = 1.0$) subestimaría las distancias y tiempos de traslado en un 20–25%, falseando el cálculo del despacho sincronizado y el gasto de batería. |
| **S8** | **Elección aleatoria equiprobable de restaurante ($R_i \sim \mathcal{U}\{1, 10\}$).** | Los clientes eligen cualquiera de los 10 restaurantes con idéntica probabilidad a priori, distribuyendo la demanda sin sesgos de marketing o sistemas de recomendación. | Supuesto estándar de desacoplamiento de preferencias en redes de colas abiertas (Kleinrock, 1975). | Si la demanda se concentrara desproporcionadamente en un solo restaurante ("estrella"), la cola de cocina de ese local se saturaría prematuramente mientras los otros 9 quedarían ociosos. |
| **S9** | **Límite de vida útil térmica en mostrador de 20 minutos ($T_{\text{max\_mostrador}} = 20\text{ min}$).** | Alimentos empacados pierden inocuidad térmica y textura tras 20 min en mostrador sin recolección. La plataforma asume el costo de merma y cancela la orden para no entregar un producto degradado. | Directrices de Calidad e Higiene de Alimentos (FDA Food Code, 2022); estándares de operación de Dark Kitchens (DoorDash, Rappi, 2023). | Si los pedidos esperaran indefinidamente sin repartidor, las órdenes quedarían en un limbo sin estado absorbente terminal, distorsionando las estadísticas de tiempo en cola ($W_q$). |
