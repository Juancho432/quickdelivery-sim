import os
import sys
import warnings
from pathlib import Path

# Agregar raíz del proyecto al sys.path para permitir ejecución independiente
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Suprimir advertencias de deprecación menores de librerías externas (ej. httpx/starlette)
warnings.filterwarnings("ignore", category=DeprecationWarning)

import unittest
from fastapi.testclient import TestClient

# Configuración del motor de persistencia con tolerancia y fallback automático
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "postgresql://delivery_user:delivery_pass@localhost:5432/delivery_db"

from sistema_real.app.main import app
from sistema_real.app.database import SessionLocal, engine, Base
from sistema_real.app.models import (
    RestaurantModel, CourierModel, OrderModel, TrackingRecordModel,
    seed_database, utcnow
)
from sistema_real.app.config import system_config


class TestQuickDeliveryAPIBase(unittest.TestCase):
    """
    Clase base modular para pruebas unitarias e integrales de la API QuickDelivery Sim.
    Provee TestClient oficial de FastAPI, gestión del ciclo de vida de BD y aislamiento de estados.
    """

    client: TestClient

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        
        # Verificar disponibilidad de base de datos e insertar semilla si es necesario
        db = SessionLocal()
        try:
            Base.metadata.create_all(bind=engine)
            seed_database(db)
            # Limpiar datos transaccionales para arrancar con estado predecible
            db.query(TrackingRecordModel).delete()
            db.query(OrderModel).delete()
            db.commit()
        except Exception as e:
            db.rollback()
            # En caso de fallo transitorio, asegurar que no queden transacciones colgadas
            pass
        finally:
            db.close()

    def setUp(self):
        """Restablece los parámetros de configuración y limpia órdenes antes de cada test para aislamiento total."""
        system_config.active_dispatch_policy = "synchronized"
        system_config.buffer_delta_t_min = 2.0
        system_config.max_shift_duration_min = 360.0
        system_config.anti_limbo_max_counter_min = 20.0
        system_config.urgency_bonus_multiplier = 1.20
        system_config.min_battery_threshold_pct = 15.0

        db = self.get_db()
        try:
            db.query(TrackingRecordModel).delete()
            db.query(OrderModel).delete()
            db.commit()
        finally:
            db.close()

    def get_db(self):
        """Retorna una sesión limpia de SQLAlchemy para aserciones directas sobre la base de datos."""
        return SessionLocal()

    def create_courier(self, name: str = "Test-Courier", x: float = 2.0, y: float = 2.0, battery: float = 95.0, is_active: bool = True, is_available: bool = True) -> CourierModel:
        """Helper para crear y persistir un repartidor determinista en pruebas."""
        db = self.get_db()
        courier = CourierModel(
            name=name,
            current_coord_x=x,
            current_coord_y=y,
            battery_level=battery,
            shift_start_time=utcnow(),
            is_active=is_active,
            is_available=is_available
        )
        db.add(courier)
        db.commit()
        db.refresh(courier)
        courier_id = courier.id
        db.close()
        # Retornar una nueva consulta para garantizar acceso a atributos sin DetachedInstanceError
        db2 = self.get_db()
        c = db2.query(CourierModel).filter(CourierModel.id == courier_id).first()
        db2.close()
        c.id = courier_id
        return c
