# COMPENDIO DE FUENTES Y PARÁMETROS DEL ESCENARIO
## Proyecto de Aula: Gemelo Digital y Simulación Estocástica (*QuickDelivery Sim*)

> **Propósito del Documento:**  
> Este documento compila las referencias académicas verificables que sustentan la formulación metodológica del proyecto y distingue explícitamente entre los conceptos respaldados por literatura indexada y los valores numéricos adoptados como **hipótesis de escenario** o **políticas operativas del sistema bajo estudio**.

---

## 1. Tabla Maestra de Parámetros, Hipótesis de Escenario y Respaldo Metodológico

| Parámetro / Métrica | Valor / Distribución Adoptada | Naturaleza del Valor | Justificación Metodológica y Fuente Comprobable |
| :--- | :--- | :--- | :--- |
| **Tiempo de Preparación en Cocina** ($T_{\text{cocina}}$) | $\text{LogNormal}(\mu_{\ln}=2.85, \sigma_{\ln}=0.35)$<br>$\text{Media} \approx 18.4\text{ min}$, $\sigma \approx 6.6\text{ min}$ | Hipótesis de escenario (a calibrar en Entrega 2 con dataset externo) | Los tiempos de servicio estrictamente positivos con asimetría derecha se modelan mediante distribuciones Log-Normales (Law, 2015). El problema de tiempos de preparación estocásticos en entrega de comida se formula en Ulmer et al. (2020). |
| **Capacidad Física de Cocinas** ($k_r$ — Criterio C6) | Heterogéneo: $k_r \in [3, 6]$ fogones.<br>Total red: $47$ fogones fijos en $10$ restaurantes. | Límite físico medible del sistema (C6) | Capacidad instalada configurada en el esquema relacional (`RestaurantModel.kitchen_capacity`) y en `simpy.Resource(capacity=k_r)`. |
| **Pool de Conexiones a Base de Datos** (Criterio C6 TI) | `pool_size = 20`, `max_overflow = 10` (máximo $30$ conexiones concurrentes en SQLAlchemy / PostgreSQL 15). | Límite duro medible de infraestructura TI (C6) | Cota física de concurrencia del contenedor `api` hacia `db` definida en `sistema_real/app/database.py`. |
| **Capacidad Máxima de Red Culinaria** ($\lambda_{\text{cocina\_max}}$) | $2.54\text{ pedidos/min}$ ($152.4\text{ ped/h}$)<br>$\lambda_{\max} = \sum k_r / \bar{T}_{\text{coc}}$ | Cota analítica derivada | Deducción de capacidad máxima estacionaria en sistemas multi-servidor (Kleinrock, 1975). |
| **Curva Diaria de Demanda** ($\lambda(t)$ - NHPP) | $\approx 1.893\text{ pedidos/día}$ en 7 franjas.<br>Pico Almuerzo: $2.70\text{ ped/min}$ ($\rho_{\text{coc}}=106\%$).<br>Pico Cena: $3.30\text{ ped/min}$ ($\rho_{\text{coc}}=130\%$). | Hipótesis de escenario no estacionario (C5) | Modelado de arribos dependientes del tiempo mediante Procesos de Poisson No Homogéneos (NHPP) por tramos horarios (Law, 2015). |
| **Cifras de Línea Base del Problema** | Espera ociosa: $16.2\text{ min}$<br>Cancelación: $16.5\%$<br>Desconexión en pico: $35\%$<br>$W_{\text{total\_p95}} > 55\text{ min}$ | Hipótesis de escenario base | Valores de referencia definidos para caracterizar el régimen de operación inicial bajo la política de asignación voraz inmediata antes de la optimización. |
| **Factor de Sinuosidad Vial** ($\tau$) | $\tau = 1.25$ sobre distancia Manhattan ($d_{\text{vial}} = 1.25 \times d_{\text{Manhattan}}$) | Parámetro respaldado en literatura vial | Estudios empíricos sobre redes viales urbanas demuestran factores de circuidad/sinuosidad entre $1.20$ y $1.30$ respecto a métricas ortogonales o euclidianas (Ballou et al., 2002; Levinson & El-Geneidy, 2009; Boeing, 2019). |
| **Velocidad Urbana del Repartidor** ($V_{\text{rep}}$) | $\mathcal{N}(18\text{ km/h}, 3\text{ km/h})$ truncada en $[8, 25]\text{ km/h}$ | Hipótesis de escenario (a calibrar en Entrega 2 con dataset externo) | Distribución normal truncada para acotar velocidades físicas positivas en desplazamientos urbanos (Law, 2015; Ulmer et al., 2020). |
| **Política de Duración de Turno** ($T_{\text{max\_turno}}$) | $6.0\text{ horas continuas}$ ($360\text{ min}$) | Política operativa de la plataforma | Regla de negocio de desconexión preventiva configurada en la plataforma (`max_shift_duration_min = 360.0` en `config.py`). |
| **Tasa de Drenaje y Reserva de Batería** | $0.15\%/\text{min}$ en marcha / $0.05\%/\text{min}$ en espera.<br>Reserva mínima operativa: $15\%$. | Hipótesis de parametrización / Regla operativa | Basada cualitativamente en la medición de consumo energético por subsistema (GPS, pantalla y radio celular) en smartphones (Carroll & Heiser, 2010). |
| **Paciencia y Abandono del Cliente** ($T_{\text{canc}}$) | $\text{Weibull}(k=2.4, \lambda_w=40\text{ min})$ | Hipótesis de escenario | El abandono de clientes impacientes en plataformas bajo demanda se fundamenta en Bai et al. (2019); el uso de la distribución Weibull con $k > 1$ para modelar tasas de riesgo crecientes se sustenta en Law (2015). |
| **Umbrales de Mostrador (SLA Térmico y Anti-Limbo)** | Enfriamiento: $6.0\text{ min}$<br>Cancelación sin repartidor: $20.0\text{ min}$ | Reglas de negocio / SLA interno de la plataforma | Parámetros de control de calidad de servicio e impaciencia configurados en la lógica transaccional del sistema (`anti_limbo_max_counter_min = 20.0`). |
| **Ventana de Oferta y Bono de Urgencia** | Timeout de oferta: $45\text{ s}$<br>Bono de urgencia: $+20\%$ | Reglas operativas de la plataforma | El uso de incentivos tarifarios dinámicos para coordinar oferta y demanda en plataformas con proveedores autónomos se sustenta en Cachon et al. (2017) y Bai et al. (2019). |

