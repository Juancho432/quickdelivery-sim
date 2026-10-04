# MASTER PLAN — PROYECTO DE AULA: ENTREGA PARCIAL 1

## Plataforma de Pedidos a Domicilio (Simulación Estocástica y Gemelo Digital)

> **Contexto de Sesión y Continuidad:**
> Este documento actúa como el **índice maestro y protocolo de ejecución** del proyecto para cualquier agente o sesión de trabajo. Define el alcance, las dependencias entre módulos, el estado de completitud de cada tarea y las directrices para alcanzar la máxima calificación (**5.0 / 5.0 + 0.2 Bono**) según la rúbrica oficial.

---

### 1. Resumen Ejecutivo del Proyecto Seleccionado

* **Dominio:** Plataforma de despacho y pedidos a domicilio en tiempo real (Food & Groceries Delivery Platform estilo Rappi / DiDi Food).
* **Estructura Obligatoria del Flujo:** **1. Pedidos $\rightarrow$ 2. Asignación $\rightarrow$ 3. Rastreo**.
* **Horizonte de Simulación:** **24 Horas Continuas ($1.440\text{ minutos} = 86.400\text{ segundos}$)**.
* **Capacidad de Cocina (10 Restaurantes, 47 fogones totales):** $k_r \in [3, 6]$ fogones por local; con preparación Log-Normal ($\mu = 18.5\text{ min}$), la capacidad nominal máxima sostenible es $\lambda_{\text{cocina\_max}} = \frac{47}{18.5} \approx \mathbf{2.54\text{ ped/min}}$.
* **Demanda Diaria Calibrada ($\approx 1.890\text{ pedidos/día}$ bajo NHPP):** Alternancia realista entre holgura y sobrecarga transitoria:
  * Madrugada (00:00–06:00): $0.15\text{ ped/min}$ ($\rho=6\%$, vacío).
  * Desayuno (06:00–10:00): $1.00\text{ ped/min}$ ($\rho=39\%$, fluido).
  * Valle Mañana (10:00–11:30): $0.80\text{ ped/min}$ ($\rho=31\%$, holgura).
  * Pico Almuerzo (11:30–14:30): $2.70\text{ ped/min}$ ($\rho=106\%$, saturación moderada y colas de 2-4 comandas).
  * Valle Tarde (14:30–18:30): $1.20\text{ ped/min}$ ($\rho=47\%$, desahogo).
  * **Pico Cena (18:30–22:00): $3.30\text{ ped/min}$ ($\rho=130\%$, saturación severa, colas de 6-10 comandas y cancelaciones).**
  * Cierre Nocturno (22:00–24:00): $0.50\text{ ped/min}$ ($\rho=20\%$, evacuación final).
* **Modelo de Flota: Flota Abierta / Crowdsourcing ($c(t)$ variable):**
  * Repartidores autónomos que se conectan (*login*) mediante NHPP ($\lambda_{\text{login}}(t)$) correlacionado con los picos ($c(t) \in [8, 100]$ couriers) y se desconectan (*logout*) voluntariamente.
  * **Límite Físico Duro ($C6$):** Permanencia máxima de **6 horas continuas ($360\text{ min}$)** por repartidor debido a fatiga psicomotriz (OIT/ILO, 2021) y autonomía de batería de smartphone (4-6h de GPS continuo a 1 Hz, Carroll & Heiser, 2010).
* **Protocolo de Protección en Tránsito y Conexión (Decisión D-08):**
  * *Verificación Preventiva de Batería:* Antes de ofertar, $\text{Bat}_{\text{actual}} - \Delta \text{Bat}_{\text{est}} \ge 15\%$; si no cumple, no califica.
  * *Flexibilidad de Turno de 6h:* Si cumple 6h en ruta con pedido en mano, completa la entrega (`EntregaFinal`) y luego ejecuta `LogoutRepartidor` automático.
  * *Contingencia por Siniestro en Ruta:* Pérdida de señal $> 5\text{ min}$ o falla grave transita a `CANCELADO_INCIDENCIA_TRANSITO` (reembolso total y merma en ruta).
