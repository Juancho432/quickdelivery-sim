# DOCUMENTACIÓN DE PRUEBAS UNITARIAS Y DE FLUJO — API REST (FastAPI)
## Plataforma de Pedidos a Domicilio (*QuickDelivery Sim*) — Entrega Parcial 1

> **Gobernanza y Propósito:**  
> Este documento detalla la arquitectura, alcance, diseño modular y matriz de verificación de la suite de pruebas unitarias y de integración de la API REST del sistema real. La suite valida integralmente el catálogo de 13 endpoints transaccionales, las reglas de negocio de despacho, la cinemática vial urbana ($\tau = 1.25$) y las decisiones arquitectónicas acordadas (**D-01 a D-11**) en [`docs/Auditoria.md`](Auditoria.md).

---

## 1. Arquitectura y Módulos de Prueba

La suite está construida aprovechando el módulo oficial de pruebas de FastAPI: **`fastapi.testclient.TestClient`** (construido sobre Starlette y HTTPX).

Para garantizar mantenibilidad, aislamiento y permitir la ejecución independiente de cualquier archivo, la suite fue desacoplada en **un archivo por cada clase temática** dentro del directorio `tests/`:

```text
tests/
├── __init__.py                  # Marcador de paquete
├── base.py                      # Clase base TestQuickDeliveryAPIBase, setup de TestClient y helpers
├── test_devops_telemetry.py     # Clase TestDevOpsAndTelemetry (Endpoint E13 y Middleware)
├── test_config.py               # Clase TestSystemConfiguration (Endpoint E12: GET/PUT)
├── test_orders.py               # Clase TestClientOrderFlow (Endpoints E1, E2, E3 y Fogones)
├── test_kds.py                  # Clase TestKitchenKDSFlow (Endpoints E4, E5 y KDS)
├── test_couriers.py             # Clase TestCourierLifecycleAndDispatch (Endpoints E6–E11)
├── test_business_logic.py       # Clase TestBusinessLogicAndEdgeCases (D-07, D-08, tau=1.25)
├── test_end_to_end.py           # Clase TestEndToEndCompleteFlows (Ciclos completos multi-actor)
├── test_live_api.py             # Clase TestLiveApiConnectivity (Socket real http://localhost:8000)
└── test_api.py                  # Agregador maestro (ejecuta todas las suites en un solo comando)
```

---

## 2. Descripción de Archivos por Clase Temática

### 2.1 `tests/base.py` — `TestQuickDeliveryAPIBase`
* **Propósito:** Provee la inicialización común del `TestClient(app)`, asegura la presencia de las tablas y los datos semilla (`seed_database`) e implementa el método `setUp()` que reinicia los parámetros del singleton `system_config` y limpia las tablas transaccionales (`orders` y `tracking_records`) antes de cada caso de prueba.
* **Helper de Repartidores:** Provee `create_courier(...)` para instanciar repartidores con atributos limpios y evitar errores de desconexión o instancias desvinculadas (`DetachedInstanceError`).

### 2.2 `tests/test_devops_telemetry.py` — `TestDevOpsAndTelemetry`
* **Endpoints Evaluados:** `GET /api/v1/telemetry/health` (E13) y `TelemetryMiddleware`.
* **Pruebas:**
  * `test_healthcheck_positive`: Verifica respuesta `200 OK`, `status == "healthy"`, `database == "connected"`, porcentaje de CPU, consumo de memoria en MB (`psutil`) y tiempo de actividad.
  * `test_telemetry_middleware_latency_recording`: Confirma que las peticiones HTTP registran latencias atómicas en telemetría.

### 2.3 `tests/test_config.py` — `TestSystemConfiguration`
* **Endpoints Evaluados:** `GET /api/v1/config/` y `PUT /api/v1/config/` (E12).
* **Pruebas:**
  * `test_get_config_positive`: Comprueba la consulta de los 6 parámetros operativos en caliente.
  * `test_update_config_positive`: Modifica la política activa (`synchronized` $\rightarrow$ `greedy`) y $\Delta t_{\text{buffer}}$, validando persistencia en consultas posteriores.
  * `test_update_config_negative_out_of_bounds`: Verifica que valores fuera de rango (ej. buffer $> 5.0$ min o batería $> 30\%$) son rechazados con código `422 Unprocessable Entity`.

