# PLAN DE ACCIÓN 04: HOJA DE RUTA, RIESGOS Y REFERENCIAS
## Módulos del Documento: 3.11 Hoja de Ruta de Integración y Riesgos, 3.12 Referencias Académicas y Anexo de IA
## Criterios de Rúbrica Asociados: R9 (0.5 parcial), R10 (0.3)

---

### 1. Objetivos del Plan
Planificar la evolución del gemelo digital a través de los módulos III y IV del curso (Entregas 2 y 3), articular la reutilización formal de conceptos y artefactos de cursos previos de la carrera de Ingeniería de Sistemas / Software, diseñar la matriz de gestión de riesgos técnicos y de alcance con planes de mitigación concretos, compilar la bibliografía académica en formato IEEE/APA con al menos 5 fuentes rigurosas, y formalizar la declaración de uso ético y transparente de herramientas de inteligencia artificial.

---

### 2. Estructura y Contenidos Detallados por Sección

#### 2.1 Hoja de Ruta de Integración Modular (Sección 3.11 & Criterio R9)
* **Tabla de Integración por Módulos y Entregas:**
  | Entrega | Módulo del Curso | Componente a Desarrollar | Artefacto Generado / Entregable |
  | :--- | :--- | :--- | :--- |
  | **Entrega 1 (Semanas 1–7)** | Módulo I: DES y Teoría de Colas | Modelo SimPy v0, API REST Dockerizada, formulación $M/M/c$ y contraste numérico | Repositorio funcional, simulación base, documento de planteamiento |
  | **Entrega 2 (Semanas 8–12)** | Módulo II: Telemetría & Pruebas de Carga; Módulo III: Inferencia Bayesiana & PINN | Pruebas de estrés con Locust, telemetría real de latencia/CPU, calibración bayesiana con PyMC, modelo subrogado con restricciones duras de hardware | Pipelines de telemetría, notebooks de ajuste bayesiano, predictor neuronal híbrido |
  | **Entrega Final (Semanas 13–16)** | Módulo IV: Modelado Multiagente & Optimización | Agentes autónomos de decisión con Mesa (repartidores y clientes adaptativos), integración bidireccional gemelo digital con API real, agente de despacho con RL | Gemelo digital conectado en tiempo real, dashboard de sustentación, demostración en vivo |

* **Relación Explícita con Cursos de la Carrera:**
  * *1. Arquitectura de Software:* Reutilización del patrón arquitectural de Microservicios desacoplados (API Gateway + Workers asíncronos), aplicación de patrones de diseño GoF (Strategy para algoritmos de asignación, Observer para el colector de métricas).
  * *2. DevOps y Computación en la Nube:* Reutilización de contenedores Docker multi-stage, orquestación local con Docker Compose, definición de pipelines de pruebas automatizadas y monitorización de telemetría de contenedores.
  * *3. Bases de Datos:* Diseño del esquema relacional en PostgreSQL 15 (`postgres:15-alpine`) para transacciones de pedidos (`Order`), couriers (`Courier`) y telemetría (`TrackingRecord`), gestionando índices B-tree, persistencia con volúmenes montados y control de concurrencia bajo alta tasa de escrituras simultáneas (Decisión D-04).

* **Matriz de Riesgos Técnicos y de Alcance (Mínimo 4 Riesgos):**
  | # | Riesgo Identificado | Tipo | Probabilidad | Impacto | Plan de Contingencia / Mitigación |
  | :---: | :--- | :---: | :---: | :---: | :--- |
  | **R-01** | La API real experimenta latencias excesivas o caídas bajo inyección de carga con Locust, impidiendo capturar telemetría confiable. | Técnico | Media | Alto | Implementar limitación de tasa (*rate limiting*) en endpoints no críticos y desplegar workers con escalado horizontal local (`docker compose up --scale api=3`). |
  | **R-02** | Dificultad en la convergencia de cadenas MCMC en PyMC para la estimación de parámetros de la Entrega 2. | Técnico | Media | Medio | Utilizar priors informativos basados en la literatura empírica de delivery y emplear métodos variacionales (ADVI) como paso previo a NUTS. |
  | **R-03** | Sobredimensionamiento del alcance al intentar simular redes viales complejas con enrutamiento GIS en tiempo real. | Alcance | Alta | Alto | Delimitar la distancia espacial a distancias métricas de Manhattan corregidas por factor empírico de sinuosidad vial urbana ($\tau = 1.25$, Ballou et al., 2002; Boeing, 2019). |
  | **R-04** | Desajuste severo entre la salida del modelo SimPy v0 y el modelo analítico $M/M/c$ debido a condiciones de frontera no estacionarias. | Metodológico | Baja | Medio | Desacoplar metodológicamente: construir un script de contraste canónico puramente markoviano en `analisis/` ($\lambda, \mu$ exponenciales, flota fija, sin abandonos) garantizando error $< 5\%$ y Ley de Little (Decisión D-03). |
  | **R-05** | Desconexiones de repartidores con pedidos en mano o pedidos en el limbo por rechazo masivo en mostrador. | Operacional / Lógica | Media | Alto | Implementar protocolo de 3 capas (filtro preventivo de batería $\ge 15\%$, flexibilidad de turno para culminar entregas en curso, y estado `CANCELADO_INCIDENCIA_TRANSITO`) junto al protocolo anti-limbo en mostrador con merma a los 20 min (`CANCELADO_SIN_REPARTIDOR`) (Decisiones D-07 y D-08). |

