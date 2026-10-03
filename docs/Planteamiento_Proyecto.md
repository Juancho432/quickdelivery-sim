### 3.6 Especificación de Entidades y Lógica de Eventos Discretos

El gemelo digital se fundamenta en un modelo de eventos discretos (DES) que orquesta la interacción entre clientes, restaurantes y flota.

#### 1. Entidad `Order` (Pedido)
La orden transita por una máquina de estados estricta de 11 fases[cite: 3]:
1. **CREADO:** El cliente confirma el pedido a través de la API[cite: 3].
2. **EN_COLA_COCINA:** Los fogones del local están ocupados; espera FIFO[cite: 3].
3. **EN_PREPARACION:** Ocupa un puesto de cocción[cite: 3].
4. **LISTO_EN_MOSTRADOR:** Cocción terminada, comida empacada[cite: 3].
5. **OFERTADO:** Se emite broadcast a la flota[cite: 3].
6. **ASIGNADO:** Un repartidor acepta el viaje[cite: 3].
7. **EN_TRANSITO_CLIENTE:** En camino al domicilio[cite: 3].
8. **ENTREGADO:** Comida recibida exitosamente[cite: 3].
9. **CANCELADO_POR_CLIENTE:** Abandono por impaciencia (Curva Weibull)[cite: 3].
10. **CANCELADO_SIN_REPARTIDOR:** 20 minutos en mostrador sin conductor (Límite FDA)[cite: 3].
11. **CANCELADO_INCIDENCIA_TRANSITO:** Pérdida de telemetría o siniestro en ruta[cite: 3].

#### 2. Entidad `Courier` (Repartidor)
Flota *crowdsourcing* gobernada por dos restricciones físicas duras (C6)[cite: 3]:
* **Límite Físico de Fatiga:** Turno continuo máximo de 6 horas para prevenir riesgos viales[cite: 3].
* **Autonomía Energética:** Drenaje de batería al 0.15%/min por GPS[cite: 3]. Incorpora un filtro preventivo: se exige una proyección de batería $\ge 15\%$ al finalizar el viaje para ser calificado[cite: 3].

#### 3. Entidad `KitchenNetwork` (Red de Restaurantes)
Compuesta por 10 locales distribuidos uniformemente[cite: 3]. Capacidad instalada heterogénea entre 3 y 6 fogones simultáneos por local, totalizando una red de 47 fogones para toda la simulación metropolitana[cite: 3].

#### 4. Ciclo de Vida del Pedido y Protocolo Anti-Limbo
```mermaid
flowchart TD
    A[Pedido CREADO] --> B{¿Fogón libre?}
    B -- No --> C[EN_COLA_COCINA]
    C --> D
    B -- Sí --> D[EN_PREPARACION]
    
    D --> E[Cálculo t_despacho = ETA_listo - t_viaje + t_buffer]
    E --> F[OFERTADO: Ventana de 45s]
    
    F --> G{¿Aceptado en 45s?}
    G -- Sí --> H[ASIGNADO]
    G -- No --> I[Fase 1: Ampliar ventana -6 a +8 min]
    I --> J{¿Aceptado?}
    J -- Sí --> H
    J -- No --> K[Fase 2: LISTO_EN_MOSTRADOR con Bono +20%]
    
    K --> L{¿Tiempo > 20 min?}
    L -- Sí --> M[CANCELADO_SIN_REPARTIDOR]
    L -- No --> N{¿Cliente Cancela - Weibull?}
    N -- Sí --> O[CANCELADO_POR_CLIENTE]
    
    H --> P[Recogida: EN_TRANSITO_CLIENTE]
    P --> Q[ENTREGADO]

    ###5. Tabla de relación de eventos atómicos

    Evento AtómicoEstado ModificadoEfecto en Variables del SistemaLlegadaPedidoOrder -> CREADO   Aumenta $L$ (inventario total), se evalúa la tasa de llegada $\lambda(t)$ del NHPP.   InicioCocinaOrder -> EN_PREPARACION   Fogón ocupado (Resource.request), inicia el tiempo de cocción Log-Normal.   FinCocinaOrder -> LISTO_EN_MOSTRADOR   Fogón liberado (Resource.release), se sella la marca de tiempo $t_{listo}$.   DisparoDespachoOrder -> OFERTADO   Se emite broadcast a la flota; repartidores evaluados por batería (> 15%) y holgura.   AceptacionRepartidorOrder -> ASIGNADO   Courier -> VIAJANDO_AL_LOCAL; inicia cinemática vial truncada con factor $\tau=1.25$.   ExpiracionOfertaSistema AlgorítmicoAmplía ventana ($\Delta t_{buffer}$) en Fase 1, o conmuta a Urgente (+20%) en Fase 2.   LlegadaARestauranteCourier -> EN_MOSTRADOR   Registra $t_{arribo}$, inicia cálculo de $\Delta t_{mostrador}$ (merma térmica si > 6 min).   RecogidaPedidoOrder -> EN_TRANSITO_CLIENTE   Termina espera ociosa en mostrador; drena batería al 0.15%/min en ruta.   EntregaFinalOrder -> ENTREGADO   Courier -> EVALUAR_TURNO (Logout obligatorio si turno acumulado > 6h).   Cancelaciones/IncidenciasOrder -> CANCELADO_...   Cierra ciclo prematuro por Weibull, abandono de 20 min o fallo; actualiza KPI de $P_{canc}$.   