### 2.4 `tests/test_orders.py` — `TestClientOrderFlow`
* **Endpoints Evaluados:** `POST /api/v1/orders/` (E1), `GET /api/v1/orders/{id}/tracking` (E2), `POST /api/v1/orders/{id}/cancel` (E3).
* **Pruebas:**
  * `test_create_order_positive_free_burners`: Con fogones disponibles, el pedido entra directo a `EN_PREPARACION` con $\text{ETA} = 18.5\text{ min}$.
  * `test_create_order_positive_burners_saturation_and_queueing`: Al saturar los $k_r$ fogones, los pedidos excedentes encolan en `EN_COLA_COCINA` y su $\text{ETA}$ se incrementa de forma proporcional a la cola.
  * `test_create_order_negative_validation_errors`: Validación de cuadrante metropolitano $[0.0, 6.0]\text{ km}$ e ID de restaurante $\in [1, 10]$ (`422`).
  * `test_tracking_order_positive_unassigned_and_assigned`: Rastreo antes de asignación (coordenadas nulas) y después de asignación (coordenadas del courier, cálculo de distancia vial y tiempo estimado).
  * `test_tracking_order_negative_not_found`: Rastreo de orden inexistente retorna `404 Not Found`.
  * `test_cancel_order_positive_and_fifo_promotion`: Cancelación voluntaria en fogón libera el recurso y promueve automáticamente la orden FIFO más antigua en `EN_COLA_COCINA` a `EN_PREPARACION`.
  * `test_cancel_order_negative_already_delivered_or_not_found`: Cancelar orden ya entregada retorna `400 Bad Request`; orden inexistente retorna `404 Not Found`.

### 2.5 `tests/test_kds.py` — `TestKitchenKDSFlow`
* **Endpoints Evaluados:** `GET /api/v1/restaurants/{id}/orders` (E4), `POST /api/v1/orders/{id}/ready` (E5).
* **Pruebas:**
  * `test_get_kds_orders_positive_and_exclusion_2`: Verifica que el KDS lista pedidos sin exponer recetas ni ingredientes (**Exclusión Culinaria 2 - Decisión D-11**).
  * `test_get_kds_orders_with_status_filter`: Comprueba el filtrado por query param `?status_filter=EN_PREPARACION`.
  * `test_mark_order_ready_positive_and_fifo_promotion`: Pase a mostrador (`LISTO_EN_MOSTRADOR`), activación de bono urgente (`is_urgent=True`) y promoción FIFO de la siguiente comanda en espera.
  * `test_mark_order_ready_negative_not_found`: Notificación de orden inexistente retorna `404 Not Found`.

