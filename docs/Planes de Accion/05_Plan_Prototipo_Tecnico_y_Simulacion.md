# PLAN DE ACCIÓN 05: PROTOTIPO TÉCNICO, SIMULACIÓN Y TELEMETRÍA
## Módulos del Documento: 4. Prototipo Técnico Mínimo y Repositorio, Bono Opcional de Carga (Locust)
## Criterios de Rúbrica Asociados: R8 (0.7), Bono (+0.2)

---

### 1. Objetivos del Plan
Diseñar, implementar y verificar la suite técnica completa del prototipo de la Entrega 1:
1. Una API REST modular en FastAPI con persistencia y telemetría integrada de latencias y consumo de recursos (CPU/RAM).
2. Despliegue reproducible con Docker y Docker Compose mediante un único comando (`docker compose up --build`).
3. El modelo de simulación de eventos discretos en SimPy (versión 0) con semilla fija, clases desacopladas y recolección de métricas.
4. El script/notebook de contraste analítico que compare empíricamente SimPy contra el modelo teórico $M/M/c$, evaluando el error porcentual.
5. El script de pruebas de carga con Locust (`locustfile.py`) con dos perfiles de usuario (Cliente y Repartidor) para asegurar el bono de +0.2.

---

### 2. Estructura de Directorios del Repositorio
```text
Modelos - PA/
├── README.md                      # Documentación y comando único de despliegue
├── docker-compose.yml             # Orquestación de servicios (API + Base de Datos + Telemetría)
├── Dockerfile                     # Construcción de la imagen reproducible de la API
├── requirements.txt               # Dependencias Python con versiones congeladas
├── locustfile.py                  # Prueba de humo de carga sintética (Bono +0.2)
├── docs/                          # Documentación, PDFs y planes de acción
│   ├── Planes de Accion/          # Planes 00 a 05
│   └── Planteamiento_Proyecto.md  # Borrador completo del documento de entrega
├── sistema_real/                  # Código fuente de la API REST real
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                # Entrada de FastAPI, endpoints y middlewares
│   │   ├── models.py              # Esquemas Pydantic y modelos SQLAlchemy
│   │   ├── database.py            # Conexión persistente PostgreSQL 15 (postgres:15-alpine)
│   │   ├── dispatch.py            # Lógica real de despacho y emparejamiento
│   │   └── telemetry.py           # Monitor de CPU/RAM y latencias HTTP
├── simulacion/                    # Motor de Simulación DES
│   ├── simpy_engine.py            # Gemelo digital 24h SimPy v0 con semilla fija
│   ├── entities.py                # Clases Order (11 estados), Courier (batería, 6h), Kitchen (47 fogones)
│   ├── policies.py                # Estrategias: GreedyImmediatePolicy vs PredictiveSynchronizedPolicy
│   └── metrics.py                 # Colector de estadísticas, percentiles p95/p99 y tiempos de mostrador
├── analisis/                      # Contrastes analíticos y validaciones
│   ├── queueing_theory.py         # Fórmulas analíticas cerradas M/M/c
│   ├── contrast_analysis.py       # Comparación numérica SimPy vs M/M/c (error < 5%) + Ley de Little
│   └── test_contrast.ipynb        # Notebook interactivo de verificación
└── datos/                         # Almacenamiento de telemetría y resultados
    ├── telemetry_log.csv          # Registro real de CPU, RAM y latencias
    └── simulation_results.json    # Salidas del modelo SimPy v0
```

---

### 3. Componentes Técnicos Detallados

#### 3.1 Sistema Real Mínimo (API REST en FastAPI + PostgreSQL en Docker Compose)
* **Catálogo de 13 Endpoints Propios del Dominio (Estructurados por Actor):**
  1. *Clientes:* `POST /api/v1/orders/` (ingesta), `GET /api/v1/orders/{order_id}/tracking` (rastreo), `POST /api/v1/orders/{order_id}/cancel` (cancelación voluntaria).
  2. *Restaurantes/KDS:* `GET /api/v1/restaurants/{id}/orders` (cola KDS sin ingredientes, Excl-2), `POST /api/v1/orders/{id}/ready` (pase a mostrador D-09, liberación de fogón y promoción FIFO).
  3. *Repartidores:* `POST /api/v1/couriers/login` (inicio de turno), `POST /api/v1/couriers/{id}/location` (pings GPS), `GET /api/v1/couriers/{id}/offers` (ofertas JIT), `POST /api/v1/orders/{id}/accept` (asignación atómica), `PATCH /api/v1/orders/{id}/status` (hitos de viaje y entrega D-08), `POST /api/v1/couriers/{id}/logout` (cierre de turno).
  4. *Configuración:* `GET /api/v1/config/` y `PUT /api/v1/config/` (control en tiempo real de políticas y umbrales).
  5. *DevOps / Salud:* `GET /api/v1/telemetry/health` (diagnóstico de hardware y conectividad PostgreSQL).
* **Componentes de Infraestructura en `docker-compose.yml` (Decisión D-04):**
  * Servicio 1 (`api`): Contenedor FastAPI con Uvicorn multi-worker, dependencias en `requirements.txt`, healthcheck interno y middleware de telemetría.
  * Servicio 2 (`db`): Contenedor oficial **PostgreSQL 15 (`postgres:15-alpine`)** con volumen persistente montado (`postgres_data`) y healthcheck activo `pg_isready`.

