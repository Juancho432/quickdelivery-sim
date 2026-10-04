# PLAN DE ACCIÓN 02: MODELO CONCEPTUAL DES Y TEORÍA DE COLAS
## Módulos del Documento: 3.6 Modelo Conceptual DES (Pasos 1–6), 3.7 Análisis Analítico Preliminar con Teoría de Colas
## Criterios de Rúbrica Asociados: R4 (0.8), R5 (0.6)

---

### 1. Objetivos del Plan
Formalizar el modelo conceptual de Simulación de Eventos Discretos (DES) que gobierna el flujo de pedidos a domicilio, estableciendo las entidades, recursos finitos, variables de estado, eventos atómicos y diagrama de flujo con abandonos y reprocesos. Simultáneamente, formular y resolver el modelo analítico de teoría de colas ($M/M/c$) para el subsistema de despacho, verificando la Ley de Little y argumentando rigurosamente por qué las restricciones de la realidad justifican la construcción del simulador computacional.

---

### 2. Estructura y Contenidos Detallados por Sección

#### 2.1 Modelo Conceptual DES (Sección 3.6 & Criterio R4)
* **Paso 1: Entidades y sus Atributos:**
  * *Entidad Principal: Pedido (`Order`)*
    * `id`: Identificador único (UUID).
    * `restaurante_id`: Identificador del restaurante seleccionado ($r \in \{1, \dots, 10\}$) con coordenadas $(x_r, y_r)$ fijas.
    * `cliente_coords`: Ubicación espacial de entrega $(x_c, y_c) \in [-3.0, 3.0]\text{ km}$.
    * `distancia_vial_km`: Distancia calculada con métrica Manhattan corregida por factor de sinuosidad vial: $d = 1.25 \times (|x_c - x_r| + |y_c - y_r|)$ (Ballou et al., 2002; Levinson & El-Geneidy, 2009).
    * `t_llegada`: Marca de tiempo de emisión del pedido ($t_{arr}$).
    * `t_cocina`: Tiempo de preparación en fogón ($\text{LogNormal}(\mu_{ln}=2.85, \sigma_{ln}=0.35)$, media $\approx 18.5\text{ min}$).
    * `t_ready_est`: Estimación inicial de finalización de cocina ($\text{ETA}_{\text{listo}}$).
    * `t_despacho`: Instante programado para emitir oferta ($t_{\text{despacho}} = t_{\text{ready\_est}} - t_{\text{viaje}} + \Delta t_{\text{buffer}}$).
    * `t_listo`: Marca de tiempo en que la comida salió al mostrador.
    * `t_mostrador`: Tiempo acumulado enfriándose en mostrador sin repartidor.
    * `es_urgente`: Booleano que indica si el pedido está en modo urgente tras salir al mostrador (bono fijo +20%).
    * `paciencia_max`: Tiempo máximo antes de abandono/cancelación voluntaria del cliente ($\text{Weibull}$, acelerada $+50\%$ si $t_{\text{mostrador}} > 6\text{ min}$).
    * `reintentos`: Contador de ciclos de 45 segundos sin conductor que acepte.
    * `estado`: `CREADO`, `EN_COLA_COCINA`, `EN_PREPARACION`, `LISTO_EN_MOSTRADOR`, `OFERTADO`, `ASIGNADO`, `EN_TRANSITO_CLIENTE`, `ENTREGADO`, `CANCELADO_POR_CLIENTE`, `CANCELADO_SIN_REPARTIDOR`, `CANCELADO_INCIDENCIA_TRANSITO`.
  * *Entidad/Recurso Activo: Repartidor (`Courier`)*
    * `id`: Identificador único.
    * `posicion`: Coordenadas dinámicas $(x_{rep}(t), y_{rep}(t))$.
    * `bateria_pct`: Porcentaje de carga actual ($100\%$ inicial, drenaje de $0.15\%/\text{min}$ en viaje GPS y $0.05\%/\text{min}$ en mostrador).
    * `t_login`: Timestamp de conexión al sistema.
    * `tiempo_activo`: Tiempo acumulado en turno (máximo físico duro de 6 horas = 360 min).
    * `pedido_actual`: Referencia a la orden asignada (o `None`).
    * `estado`: `DESCONECTADO`, `CONECTADO_LIBRE`, `OFERTA_RECIBIDA`, `VIAJANDO_A_COCINA`, `EN_MOSTRADOR`, `VIAJANDO_AL_CLIENTE`, `EVALUAR_TURNO`.