### 2.6 `tests/test_couriers.py` — `TestCourierLifecycleAndDispatch`
* **Endpoints Evaluados:** `POST /couriers/login` (E6), `POST /couriers/{id}/location` (E7), `GET /couriers/{id}/offers` (E8), `POST /orders/{id}/accept` (E9), `PATCH /orders/{id}/status` (E10), `POST /couriers/{id}/logout` (E11).
* **Pruebas:**
  * `test_courier_login_positive`: Registro de inicio de turno (límite de 6h y batería inicial).
  * `test_courier_login_negative_invalid_coordinates`: Coordenadas inválidas devuelven `422`.
  * `test_courier_location_update_positive`: Pings GPS y persistencia en tabla `tracking_records`.
  * `test_courier_location_update_negative_not_found_or_inactive`: Reporte de courier inexistente o inactivo devuelve `404`.
  * `test_courier_offers_positive_and_bonus_calculation`: Ofertas JIT con cinemática vial y cálculo de tarifa con recargo urgente (+20%) para comanda lista en mostrador.
  * `test_courier_offers_negative_low_battery_exclusion`: Filtro preventivo D-08 excluye repartidores si su batería estimada es $< 15\%$.
  * `test_accept_order_atomic_positive_and_negative_race_condition`: Asignación con bloqueo de fila (`SELECT FOR UPDATE`). El primer courier gana; el segundo recibe `409 Conflict`.
  * `test_accept_order_negative_unavailable_courier`: Repartidor ocupado o inactivo no califica (`400 Bad Request`).
  * `test_order_status_transitions_positive_full_cycle`: Transición secuencial de hitos (`LlegadaARestaurante` $\rightarrow$ `EN_TRANSITO_CLIENTE` $\rightarrow$ `ENTREGADO`).
  * `test_order_status_transitions_negative_unauthorized_and_invalid`: Repartidor no asignado intentando modificar la comanda recibe `403 Forbidden`; estado no válido recibe `400 Bad Request`.
  * `test_courier_logout_positive_and_negative`: Desconexión formal exitosa (`200`) y control de inexistente (`404`).

### 2.7 `tests/test_business_logic.py` — `TestBusinessLogicAndEdgeCases`
* **Reglas Evaluadas:** Decisiones **D-07**, **D-08** y **D-11 (Exclusión 4)**.
* **Pruebas:**
  * `test_vial_kinematics_and_sinuosity_factor`: Distancia Manhattan multiplicada exactamente por $\tau = 1.25$ y tiempo de viaje estimado a $18\text{ km/h}$.
  * `test_anti_limbo_timeout_counter_d07`: Si una orden supera el tiempo máximo en mostrador sin repartidor (`anti_limbo_max_counter_min`), transiciona automáticamente a `CANCELADO_SIN_REPARTIDOR` con motivo `COUNTER_TIMEOUT_20MIN`.
  * `test_courier_auto_logout_on_delivery_d08`: Regla de flexibilidad operativa; si el repartidor completa su entrega con batería $< 15\%$ o habiendo superado su turno de 6 horas, se ejecuta *auto-logout* formal.

### 2.8 `tests/test_end_to_end.py` — `TestEndToEndCompleteFlows`
* **Flujos Evaluados:** Interacción orquestada multi-actor.
* **Pruebas:**
  * `test_end_to_end_successful_delivery_lifecycle`: Ciclo completo desde la creación del cliente hasta la entrega final y liberación del repartidor para nuevas ofertas.
  * `test_end_to_end_transit_incident_lifecycle`: Contingencia por siniestro en ruta (`CANCELADO_INCIDENCIA_TRANSITO`) que preserva la disponibilidad del conductor.
  * `test_end_to_end_customer_cancel_frees_assigned_courier`: Cancelación voluntaria del cliente con repartidor asignado libera al repartidor de inmediato.

### 2.9 `tests/test_live_api.py` — `TestLiveApiConnectivity`
* **Objetivo:** Verifica la conectividad por socket HTTP real contra `http://localhost:8000` (FastAPI activo en Docker/Host) y la disponibilidad de la documentación interactiva Swagger en `/docs`.

---

## 3. Matriz Completa de Casos de Prueba (34 Casos)

