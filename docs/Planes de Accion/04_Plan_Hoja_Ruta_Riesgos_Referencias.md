# PLAN DE ACCIÓN 04: HOJA DE RUTA, RIESGOS Y REFERENCIAS

## Módulos del Documento: 3.11 Hoja de Ruta de Integración y Riesgos, 3.12 Referencias Académicas y Anexo de IA

## Criterios de Rúbrica Asociados: R9 (0.5 parcial), R10 (0.3)

---

### 1. Objetivos del Plan

Planificar la evolución del gemelo digital a través de los módulos III y IV del curso (Entregas 2 y 3), articular la reutilización formal de conceptos y artefactos de cursos previos de la carrera de Ingeniería de Sistemas / Software, diseñar la matriz de gestión de riesgos técnicos y de alcance con planes de mitigación concretos, compilar la bibliografía académica en formato IEEE/APA con al menos 5 fuentes rigurosas, y formalizar la declaración de uso ético y transparente de herramientas de inteligencia artificial.

---

### 2. Estructura y Contenidos Detallados por Sección

#### 2.1 Hoja de Ruta de Integración Modular (Sección 3.11 & Criterio R9)

El proyecto está concebido como una arquitectura evolutiva. Hoja de ruta para su integración con los módulos de la asignatura y otras materias del plan de estudios.

**Integración con Módulos del Curso**

| Módulo | Entregable / Componente a Desarrollar | Entrega |
| :--- | :--- | :---: |
| **Módulo II** | Pruebas de estrés de la API REST usando Locust para capturar telemetría empírica bajo carga (simulación del pico de cena). | Entrega 2 |
| **Módulo III** | Ajuste de distribuciones (KS) y estimación bayesiana con PyMC para calibrar los parámetros de las colas de cocina y fatiga. | Entrega 2 |
| **Módulo IV** | Transición de los repartidores a agentes autónomos (ABM con Mesa) y optimización de la política algorítmica mediante aprendizaje por refuerzo. | Final |

**Integración con Otras Asignaturas**

* **Arquitectura de Software:** Implementación del patrón de diseño *Strategy* para desacoplar las políticas de despacho, y diseño de la API REST bajo el patrón *MVC* (Model-View-Controller) en FastAPI.
* **Bases de Datos:** Uso de bases de datos relacionales (PostgreSQL) para la persistencia transaccional del estado de los pedidos y la telemetría de los repartidores.
* **DevOps / Infraestructura:** Despliegue de los entornos de simulación y la API real mediante contenedores aislados orquestados con Docker Compose.

**Matriz de Riesgos Técnicos**

| Riesgo Técnico | Probabilidad | Impacto | Plan de Contingencia |
| :--- | :---: | :---: | :--- |
| **1. Colapso de la API REST durante pruebas Locust** | Alta | Alto | Limitar la concurrencia progresivamente y escalar el número de *workers* de Uvicorn en Docker para balancear la carga. |
| **2. Error analítico > 5% entre M/M/c y SimPy** | Media | Alto | Incrementar el número de réplicas en SimPy (\(N > 100\)) y verificar el calentamiento del sistema (*warm-up period*). |
| **3. Bloqueo (*deadlock*) de entidades en SimPy** | Baja | Crítico | Implementar *timeouts* de seguridad (abandono) y trazas de depuración (logs) en la cola de cocina. |
| **4. Asincronía de telemetría en el sistema real** | Media | Medio | Emplear *middlewares* no bloqueantes en FastAPI y delegar la escritura del CSV a procesos en segundo plano. |

#### 2.2 Referencias Académicas y Anexo de IA (Sección 3.12 & Criterio R10)

**Referencias Bibliográficas**