---

## 2. Referencias Bibliográficas Verificadas (Formato APA 7.ª Edición)

Bai, J., So, K. C., Tang, C. S., Chen, X., & Wang, H. (2019). Coordinating supply and demand on an on-demand service platform with impatient customers. *Manufacturing & Service Operations Management*, *21*(3), 556–570. https://doi.org/10.1287/msom.2018.0707

Ballou, R. H., Rahardja, H., & Sakai, N. (2002). Selected properties of Manhattan and Euclidean distances as approximations for network distances. *Computers & Operations Research*, *29*(8), 983–1001. https://doi.org/10.1016/S0305-0548(00)00101-9

Boeing, G. (2019). Urban spatial order: Street network orientation, configuration, and entropy. *Applied Network Science*, *4*(1), 67. https://doi.org/10.1007/s41109-019-0189-1

Cachon, G. P., Daniels, K. M., & Lobel, R. (2017). The role of surge pricing on a service platform with customer and provider self-scheduling. *Management Science*, *63*(11), 3684–3699. https://doi.org/10.1287/mnsc.2017.2788

Carroll, A., & Heiser, G. (2010). An analysis of power consumption in a smartphone. En *Proceedings of the 2010 USENIX Annual Technical Conference (USENIX ATC '10)* (pp. 21–34). USENIX Association.

Kleinrock, L. (1975). *Queueing systems, Volume 1: Theory*. John Wiley & Sons.

Law, A. M. (2015). *Simulation modeling and analysis* (5.ª ed.). McGraw-Hill Education.

Levinson, D., & El-Geneidy, A. (2009). The circuity of urban travel. *Transportation Research Part A: Policy and Practice*, *43*(8), 701–713. https://doi.org/10.1016/j.tra.2009.07.001

Ulmer, M. W., Goodson, J. C., Mattfeld, D. C., & Hennig, M. (2020). Offline–online approximate dynamic programming for dynamic delivery problems. *European Journal of Operational Research*, *284*(2), 577–595. https://doi.org/10.1016/j.ejor.2019.12.039