* **Protocolo Anti-Limbo en Mostrador (Decisión D-07):** Reintentos cada 45s con bono fijo de emergencia (+20%); si $t_{\text{mostrador}} \ge 20\text{ min}$, transición a `CANCELADO_SIN_REPARTIDOR` (merma asumida al restaurante y reembolso). Si el repartidor se desconecta antes de recoger, desasignación inmediata y vuelta a cola urgente.
* **Límites del Sistema y Exclusiones Formales (Decisión D-11):** 15 exclusiones rigurosamente justificadas en 5 dominios (Culinario, Vial/Flota, Cliente, Tecnología, Negocio), destacando la exclusión de comensales en salón, semáforos microscópicos, gasolina (el cuello de botella de 6h es la batería del móvil), multientrega (cero batching) y facturación contable.
* **Problema Central:** Desincronización entre la preparación en cocina y el arribo del repartidor. En los picos, la política voraz inmediata hace que el repartidor espere $16.2$ min (o más si hay cola de fogón) inactivo en el restaurante, desperdiciando su ventana de 6h, drenando su batería en reposo y provocando desconexiones tempranas que desabastecen la ciudad.
* **Variable de Decisión Principal ($C4$):**
  * *Política Actual (Línea Base):* Asignación Voraz Inmediata (emparejamiento al entrar la orden).
  * *Política Alternativa (Propuesta):* Despacho Sincronizado Predictivo ($t_{\text{despacho}} = t_{\text{ready}} - t_{\text{viaje}} + \Delta t_{\text{buffer}}$) basado en el tiempo estimado de cocción del restaurante (ETA de cocina), con escalamiento dinámico en dos fases (ventana $[-6, +8]\text{ min}$ y conmutación urgente a bono +20%).
* **Actores Autónomos / Agentes ($C7$):**
  * *Clientes:* Realizan pedidos de comida a domicilio, monitorean el rastreo GPS y cancelan por impaciencia si la espera supera su umbral estocástico (Weibull, $35-45\text{ min}$, con tasa de riesgo acelerada en $+50\%$ si la comida lleva $> 6\text{ min}$ en mostrador).
  * *Restaurantes:* Reciben pedidos, disponen de capacidad finita de cocina ($k_r \in [3, 6]$ fogones, total 47) y tiempos estocásticos de preparación (Log-Normal, $\mu = 18.5\text{ min}$).
  * *Repartidores:* Evalúan viajes según tarifa/distancia, aceptan/rechazan (timeout 45s), transmiten telemetría y se desconectan al cumplir 6 horas o agotar batería ($<15\%$).

---

### 2. Estructura Modular de Planes de Acción (`docs/Planes de Accion/`)