| # | Archivo | Método de Prueba | Endpoint / Lógica | Entrada / Condición | Código HTTP | Resultado Esperado |
| :-: | :--- | :--- | :--- | :--- | :-: | :--- |
| **1** | `test_devops_telemetry.py` | `test_healthcheck_positive` | `GET /telemetry/health` | Ninguna | `200 OK` | `status="healthy"`, `database="connected"`. |
| **2** | `test_devops_telemetry.py` | `test_telemetry_middleware_latency_recording` | Middleware | Petición HTTP | `200 OK` | Registro de métrica de latencia y CPU/RAM. |
| **3** | `test_config.py` | `test_get_config_positive` | `GET /config/` | Ninguna | `200 OK` | 6 parámetros del sistema retornados. |
| **4** | `test_config.py` | `test_update_config_positive` | `PUT /config/` | Payload válido | `200 OK` | Política y buffer actualizados en caliente. |
| **5** | `test_config.py` | `test_update_config_negative_out_of_bounds` | `PUT /config/` | `buffer=9.9`, `bat=45%` | `422 Unprocessable` | Rechazo por validación Pydantic. |
| **6** | `test_orders.py` | `test_create_order_positive_free_burners` | `POST /orders/` | Fogones libres | `201 Created` | Estado `EN_PREPARACION`, $\text{ETA}=18.5$. |
| **7** | `test_orders.py` | `test_create_order_positive_burners_saturation_and_queueing` | `POST /orders/` | Fogones llenos | `201 Created` | Estado `EN_COLA_COCINA`, $\text{ETA}$ incremental. |
| **8** | `test_orders.py` | `test_create_order_negative_validation_errors` | `POST /orders/` | Coords $<0$ o $>6$, rest $99$ | `422 Unprocessable` | Rechazo de parámetros fuera de cuadrante. |
| **9** | `test_orders.py` | `test_tracking_order_positive_unassigned_and_assigned` | `GET /orders/{id}/tracking` | Sin/con courier | `200 OK` | Coords y distancia vial con $\tau=1.25$. |
| **10** | `test_orders.py` | `test_tracking_order_negative_not_found` | `GET /orders/{id}/tracking` | ID inexistente ($999999$) | `404 Not Found` | Mensaje de orden no encontrada. |
| **11** | `test_orders.py` | `test_cancel_order_positive_and_fifo_promotion` | `POST /orders/{id}/cancel` | Orden en preparación | `200 OK` | Cancelada y promoción FIFO automática. |
| **12** | `test_orders.py` | `test_cancel_order_negative_already_delivered_or_not_found` | `POST /orders/{id}/cancel` | Orden entregada o falsa | `400 / 404` | No cancelable en estado final. |
| **13** | `test_kds.py` | `test_get_kds_orders_positive_and_exclusion_2` | `GET /restaurants/{id}/orders` | Cocina KDS | `200 OK` | Sin recetas ni ingredientes (**D-11 Excl-2**). |
| **14** | `test_kds.py` | `test_get_kds_orders_with_status_filter` | `GET /restaurants/{id}/orders` | `?status_filter=...` | `200 OK` | Filtrado estricto por estado. |
| **15** | `test_kds.py` | `test_mark_order_ready_positive_and_fifo_promotion` | `POST /orders/{id}/ready` | Comanda cocinada | `200 OK` | `LISTO_EN_MOSTRADOR`, bono urgente y FIFO. |
| **16** | `test_kds.py` | `test_mark_order_ready_negative_not_found` | `POST /orders/{id}/ready` | ID falso | `404 Not Found` | Error 404 controlado. |
| **17** | `test_couriers.py` | `test_courier_login_positive` | `POST /couriers/login` | Conexión NHPP | `201 Created` | Inicio de turno (6h máx) y batería. |
| **18** | `test_couriers.py` | `test_courier_login_negative_invalid_coordinates` | `POST /couriers/login` | Coordenada $7.0 > 6.0$ | `422 Unprocessable` | Validación Pydantic de cuadrante. |
| **19** | `test_couriers.py` | `test_courier_location_update_positive` | `POST /couriers/{id}/location` | Ping GPS y batería | `200 OK` | Registro en `tracking_records`. |
| **20** | `test_couriers.py` | `test_courier_location_update_negative_not_found_or_inactive` | `POST /couriers/{id}/location` | Courier inactivo o falso | `404 Not Found` | Error 404 controlado. |
| **21** | `test_couriers.py` | `test_courier_offers_positive_and_bonus_calculation` | `GET /couriers/{id}/offers` | Orden en mostrador | `200 OK` | Tarifa con bono urgente $+20\%$. |
| **22** | `test_couriers.py` | `test_courier_offers_negative_low_battery_exclusion` | `GET /couriers/{id}/offers` | Batería $< 15\%$ | `200 OK` | Array vacío (exclusión preventiva D-08). |
| **23** | `test_couriers.py` | `test_accept_order_atomic_positive_and_negative_race_condition` | `POST /orders/{id}/accept` | 2 couriers simultáneos | `200 / 409` | El 1ro asigna; el 2do recibe `409 Conflict`. |
| **24** | `test_couriers.py` | `test_accept_order_negative_unavailable_courier` | `POST /orders/{id}/accept` | Courier ocupado | `400 Bad Request` | Courier no disponible. |
| **25** | `test_couriers.py` | `test_order_status_transitions_positive_full_cycle` | `PATCH /orders/{id}/status` | Hitos 1, 2 y 3 | `200 OK` | Llegada $\rightarrow$ Recogida $\rightarrow$ Entrega. |
| **26** | `test_couriers.py` | `test_order_status_transitions_negative_unauthorized_and_invalid` | `PATCH /orders/{id}/status` | Courier no dueño / fake | `403 / 400` | `403 Forbidden` y `400 Bad Request`. |
| **27** | `test_couriers.py` | `test_courier_logout_positive_and_negative` | `POST /couriers/{id}/logout` | Cierre de turno | `200 / 404` | Courier pasa a inactivo y no disponible. |
| **28** | `test_business_logic.py` | `test_vial_kinematics_and_sinuosity_factor` | Cinemática vial | $\Delta x=2, \Delta y=3$ | N/A | Distancia $= 6.25\text{ km}$, $t=20.83\text{ min}$. |
| **29** | `test_business_logic.py` | `test_anti_limbo_timeout_counter_d07` | Anti-Limbo (D-07) | Mostrador $> 20\text{ min}$ | `200 OK` | `CANCELADO_SIN_REPARTIDOR`. |
| **30** | `test_business_logic.py` | `test_courier_auto_logout_on_delivery_d08` | Límite D-08 | Entrega con batería $<15\%$ | `200 OK` | *Auto-logout* forzado tras entrega. |
| **31** | `test_end_to_end.py` | `test_end_to_end_successful_delivery_lifecycle` | E2E Completo | 3 Actores coordinados | Múltiples | Entrega exitosa y courier liberado. |
| **32** | `test_end_to_end.py` | `test_end_to_end_transit_incident_lifecycle` | Contingencia E2E | Siniestro en viaje | `200 OK` | Incidencia en tránsito y courier liberado. |
| **33** | `test_end_to_end.py` | `test_end_to_end_customer_cancel_frees_assigned_courier` | Cancelación E2E | Cliente cancela asignado | `200 OK` | Cancelación cliente y courier liberado. |
| **34** | `test_live_api.py` | `test_live_server_health_and_docs` | Socket `:8000` | Host en vivo | `200 OK` | Salud de Uvicorn y Swagger UI en `/docs`. |

---

## 4. Guía de Ejecución

Todos los archivos contienen el ajuste de `sys.path` en su cabecera, permitiendo su ejecución desde la raíz o dentro de cualquier subdirectorio:

### Ejecutar toda la suite consolidada:
```bash
.venv\Scripts\python.exe tests/test_api.py
```

### Ejecutar mediante el descubridor estándar de `unittest`:
```bash
.venv\Scripts\python.exe -m unittest discover tests -v
```

### Ejecutar módulos temáticos individuales:
```bash
# Solo pedidos y cocina
.venv\Scripts\python.exe tests/test_orders.py
.venv\Scripts\python.exe tests/test_kds.py

# Solo repartidores y asignación
.venv\Scripts\python.exe tests/test_couriers.py

# Solo reglas de negocio y cinemática
.venv\Scripts\python.exe tests/test_business_logic.py

# Solo flujos de punta a punta (End-to-End)
.venv\Scripts\python.exe tests/test_end_to_end.py

# Solo configuración y telemetría
.venv\Scripts\python.exe tests/test_config.py
.venv\Scripts\python.exe tests/test_devops_telemetry.py
```
