"""
Paquete dashboard_pages: Registro modular de páginas para el Dashboard de NiceGUI.
Permite extender el sistema agregando nuevos módulos .py dentro de esta carpeta.
"""
import importlib
import pkgutil
from pathlib import Path

# Importación de páginas principales
from . import map_page
from . import metrics_page


def register_all_pages():
    """
    Descubre e importa automáticamente todas las páginas ubicadas en dashboard_pages/.
    Cualquier archivo nuevo que defina @ui.page se registrará automáticamente en NiceGUI.
    """
    package_dir = Path(__file__).resolve().parent
    for module_info in pkgutil.iter_modules([str(package_dir)]):
        if module_info.name not in ("common", "__init__"):
            importlib.import_module(f"sistema_real.dashboard_pages.{module_info.name}")


__all__ = ["register_all_pages", "map_page", "metrics_page"]