| Archivo                                                       | Secciones del PDF Asociadas                                                                                                                             | Criterios Rúbrica   | Estado                                                  |
| :------------------------------------------------------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------ | :------------------- | :------------------------------------------------------ |
| **`00_Master_Plan.md`**                               | Índice maestro, directrices y estado de ejecución                                                                                                     | R1 – R10 + Bono     | **ACTIVO (Alineado con Opción 1 y D-01 a D-11)** |
| **`01_Plan_Definicion_Sistema_y_Negocio.md`**         | 3.1 Identificación, 3.2 Sistema real & taxonomía, 3.3 Problema & preguntas de decisión, 3.4 Objetivos, 3.5 Alcance & Supuestos (15 exclusiones D-11) | R1, R2, R3           | **COMPLETADO (Alineado con D-11)**                |
| **`02_Plan_Modelo_Conceptual_DES_y_Teoria_Colas.md`** | 3.6 Modelo Conceptual DES, 3.7 Análisis analítico con Teoría de Colas                                                                                | R4, R5               | **LISTO PARA REDACTAR (Diseño cerrado)**         |
| **`03_Plan_Parametros_Metricas_Diseno_POO.md`**       | 3.8 Parámetros & plan de datos, 3.9 KPIs, 3.10 Clases POO (Strategy)                                                                                   | R6, R7, R9 (parcial) | **LISTO PARA REDACTAR (Diseño cerrado)**         |
| **`04_Plan_Hoja_Ruta_Riesgos_Referencias.md`**        | 3.11 Integración & riesgos, 3.12 Referencias IEEE/APA & Anexo IA                                                                                       | R9, R10              | **LISTO PARA REDACTAR (Diseño cerrado)**         |
| **`05_Plan_Prototipo_Tecnico_y_Simulacion.md`**       | 4. Prototipo técnico: API REST (Docker + Postgres), Telemetría, SimPy v0, Contraste $M/M/c$, Locust (Bono)                                           | R8, Bono (+0.2)      | **PARCIALMENTE COMPLETADO (API, Docker, Telemetría y Locust listos; SimPy y Contraste pendientes)** |
| **`06_Plan_Implementacion_API_FastAPI_Locust.md`**   | 4. API REST FastAPI, PostgreSQL 15, Telemetría, requirements.txt, Docker Compose y Locust (Bono +0.2) - Integrante 2                                  | C1, C2, R8, Bono     | **COMPLETADO (13 endpoints, Docker Compose, Telemetría y Locust verificados)** |

### 2.1 Archivo Maestro de Auditoría, Decisiones y Rúbrica (`docs/Auditoria.md`)

> **DIRECTRIZ OPERATIVA PERMANENTE PARA TODOS LOS AGENTES:**El archivo [`docs/Auditoria.md`](../Auditoria.md) es el **cuaderno de bitácora central y archivo de auditoría formal** del proyecto.
>
> * **¿Qué contiene este archivo?:**
>
>   1. **Auditoría de Criterios Oficiales:** Verificación punto por punto de los **7 Criterios de Elegibilidad (C1 a C7)** y los **10 Criterios de Rúbrica (R1 a R10 + Bono de +0.2)**, demostrando el cumplimiento para obtener la calificación máxima (**5.0 / 5.0 + 0.2**).
>   2. **Mapa de Huecos Técnicos (H-01 a H-11):** Historial de vacíos, ambigüedades e inconsistencias identificadas y resueltas durante el diseño.
>   3. **Registro de Decisiones Acordadas (D-01 a D-11):** Resoluciones formales adoptadas con el equipo (dinámica NHPP de logins, escalamiento con buffer $\Delta t_{\text{buffer}}$, arquitectura Docker con PostgreSQL 15, protocolos anti-limbo y contingencia, KDS, desacoplamiento estricto SimPy vs. API, y las 15 exclusiones del modelo).
>   4. **Plan de Cambios:** Lista de verificación de tareas de redacción y desarrollo técnico.
> * **¿Qué debe registrar y guardar cualquier agente en `docs/Auditoria.md`?:**
>
>   - **Nuevas brechas o dudas:** Si surge una inconsistencia o aspecto no definido, registrarla en el Mapa de Huecos con código secuencial (`H-12`, `H-13`, ...).
>   - **Nuevas decisiones técnicas o de arquitectura:** Registrar la resolución con código secuencial (`D-12`, `D-13`, ...), explicando su justificación, fuentes bibliográficas y su correspondencia transaccional en SimPy y en los endpoints de FastAPI.
>   - **Evidencias de rúbrica:** Conforme se desarrollen los módulos de código (API, Docker, SimPy, Locust), actualizar las tablas de verificación para mantener la trazabilidad ante sustentaciones.

### 2.2 Matriz de Asignaciones del Equipo de 3 Personas (`docs/Asignaciones_Equipo_E1.md`)