1. Bai, J., So, K. C., Tang, C. S., Chen, X., & Wang, H. (2019). "Coordinating supply and demand on an on-demand service platform with impatient customers." *Manufacturing & Service Operations Management*, 21(3), 556–570.
2. Ballou, R. H., Rahardja, H., & Sakai, N. (2002). "Selected properties of Manhattan and Euclidean distances as approximations for network distances." *Computers & Operations Research*, 29(8), 983–1001.
3. Boeing, G. (2019). "Urban spatial order: Street network orientation, configuration, and entropy." *Applied Network Science*, 4(1), 67.
4. Cachon, G. P., Daniels, K. M., & Lobel, R. (2017). "The role of surge pricing on a service platform with customer and provider self-scheduling." *Management Science*, 63(11), 3684–3699.
5. Carroll, A., & Heiser, G. (2010). "An analysis of power consumption in a smartphone." *Proceedings of the 2010 USENIX Annual Technical Conference (USENIX ATC'10)*, Boston, MA, pp. 21–34.
6. Levinson, D., & El-Geneidy, A. (2009). "The circuity of urban travel." *Transportation Research Part A: Policy and Practice*, 43(8), 701–713.
7. Ulmer, M. W., Goodson, J. C., Mattfeld, D. C., & Hennig, M. (2020). "Offline–online approximate dynamic programming for dynamic delivery problems." *European Journal of Operational Research*, 284(2), 577–595.
8. Kleinrock, L. (1975). *Queueing Systems, Volume 1: Theory*. John Wiley & Sons, New York.
9. Law, A. M. (2015). *Simulation Modeling and Analysis* (5th ed.). McGraw-Hill Education, New York.
10. Food and Drug Administration (FDA, 2022). *Food Code 2022: Recommendations of the United States Public Health Service*. U.S. Department of Health and Human Services.
11. Organización Internacional del Trabajo (OIT / ILO, 2021). *World Employment and Social Outlook 2021: The role of digital labour platforms in transforming the world of work*.
12. National Restaurant Association (NRA, 2022). *State of the Restaurant Industry: Kitchen Operations and Production Benchmarks Report*.
13. Deliverect (2023). *Global Consumer Delivery Trends & Thermal Experience Report 2023*.
14. DoorDash Engineering (2020). *Optimizing Kitchen Prep Time and Courier Dispatch Synchronization*.
15. Statista Digital Market Insights (2023). *Online Food Delivery Worldwide: Market Report & Hourly Demand Distribution*.
16. DoorDash, Rappi, & DiDi Food (2022–2023). *Delivery Partner Operational Guidelines & Service Terms*.

**Anexo: Declaración de Uso de Inteligencia Artificial**
Para el desarrollo de este proyecto, el equipo empleó un modelo de lenguaje (LLM) operando como asistente técnico.

* **Herramienta:** Gemini.
* **Uso específico:**
  * **Por parte del Integrante 3:**
    * Soporte en la estructuración de los documentos Markdown y planes de acción.
    * Generación de sintaxis LaTeX y diseño de diagramas UML en formato Mermaid.
    * Validación de las ecuaciones teóricas de Erlang-C.
    * Generación de plantillas base y estructuras algorítmicas en Python para la API REST (FastAPI) y scripts de análisis matemático (`queueing_theory.py`, `metrics.py`, `contrast_analysis.py`).
  * **Por el Integrante 1:**
    * Generación de código estructural en Python aplicando POO y tipado estático para el orquestador de simulación (`simulacion/entities.py`, `simulacion/policies.py`, `simulacion/simpy_engine.py`).
    * Redacción de documentación técnica, tabla de eventos atómicos y diagrama de flujo Mermaid para el ciclo de vida del pedido (Sección 3.6).
* **Verificación:** 
   Todo el texto documentado y el código generado fue auditado, y revisado lógica y matemáticamente por los integrantes del equipo, garantizando que la arquitectura del software, las variables aleatorias y el diseño cumplen estrictamente con las directrices de la asignatura.

---

### 3. Criterios de Aceptación y Verificación

* [ ] La tabla de integración detalla entregables concretos para Módulo II, Módulo III y Módulo IV.

* [ ] Se vincula explícitamente el trabajo con al menos 2 cursos aprobados de la carrera.
* [ ] Se formulan al menos 4 riesgos con probabilidad, impacto y plan de contingencia claro.
* [ ] Se incluyen al menos 5 referencias completas, con al menos 2 libros/papers indexados.
* [ ] El anexo de IA responde transparentemente a los cuatro requerimientos éticos del PDF.
