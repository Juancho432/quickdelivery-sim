# QuickDelivery Sim — Gemelo Digital y Simulación Estocástica
## Proyecto de Aula: Entrega Parcial 1
### Plataforma de Pedidos a Domicilio con Despacho Sincronizado y Retención de Flota Abierta en 24 Horas

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15_Alpine-336791.svg?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker_Compose-Multi--Container-2496ED.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![Locust](https://img.shields.io/badge/Locust-Load_Testing-34495E.svg?style=flat&logo=locust&logoColor=white)](https://locust.io/)
[![SimPy](https://img.shields.io/badge/SimPy-4.1.1-green.svg?style=flat)](https://simpy.readthedocs.io/)

---

## 1. Descripción del Proyecto

**QuickDelivery Sim** es un prototipo técnico y gemelo digital de eventos discretos (DES) para optimizar el despacho en plataformas de pedidos a domicilio en tiempo real (estilo Rappi, Uber Eats o DiDi Food) a lo largo de una **jornada continua de 24 horas**.

El sistema aborda el problema de la **desincronización entre la preparación en cocina y el arribo del repartidor**:
* **Política Actual (Línea Base):** Asignación Voraz Inmediata, donde el repartidor pasa un promedio de $16.2\text{ minutos}$ inactivo en el restaurante esperando la comida, desperdiciando su cota física de 6 horas y drenando su batería móvil.
* **Política Propuesta (Alternativa):** Despacho Sincronizado Predictivo ($t_{\text{despacho}} = \text{ETA}_{\text{listo}} - t_{\text{viaje}} + \Delta t_{\text{buffer}}$) con cinemática vial corregida por sinuosidad ($\tau = 1.25$), filtro preventivo de batería ($\ge 15\%$) y límite de fatiga de 6 horas (OIT/ILO, 2021).

---

## 2. Arquitectura del Sistema Real Mínimo

El sistema real desacoplado opera en **tiempo de reloj real (*wall-clock time*)** mediante dos contenedores independientes enlazados por Docker Compose:

```
[ Clientes / KDS / Repartidores / Locust ]
                   │
                   ▼  HTTP :8000
    ┌──────────────────────────────┐
    │     Contenedor: api          │
    │  (FastAPI + Uvicorn Workers) │
    │   Middleware de Telemetría   │
    └──────────────┬───────────────┘
                   │ TCP :5432 (Internal Bridge)
                   ▼
    ┌──────────────────────────────┐
    │     Contenedor: db           │
    │  (PostgreSQL 15 Alpine)      │
    │  Volumen: postgres_data      │
    └──────────────────────────────┘
                   │
                   ▼ Montaje Bind ./datos
    [ datos/telemetry_log.csv ]
```

---

## 3. Despliegue con un Solo Comando (Criterio R8)

### Prerrequisitos:
* **Docker Desktop** (con Docker Compose v2+) instalado y corriendo en Windows, Linux o macOS.

### Comando Único de Despliegue:
Para construir las imágenes, inicializar PostgreSQL 15, ejecutar las migraciones, sembrar la base de datos (10 restaurantes y 47 fogones) y levantar la API con telemetría activa:

```bash
docker compose up --build
```

Una vez levantado, la API estará disponible y lista para responder peticiones en:
* **Documentación Interactiva Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Documentación ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
* **Diagnóstico de Salud y Telemetría:** [http://localhost:8000/api/v1/telemetry/health](http://localhost:8000/api/v1/telemetry/health)

Para detener los contenedores:
```bash
docker compose down
```

---

## 4. Catálogo de Endpoints de la API REST (13 Endpoints del Dominio)

La API expone 13 endpoints organizados según los 4 actores del ecosistema:

### 👤 Clientes
* `POST /api/v1/orders/`: Ingesta y persistencia de pedidos. Evalúa capacidad de cocina ($k_r$) y asigna a cocción (`EN_PREPARACION`) o cola (`EN_COLA_COCINA`).
* `GET /api/v1/orders/{order_id}/tracking`: Rastreo GPS en tiempo real de posición cartesiana del courier, distancia restante y estado de viaje.
* `POST /api/v1/orders/{order_id}/cancel`: Cancelación voluntaria del cliente por impaciencia (Weibull), liberando fogón o repartidor.

### 🍳 Restaurantes (KDS)
* `GET /api/v1/restaurants/{restaurant_id}/orders`: Pantalla KDS de cocina (**sin ingredientes ni recetas, Exclusión 2**). Evalúa merma anti-limbo ($\ge 20\text{ min}$).
* `POST /api/v1/orders/{order_id}/ready`: Notificación de comanda lista en mostrador (Decisión D-09). Libera fogón y **promueve automáticamente la siguiente orden en cola FIFO**.

### 🛵 Repartidores
* `POST /api/v1/couriers/login`: Inicio de turno de 6 horas, registro de batería inicial ($\sim \mathcal{N}(95\%, 5\%)$) y disponibilidad.
* `POST /api/v1/couriers/{courier_id}/location`: Pings periódicos de telemetría GPS y batería (insumo para Pregunta 3: 5s vs 15s).
* `GET /api/v1/couriers/{courier_id}/offers`: Consulta Just-In-Time de ofertas calificadas (filtros de batería $\ge 15\%$, turno $< 6\text{ h}$ y ventana de 45 s).
* `POST /api/v1/orders/{order_id}/accept`: Aceptación atómica concurrente en ventana de 45 s con `SELECT FOR UPDATE`.
* `PATCH /api/v1/orders/{order_id}/status`: Hitos físicos: arribo, recogida (sellado de tiempo en mostrador $t_{\text{mostrador}}$) y entrega final con logout forzado si cumplió 6 horas.
* `POST /api/v1/couriers/{courier_id}/logout`: Cierre formal de turno voluntario o forzado.

### ⚙️ Configuración y DevOps
* `GET /api/v1/config/`: Consulta de parámetros operativos vigentes.
* `PUT /api/v1/config/`: **Control Dinámico en Tiempo Real:** Permite alternar la política activa (`greedy` vs `synchronized`), ajustar el buffer $\Delta t_{\text{buffer}} \in [0, 5]\text{ min}$ y flexibilizar límites temporales para tests rápidos sin reiniciar contenedores.
* `GET /api/v1/telemetry/health`: Diagnóstico continuo de CPU (`psutil`), RAM, estado de la conexión a PostgreSQL y latencia promedio.

---

## 5. Pruebas de Carga Sintética con Locust (Bono +0.2)

El archivo `locustfile.py` implementa una prueba de carga sintética que simula la interacción concurrente de los 3 actores:
* `CustomerUser` (Weight = 5): Crea pedidos, consulta rastreo y simula cancelaciones esporádicas.
* `RestaurantUser` (Weight = 2): Consulta pantalla KDS y confirma comandas listas en mostrador.
* `CourierUser` (Weight = 3): Inicia turno, emite pings GPS, sondea ofertas calificadas, compite por aceptar viajes y avanza los estados de entrega.

### Ejecución Headless y Generación de Reportes:
Con la API levantada en Docker, ejecuta en otra terminal:

```bash
locust -f locustfile.py --headless -u 50 -r 5 --run-time 1m --host http://localhost:8000 --html datos/locust_report.html --csv datos/locust_stats
```

### Ejecución con Interfaz Gráfica:
```bash
locust -f locustfile.py --host http://localhost:8000
```
Accede al panel de control en [http://localhost:8089](http://localhost:8089) para configurar usuarios concurrentes y tasa de spawn.

---

## 6. Telemetría de Sistema en Tiempo Real

El middleware asíncrono en FastAPI intercepta cada solicitud HTTP y escribe de forma atómica en el archivo [`datos/telemetry_log.csv`](datos/telemetry_log.csv):
```csv
timestamp,method,path,status_code,latency_ms,cpu_percent,memory_mb
2026-10-02T17:00:00.123456+00:00,POST,/api/v1/orders/,201,14.25,8.5,42.80
2026-10-02T17:00:01.654321+00:00,GET,/api/v1/orders/1/tracking,200,3.12,9.1,43.10
```

Este registro permite validar el KPI de latencia de backend ($T_{\text{lat\_api\_p99}} \le 180\text{ ms}$) y provee el insumo empírico para el análisis del Integrante 3.

---

## 7. Estructura de Directorios del Repositorio

```text
Modelos - PA/
├── README.md                      # Documentación y comando único de despliegue
├── docker-compose.yml             # Orquestación de servicios (API + PostgreSQL 15)
├── Dockerfile                     # Construcción reproducible de imagen Python 3.11-slim
├── requirements.txt               # Dependencias Python con versiones congeladas
├── locustfile.py                  # Suite de pruebas de carga sintética (Bono +0.2)
├── sistema_real/                  # Código fuente de la API REST real
│   └── app/
│       ├── __init__.py
│       ├── main.py                # Entrada de FastAPI y catálogo de 13 endpoints
│       ├── models.py              # Modelos SQLAlchemy y seeding de 10 locales (47 fogones)
│       ├── schemas.py             # Esquemas de validación Pydantic v2
│       ├── database.py            # Conexión y sesión persistente PostgreSQL 15
│       ├── config.py              # Configuración dinámica en caliente (/config/)
│       ├── dispatch.py            # Motor de despacho, cinemática vial tau=1.25 y FIFO
│       └── telemetry.py           # Middleware de telemetría de latencias y CPU/RAM
├── simulacion/                    # Motor de Simulación DES (SimPy v0 24h)
├── analisis/                      # Contrastes analíticos M/M/c y Ley de Little
├── datos/                         # Persistencia de telemetría y resultados de simulación
│   ├── telemetry_log.csv          # Registro en vivo de peticiones HTTP, CPU y RAM
│   └── simulation_results.json    # Resultados de corridas SimPy
└── docs/                          # Documentación del proyecto de aula
    ├── Asignaciones_Equipo_E1.md  # Matriz de roles y responsabilidades de 3 personas
    ├── Auditoria.md               # Bitácora central, criterios C1-C7 y decisiones D-01 a D-11
    ├── Flujo_Completo_y_Dinamica_24h.md # Especificación del gemelo digital de 24 horas
    └── Planes de Accion/          # Planes modulares 00 al 06
```