#### 3.2 Telemetría Base de Rendimiento
* **Métricas Registradas:**
  * Tiempo de respuesta por solicitud HTTP ($ms$) registrado mediante middleware asíncrono con `time.perf_counter()`.
  * Porcentaje de uso de CPU (`psutil.cpu_percent(interval=None)`).
  * Consumo de memoria RAM en megabytes (`psutil.Process().memory_info().rss / 1024**2`).
* **Formato de Exportación:** Archivo continuo `datos/telemetry_log.csv` con columnas:  
  `timestamp, method, path, status_code, latency_ms, cpu_percent, memory_mb`.
* **Modo de Escritura:** Append atómico con flush inmediato (`buffering=1`) para tolerar alta concurrencia sin corrupción.

#### 3.3 Modelo DES SimPy Versión 0 (Gemelo Digital 24 Horas)
* **Características Clave:**
  * Entorno estocástico reproducible: `random.seed(42)` y `numpy.random.seed(42)` para $1.440\text{ minutos}$ continuos.
  * **Desacoplamiento Estricto (Decisión D-10):** SimPy opera de forma 100% autónoma en tiempo virtual simulado (sin dependencias ni llamadas HTTP contra la API REST), resolviendo la jornada completa de 24 horas y $\approx 1.890$ pedidos en **2 a 5 segundos** de cómputo.
  * Red de 10 restaurantes con 47 fogones totales (`simpy.Resource(env, capacity=k_r)` con $k_r \in [3, 6]$).
  * Flota variable gobernada por NHPP de conexiones ($\lambda_{\text{login}}(t)$) con filtro preventivo de batería ($\ge 15\%$) y límite de 6 horas con flexibilidad de fin de entrega (Decisión D-08).
  * Políticas de despacho intercambiables: `GreedyImmediatePolicy` vs. `PredictiveSynchronizedPolicy` (con escalamiento dinámico y bono urgente +20%).
  * Protocolo anti-limbo en mostrador: merma y cancelación a los 20 min (`CANCELADO_SIN_REPARTIDOR`, Decisión D-07).
  * Salida verificable: Generación de métricas de desempeño ($W_{total\_p95}, T_{espera\_rest}, \rho, P_{canc}, T_{\text{mostrador\_p95}}$).

#### 3.4 Contraste Analítico: SimPy vs. $M/M/c$
* **Escenario de Contraste Homogéneo:**
  * Se parametrizan tanto el modelo analítico como la simulación SimPy con distribuciones estrictamente exponenciales ($\lambda = 12 \text{ ped/h}$, $\mu = 3 \text{ ped/h por repartidor}$, $c = 5$ repartidores, $\rho = \frac{12}{5 \times 3} = 0.80$).
* **Métricas Contrastadas:**
  * Utilización $\rho$, tiempo en cola $W_q$, tiempo en sistema $W$, longitud de cola $L_q$, pedidos en sistema $L$.
* **Tabla de Comparación:**
  * Columnas: Métrica | Valor Teórico $M/M/c$ | Valor Simulado SimPy (media de réplicas) | Diferencia Absoluta | Error Porcentual ($\%$) | Intervalo de Confianza al 95%.
  * Criterio de Aceptación: El error porcentual en estado estable debe ser menor al $5\%$, validando la correcta implementación de los eventos SimPy.

#### 3.5 Bono Opcional: Prueba de Humo con Locust (`locustfile.py`)
* **Perfiles de Usuario (3 Actores Concurrentes):**
  * `CustomerUser` (peso 5): Emite solicitudes de creación de pedidos (`POST /api/v1/orders/`), sondea el rastreo (`GET /api/v1/orders/{id}/tracking`) y cancela esporádicamente (`POST /api/v1/orders/{id}/cancel`).
  * `RestaurantUser` (peso 2): Consulta pantalla KDS (`GET /api/v1/restaurants/{id}/orders`) y notifica comanda lista en mostrador (`POST /api/v1/orders/{id}/ready`, Decisión D-09).
  * `CourierUser` (peso 3): Inicia turno (`POST /api/v1/couriers/login`), emite pings GPS (escenarios de 5s vs 15s para Pregunta 3), consulta ofertas JIT (`GET /api/v1/couriers/{id}/offers`), acepta de forma concurrente (`POST /api/v1/orders/{id}/accept`) y actualiza estados de viaje (`PATCH /api/v1/orders/{id}/status`).
* **Reporte de Desempeño:**
  * Reportes generados en `datos/locust_report.html` y `datos/locust_stats_stats.csv` mostrando peticiones por segundo sostenidas, $0.00\%$ de tasa de errores y percentiles de latencia sub-milimétricos.

---

### 4. Criterios de Aceptación y Verificación
- [X] Todo el entorno se levanta con un solo comando: `docker compose up --build`.
- [X] La API expone 13 endpoints específicos de pedidos a domicilio y responde con código HTTP 200/201 (supera el mínimo de 3).
- [X] Se genera un log real en `datos/telemetry_log.csv` con métricas de latencia, CPU y RAM mediante append atómico.
- [ ] El script de SimPy corre de punta a punta con semilla fija y reproduce las métricas.
- [ ] El script de contraste calcula el error porcentual y demuestra convergencia hacia el modelo $M/M/c$.
- [X] El archivo `locustfile.py` se ejecuta sin errores y prueba los 3 tipos de usuario con escenarios de la Pregunta 3 (Bono +0.2 asegurado).