* **Paso 2: Recursos del Sistema, Capacidades y Disciplinas:**
  * *Recurso 1: Flota de Repartidores (`CourierPool`)*
    * Capacidad: Oferta estocástica $c(t)$ repartidores conectados simultáneamente ($c(t) \in [8, 100]$ couriers gobernados por NHPP de logins $\lambda_{\text{login}}(t)$).
    * Disciplina: Oferta simultánea (*broadcast*) a couriers dentro del radio elegible con filtro preventivo de batería ($\text{Bat}_{\text{actual}} - \Delta \text{Bat}_{\text{est}} \ge 15\%$). Prioridad estricta para órdenes en mostrador urgente (+20% bono).
  * *Recurso 2: Red de Cocinas de Restaurantes (`KitchenNetwork`)*
    * Capacidad: 10 restaurantes independientes con $k_r \in [3, 6]$ fogones simultáneos (`simpy.Resource(capacity=k_r)`), sumando **47 fogones en toda la red**. Capacidad nominal: $\lambda_{\text{cocina\_max}} = 2.54\text{ ped/min}$.
    * Disciplina: FIFO por restaurante.
  * *Recurso 3: Servidor API REST y Base de Datos (`APIWorkers` & `PostgresPool`)*
    * Capacidad: Workers HTTP concurrentes de Uvicorn y pool de conexiones `QueuePool` en Docker Compose (`api` + `db: postgres:15-alpine`), atendiendo el catálogo de 13 endpoints transaccionales y telemetría atómica continua.
* **Paso 3: Variables de Estado del Sistema:**
  * $N_{ped}(t)$: Número total de pedidos activos en la plataforma en el instante $t$.
  * $Q_{cocina}(t)$: Número de pedidos esperando o en preparación en los 10 restaurantes.
  * $Q_{asig}(t)$: Número de pedidos en cola de asignación y despacho.
  * $Q_{mostrador}(t)$: Número de pedidos cocinados esperando repartidor en mostrador.
  * $c(t)$: Repartidores totales conectados en el instante $t$.
  * $R_{disp}(t)$: Repartidores disponibles y libres en el instante $t$.
  * $R_{ocup}(t)$: Repartidores en servicio (viajando o en mostrador).
  * $N_{canc\_cli}(t)$: Pedidos cancelados por impaciencia del cliente.
  * $N_{canc\_sin\_rep}(t)$: Pedidos cancelados por superar 20 min en mostrador sin repartidor.
  * $N_{canc\_inc}(t)$: Pedidos cancelados por falla / siniestro en ruta con comida en mano.
* **Paso 4: Eventos Atómicos que Modifican el Estado:**
  1. `LlegadaPedido`: Se incrementa $N_{ped}$, entra a cocina ($Q_{cocina}++$). Bajo política sincronizada, programa `DisparoDespacho` para $t_{\text{despacho}}$.
  2. `LoginRepartidor`: Courier autónomo inicia turno ($c(t)++, R_{disp}++$), inicializa batería y temporizador de 6 horas.
  3. `InicioCocina`: Se ocupa un fogón en el restaurante $r$; se simula $T_{\text{cocina}} \sim \text{LogNormal}$.
  4. `FinCocina`: Se libera fogón ($Q_{cocina}--$). Comida pasa a mostrador ($Q_{mostrador}++$). Si no hay repartidor asignado, conmuta de inmediato a modo urgente con bono +20%.
  5. `DisparoDespacho` / `EmisionOferta`: Se evalúa flota libre calificada ($\text{Bat} - \Delta \text{Bat} \ge 15\%$) y se emite broadcast simultáneo con timeout de 45 segundos.
  6. `AceptacionRepartidor`: Primer repartidor en aceptar toma la orden. $R_{disp}--, R_{ocup}++, Q_{asig}--$. Inicia viaje al local.
  7. `ExpiracionOferta` (Timeout 45s sin aceptación): Reintento automático. Fase 1: amplía ventana a $[-6, +8]\text{ min}$ y radio. Fase 2 (si la comida ya salió): mantiene bono urgente +20% y emite ciclo cada 45s.
  8. `LlegadaARestaurante`: Courier arriba al local. Si la comida no está lista, espera en mostrador (tiempo ocioso $T_{\text{espera\_rest}}$); si ya está lista, recoge de inmediato.
  9. `RecogidaPedido`: Courier toma la bolsa térmica ($Q_{mostrador}--$) e inicia tránsito hacia el domicilio del cliente emitiendo telemetría de rastreo.
  10. `EntregaFinal`: Pedido entregado exitosamente ($N_{ped}--$). Se libera repartidor ($R_{ocup}--$). Se evalúa turno: si $T_{\text{turno}} < 6\text{ h}$ y batería $\ge 15\%$, pasa a $R_{disp}++$; si cumplió $\ge 6\text{ h}$ o batería $< 15\%$, ejecuta `LogoutRepartidor` automático (flexibilidad operativa cumplida).
  11. `CancelacionPorCliente`: Temporizador de impaciencia expira ($N_{canc\_cli}++, N_{ped}--$). Si estaba cocinándose o en mostrador, se genera merma.
  12. `CancelacionSinRepartidor`: La orden cumple $20\text{ min}$ en mostrador sin conductor ($N_{canc\_sin\_rep}++, Q_{mostrador}--, N_{ped}--$). Merma compensada al local y reembolso al cliente.
  13. `IncidenciaTransito`: Falla mecánica, accidente o pérdida de señal $> 5\text{ min}$ en viaje al cliente ($N_{canc\_inc}++, R_{ocup}--, N_{ped}--$). Reembolso total y merma en ruta.

