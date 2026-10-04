"""
Módulo común para páginas del Dashboard: estado global compartido y cabecera de navegación.
"""
from typing import Dict, Any
from nicegui import ui
from sistema_real.api_client import DeliveryApiClient, API_BASE_URL

# Cliente HTTP compartido hacia FastAPI
api_client = DeliveryApiClient(API_BASE_URL)

# Estado global compartido en memoria
state: Dict[str, Any] = {
    "restaurants": [],
    "couriers": [],
    "orders": [],
    "stats": {
        "total_orders": 0,
        "orders_in_progress": 0,
        "orders_completed": 0,
        "orders_cancelled": 0,
        "connected_couriers": 0,
    },
    "telemetry": {
        "cpu_percent": 0.0,
        "memory_mb": 0.0,
        "latency_avg_ms": 0.0,
        "uptime_seconds": 0.0,
        "status": "connected"
    },
    "selected_order_id": None,
    "preview_point": (3.0, 3.0),
    "auto_pilot_order_id": None,
    "map_layers": {
        "restaurants": True,
        "customers": True,
        "couriers_free": True,
        "couriers_busy": True,
        "preview": True,
    },
}


def common_header(active_route: str = "/"):
    """Barra superior de navegación y estado de conexión en vivo."""
    with ui.header().classes("bg-slate-950 border-b border-slate-800 px-6 py-2.5 flex justify-between items-center text-white z-50"):
        with ui.row().classes("items-center gap-3"):
            ui.icon("local_shipping", size="sm").classes("text-amber-400")
            with ui.column().classes("gap-0"):
                ui.label("QuickDelivery Sim").classes("text-base font-bold tracking-tight text-white")
                ui.label("Centro de Control & Gemelo Digital").classes("text-[11px] text-slate-400")
            ui.badge("Entrega 1", color="indigo").classes("ml-2 text-[10px] font-semibold")

        with ui.row().classes("items-center gap-2"):
            ui.button("📍 Mapa & Operaciones", on_click=lambda: ui.navigate.to("/")).props(
                "unelevated" if active_route == "/" else "flat"
            ).classes("text-xs font-medium px-3 py-1.5 " + ("bg-indigo-600 text-white" if active_route == "/" else "text-slate-300"))
            
            ui.button("📊 Métricas & Configuración", on_click=lambda: ui.navigate.to("/metricas")).props(
                "unelevated" if active_route == "/metricas" else "flat"
            ).classes("text-xs font-medium px-3 py-1.5 " + ("bg-indigo-600 text-white" if active_route == "/metricas" else "text-slate-300"))

            # Indicador de estado de API
            is_connected = state["telemetry"]["status"] in ("healthy", "connected")
            status_color = "emerald" if is_connected else "rose"
            status_text = "API Online" if is_connected else "API Offline"
            with ui.row().classes("items-center gap-1.5 ml-3 px-2 py-0.5 rounded-full bg-slate-900 border border-slate-800"):
                ui.element("div").classes(f"w-2 h-2 rounded-full bg-{status_color}-500 animate-pulse")
                ui.label(status_text).classes(f"text-[10px] font-semibold text-{status_color}-400")
