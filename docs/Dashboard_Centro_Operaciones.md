# Centro de Control & Dashboard de Operaciones en Tiempo Real (QuickDelivery Sim)

## 1. Visión General

El **Centro de Control y Gemelo Digital** (`sistema_real/dashboard.py`) es una interfaz web reactiva diseñada para operar, monitorizar y contrastar el ecosistema de entrega de pedidos en tiempo real sobre una cuadrícula urbana de $6.00 \times 6.00\text{ km}$ sin necesidad de herramientas externas como Postman ni recargas de página (*zero page reload*).

Está construido sobre **NiceGUI 2.x** y **FastAPI**, apoyado en WebSockets nativos bidireccionales y renderizado vectorial SVG de alto rendimiento.

---

## 2. Arquitectura del Módulo

El sistema del dashboard se diseñó con una arquitectura modular desacoplada:

```
sistema_real/
├── dashboard.py                  # Entrypoint maestro y servidor NiceGUI (:8080)
├── api_client.py                 # Cliente asíncrono con triple capa de resiliencia
├── map_renderer.py               # Motor de proyección vectorial SVG 2D con capas y transparencias
└── dashboard_pages/              # Paquete modular de páginas
    ├── __init__.py               # Descubrimiento dinámico de rutas
    ├── common.py                 # Estado global en memoria y cabecera de navegación
    ├── map_page.py               # Página 1: Mapa 2D, leyenda interactiva y control de pedidos
    └── metrics_page.py           # Página 2: Métricas operativas, telemetría y configuración
```

### Características de la Arquitectura:
- **Descubrimiento Dinámico de Páginas (`register_all_pages`):** El archivo base escanea automáticamente los módulos en `dashboard_pages/` y los registra como endpoints de NiceGUI (`/` y `/metricas`), permitiendo extender la aplicación añadiendo nuevos archivos sin modificar el entrypoint.
- **Triple Capa de Resiliencia en [`api_client.py`](../sistema_real/api_client.py):**
  1. *Primaria:* Consultas HTTP REST contra FastAPI (`http://localhost:8000`).
  2. *Secundaria:* Conexión directa a PostgreSQL mediante SQLAlchemy `SessionLocal()`.
  3. *Terciaria:* Mock estático con los 10 locales y parámetros de Bogotá si la base de datos y la API están desconectadas.

---

## 3. Funcionalidades Detalladas por Página

### 3.1 Página 1: Mapa & Operaciones (`/`)

* **Plano Cartesiano 2D ($[0.00, 6.00]\text{ km}$):**
  - Sistema de proyección simétrica $680 \times 680\text{ px}$ con mallas submétricas y principales.
  - Proyección precisa de 10 restaurantes (cuadrados verdes con aforo), clientes (círculos ámbar) y repartidores (libres en cyan y en ruta en magenta).
* **Leyenda Interactiva con Filtros Booleanos:**
  - Cada elemento de la leyenda (`Restaurantes (10)`, `Clientes`, `Couriers Libres`, `Couriers en Ruta`, `Punto de Clic`) actúa como un selector interactivo.
  - Permite alternar la visibilidad de cualquier capa de manera independiente (mostrar todos, solo 3 de ellos, solo restaurantes, etc.).
  - Controles de acceso rápido: **"Todos"** y **"Ninguno"** para despejar o poblar el plano en un solo clic.
* **Captura Nativa de Clics para Pedidos:**
  - Al hacer clic en cualquier punto del mapa, se transforma de píxeles a coordenadas cartesianas $(\text{km}_x, \text{km}_y)$ fijando los valores de entrega sin alertas emergentes intrusivas.
* **Regla de Transparencia Enfocada:**
  - Al seleccionar una orden activa, todos los elementos ajenos en el mapa reducen su opacidad al $15\%$ (`opacity="0.15"`).
  - El restaurante emisor, el cliente receptor y el repartidor asignado permanecen al $100\%$ (`opacity="1.0"`) con halos brillantes (`feGaussianBlur`) y trazado de vectores de ruta en tiempo real.
* **Control del Ciclo de Vida & Piloto Automático:**
  - Botones paso a paso: `1. Listo` $\to$ `2. Asignar` $\to$ `3. En Ruta` $\to$ `4. Entregar` / `Cancelar`.
  - **Piloto Automático:** Switch para delegar el avance autónomo segundo a segundo de la comanda con cinemática vial corregida por sinuosidad ($\tau = 1.25$).

---

### 3.2 Página 2: Métricas & Configuración (`/metricas`)

* **Tarjetas KPI en Vivo:**
  - Conteo de repartidores conectados (libres vs en ruta).
  - Pedidos acumulados, en curso, completados y cancelados (anti-limbo o impaciencia).
* **Distribución de Pedidos (Pie Chart):**
  - Gráfico interactivo circular de Apache ECharts (`ui.echart`) con animación y leyenda dinámica.
* **Telemetría de Servidor (Host):**
  - Medición continua de uso de CPU (%) y RAM asignada (MB) con barras de progreso lineales.
* **Switch de Estrategia de Despacho:**
  - Conmutador visual entre **Sincronizado Predictivo** (propuesta con ETA de cocina y buffer) y **Voraz Inmediato** (línea base).
* **Configuración en Caliente (`/api/v1/config/`):**
  - Ajuste en vivo de parámetros: $\Delta t_{\text{buffer}}$ (min), turno máximo (min), timeout anti-limbo (min), multiplicador de bono urgente y umbral crítico de batería.

---

## 4. Resolución de Errores e Incidentes Clave

1. **Error `AttributeError: 'GenericEventArguments' object has no attribute 'value'`:**
   - *Diagnóstico:* Uso de listeners de bajo nivel `.on("update:model-value", ...)` en componentes `ui.select` y `ui.switch`. En NiceGUI, estos reciben argumentos genéricos Quasar donde el valor reside en `.args`.
   - *Corrección:* Migración a eventos nativos `on_change=...` y extracción resiliente con `getattr(e, "value", None) or getattr(e, "args", None) or element.value`.
2. **Desincronización de Restaurantes en Base de Datos vs API:**
   - *Diagnóstico:* Imagen Docker desactualizada sin endpoints `/api/v1/restaurants/` y dialecto incompatible de SQLAlchemy (`postgresql://` exigiendo `psycopg` v3).
   - *Corrección:* Reconstrucción de imagen Docker con volumen montado `./sistema_real:/app/sistema_real`, forzado de dialecto `postgresql+psycopg2://` y endpoints REST de consulta individual.
3. **Filtro de Capas en Renderizado SVG:**
   - *Diagnóstico:* Necesidad de ocultar selectivamente iconos en el plano cartesiano según preferencias del operador.
   - *Corrección:* Parámetro `layers: Optional[Dict[str, bool]]` integrado en `render_cartesian_svg_content`, permitiendo apagar selectivamente colecciones completas sin afectar el rendimiento ni romper las pruebas unitarias.

---

## 5. Guía de Ejecución y Verificación

### Iniciar el Dashboard:
```bash
# Con la API levantada en http://localhost:8000
python -m sistema_real.dashboard
```
Navega a [http://localhost:8080](http://localhost:8080).

### Ejecutar Pruebas Automatizadas:
```bash
# Dentro del contenedor Docker
docker compose exec api pytest tests/test_dashboard.py

# O la suite completa
docker compose exec api pytest tests/
```
Todas las 80 pruebas unitarias y de integración pasan con **100% de éxito**.