#### 2.2 Análisis Analítico con Teoría de Colas (Sección 3.7 & Criterio R5)
* **Subsistema Seleccionado:**
  * Subsistema de **Despacho y Asignación de Repartidores**, aproximado como un sistema **$M/M/c$**.
  * Justificación del modelo: Los pedidos llegan con tasa media $\lambda$ (pedidos por hora o minuto) y son atendidos por $c$ repartidores en paralelo, donde el tiempo de servicio total (traslado a restaurante + recolección + traslado a cliente) tiene tasa media $\mu$.
* **Fórmulas Matemáticas Obligatorias:**
  1. *Factor de utilización del sistema:*
     $$\rho = \frac{\lambda}{c \cdot \mu} \quad (\text{condición de estabilidad: } \rho < 1)$$
  2. *Probabilidad de que el sistema esté vacío ($P_0$):*
     $$P_0 = \left[ \sum_{n=0}^{c-1} \frac{(c\rho)^n}{n!} + \frac{(c\rho)^c}{c!(1-\rho)} \right]^{-1}$$
  3. *Probabilidad de espera en cola (Fórmula C de Erlang, $P_w$):*
     $$P_w = \frac{(c\rho)^c}{c!(1-\rho)} P_0$$
  4. *Número promedio de pedidos en cola ($L_q$):*
     $$L_q = \frac{P_w \cdot \rho}{1 - \rho} = \frac{(c\rho)^c \rho}{c!(1-\rho)^2} P_0$$
  5. *Tiempo promedio de espera en cola ($W_q$):*
     $$W_q = \frac{L_q}{\lambda}$$
  6. *Tiempo promedio de permanencia total ($W$):*
     $$W = W_q + \frac{1}{\mu}$$
  7. *Número promedio de pedidos en el sistema ($L$):*
     $$L = \lambda \cdot W = L_q + \frac{\lambda}{\mu} = L_q + c\rho$$
* **Verificación de la Ley de Little:**
  * Demostración numérica explícita de:
    $$L = \lambda W \quad \text{y} \quad L_q = \lambda W_q$$
* **Identificación del Cuello de Botella y Capacidad Máxima:**
  * Cuello de botella: Cantidad de repartidores activos $c$.
  * Capacidad máxima sostenible: $\lambda_{max} = c \cdot \mu$. Si la tasa de llegada $\lambda$ supera $\lambda_{max}$, el sistema entra en régimen transitorio no estacionario con cola infinita ($\rho \ge 1$).
* **Discusión Crítica: ¿Por qué simular? Límites del Modelo Analítico $M/M/c$:**
  * Las llegadas reales en horas pico son no homogéneas ($\lambda(t)$ variable en el tiempo), violando la estacionariedad de Poisson.
  * Los tiempos de entrega dependen de distancias espaciales y rutas urbanas (no siguen una distribución Exponencial pura con propiedad de pérdida de memoria).
  * En la realidad existen clientes impacientes que cancelan pedidos ($M/M/c/K$ con abandonos y reintentos) y repartidores que rechazan viajes (reprocesos), dinámicas no capturables en un $M/M/c$ estándar sin recurrir a simulación computacional.

---

### 3. Criterios de Aceptación y Verificación
- [ ] Todas las entidades poseen identificador, tipo y marcas de tiempo asociadas.
- [ ] El diagrama de flujo modela bifurcaciones (aceptar/rechazar), abandonos (cancelación) y reprocesos.
- [ ] La tabla evento–estado detalla exactamente qué variable se incrementa o decrementa.
- [ ] El modelo analítico incluye el cálculo formal paso a paso de $P_0, P_w, L_q, W_q, W, L$.
- [ ] La Ley de Little se comprueba con valores numéricos coherentes.
- [ ] Se incluye la discusión formal de al menos 3 supuestos analíticos que fallan en la realidad.