> **ASIGNACIÓN INDIVIDUAL DE TRABAJO:**
> * **Integrante 1 (Modelos):** Modelo conceptual DES (Sección 3.6), formalización de eventos, entidades y recursos, motor de simulación SimPy v0 de 24 horas (`simulacion/`) y políticas de despacho (patrón Strategy).
> * **Integrante 2 (Infraestructura):** API REST en FastAPI (`sistema_real/`), persistencia PostgreSQL 15, orquestación `docker-compose.yml`, middleware de telemetría y pruebas de carga sintética con Locust (`locustfile.py`, Bono +0.2).
> * **Integrante 3 (Análisis de Datos):** Formulación analítica de teoría de colas $M/M/c$ (Sección 3.7), scripts de contraste analítico (`analisis/`) y explicación de disparidad con SimPy, parámetros y distribuciones con fuentes comprobables (3.8), 6 KPIs con percentiles (3.9), diseño de clases POO Strategy (3.10), matriz de riesgos (3.11), compendio de referencias IEEE/APA y anexo de IA (3.12), y colector de métricas (`simulacion/metrics.py`).

---

### 3. Matriz de Tareas y Control de Avance

- [X] **Fase 0: Análisis de Requisitos y Elección de Problema:**
  - [X] Extracción y análisis de las 10 páginas del PDF de la entrega.
  - [X] Diseño de planes modulares en `docs/Planes de Accion/`.
  - [X] Formulación de dinámicas 24h, flotas abiertas, calibración de fogones y demanda en `docs/Flujo_Completo_y_Dinamica_24h.md`.
  - [X] Aprobación y selección de la **Opción 1 (Despacho Sincronizado)** por parte del equipo.
  - [X] Auditoría de huecos no definidos y resolución formal de Decisiones D-01 a D-11 en [`docs/Auditoria.md`](../Auditoria.md).
- [X] **Fase 1: Ejecución del Plan 01 (Secciones 3.1 a 3.5):**
  - [X] Actualización de especificaciones de Plan 01 para Opción 1.
  - [X] Redacción formal exhaustiva de las Secciones 3.1 a 3.5 en `docs/Planteamiento_Proyecto.md`.
- [ ] **Fase 2: Ejecución del Plan 02 (Secciones 3.6 y 3.7):**
  - [ ] Modelo conceptual DES con 10 eventos, 3 agentes, protocolos anti-limbo y contingencia en tránsito, y tabla evento-estado.
  - [ ] Formulación analítica $M/M/c$, deducción paso a paso y verificación de Ley de Little ($L = \lambda W$).
- [ ] **Fase 3: Ejecución del Plan 03 (Secciones 3.8 a 3.10):**
  - [ ] Tabla de parámetros continuos (NHPP logins, batería, sinuosidad $\tau=1.25$, tiempos de cocción Log-Normal).
  - [ ] 6 KPIs cuantificables con percentiles ($p95, p99$) y métrica de enfriamiento en mostrador ($T_{\text{mostrador\_p95}}$).
  - [ ] Diagrama de clases POO con patrón Strategy puro para Opción 1 y puntos de extensión (Módulos II, III y IV).
- [ ] **Fase 4: Ejecución del Plan 04 (Secciones 3.11 y 3.12):**
  - [ ] Hoja de ruta modular, matriz de 4 riesgos con contingencias D-07/D-08, referencias IEEE/APA y anexo de IA.
- [ ] **Fase 5: Prototipo Técnico y Simulación (Plan 05 y Plan 06):**
  - [X] API REST Dockerizada con FastAPI + PostgreSQL 15 y telemetría integrada a `datos/telemetry_log.csv` (13 endpoints REST implementados y probados).
  - [X] Suite modular de pruebas unitarias e integración en `tests/` con `TestClient` (34 tests con 100% éxito cubriendo caminos positivos y negativos, desacoplada por clases temáticas y documentada en `docs/Documentacion_Pruebas_Unitarias_y_API.md`).
  - [ ] Modelo SimPy v0 ejecutable de 24h con semilla fija.
  - [ ] Script de contraste numérico $M/M/c$ vs SimPy con error $< 5\%$.
  - [X] Bono con Locust (`locustfile.py`) con 3 perfiles concurrentes (Cliente, Restaurante y Repartidor) y reportes generados con 0% fallos.
