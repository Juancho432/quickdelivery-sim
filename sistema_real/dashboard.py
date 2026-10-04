"""
QuickDelivery Sim — Centro de Operaciones en Tiempo Real (Archivo Base).
Inicializa la aplicación NiceGUI, registra dinámicamente las páginas modulares
desde 'dashboard_pages/' y ejecuta el servidor web.
"""
import os
import sys
from pathlib import Path

# Asegurar importación de módulos del proyecto
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from nicegui import ui
from sistema_real.dashboard_pages import register_all_pages

# Registro dinámico y modular de todas las páginas (map_page, metrics_page, etc.)
register_all_pages()


def start_dashboard(port: int = 8080, reload: bool = False):
    """Punto de entrada maestro para ejecutar el Dashboard de Operaciones."""
    port_env = int(os.getenv("DASHBOARD_PORT", str(port)))
    ui.run(
        title="QuickDelivery Sim — Dashboard",
        port=port_env,
        reload=reload,
        show=False,
        favicon="🛵"
    )


if __name__ in ("__main__", "__mp_main__"):
    start_dashboard()