#### 2.2 Referencias Académicas y Anexo de IA (Sección 3.12 & Criterio R10)
* **Referencias Bibliográficas (Formato IEEE / APA, Mínimo 5 Fuentes):**
  1. *Libro clásico de simulación:* Law, A. M. (2015). *Simulation Modeling and Analysis* (5th ed.). McGraw-Hill Education.
  2. *Libro de teoría de colas:* Kleinrock, L. (1975). *Queueing Systems, Volume 1: Theory*. John Wiley & Sons.
  3. *Paper indexado sobre despacho de delivery:* Ulmer, M. W., Goodson, J. C., Mattfeld, D. C., & Hennig, M. (2020). "Offline–online approximate dynamic programming for dynamic delivery problems." *European Journal of Operational Research*, 284(2), 577-595.
  4. *Paper sobre plataformas on-demand y clientes impacientes:* Bai, J., So, K. C., Tang, C. S., Chen, X., & Wang, H. (2019). "Coordinating supply and demand on an on-demand service platform with impatient customers." *Manufacturing & Service Operations Management*, 21(3), 556-570.
  5. *Paper sobre sinuosidad vial urbana ($\tau = 1.25$):* Ballou, R. H., Rahardja, H., & Sakai, N. (2002). "Selected Properties of Manhattan and Euclidean Distances as Approximations for Network Distances." *Computers & Operations Research*, 29(8), 983–1001.
  6. *Paper sobre circuity en transporte urbano:* Levinson, D., & El-Geneidy, A. (2009). "The circuity of urban travel." *Transportation Research Part A: Policy and Practice*, 43(8), 701-713.
  7. *Estudio de consumo energético en smartphones (GPS continuo):* Carroll, A., & Heiser, G. (2010). "An Analysis of Power Consumption in a Smartphone." *USENIX Annual Technical Conference*, 21-34.
  8. *Documentación técnica SimPy:* Team SimPy. (2024). *SimPy: Event Discrete Simulation for Python*, Version 4.1. Documentation: https://simpy.readthedocs.io/
* **Anexo Obligatorio de Declaración de Uso de Inteligencia Artificial:**
  * *Herramienta utilizada:* Antigravity AI Assistant (Google DeepMind).
  * *Propósito:* Soporte en la estructuración de documentos markdown, diseño de diagramas Mermaid, generación de plantillas de código para FastAPI/SimPy y revisión de coherencia de fórmulas matemáticas.
  * *Secciones intervenidas:* Estructuración de planes de acción, esqueletos de código y formato de tablas de contraste.
  * *Verificación humana del grupo:* Los integrantes del grupo verificaron y validaron la deducción de fórmulas de teoría de colas ($M/M/c$), calcularon manualmente los parámetros de prueba, adaptaron la lógica de negocio al dominio de pedidos a domicilio y probaron la ejecución local en contenedores.

---

### 3. Criterios de Aceptación y Verificación
- [ ] La tabla de integración detalla entregables concretos para Módulo II, Módulo III y Módulo IV.
- [ ] Se vincula explícitamente el trabajo con al menos 2 cursos aprobados de la carrera.
- [ ] Se formulan al menos 4 riesgos con probabilidad, impacto y plan de contingencia claro.
- [ ] Se incluyen al menos 5 referencias completas, con al menos 2 libros/papers indexados.
- [ ] El anexo de IA responde transparentemente a los cuatro requerimientos éticos del PDF.
