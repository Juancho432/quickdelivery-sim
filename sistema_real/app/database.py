import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Obtención de la URL de conexión desde variables de entorno
# En Docker Compose apunta al servicio 'db' (PostgreSQL 15 Alpine)
# Permite fallback transparente a SQLite para pruebas locales o CI
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://delivery_user:delivery_pass@db:5432/delivery_db"
)

# Argumentos de conexión específicos según el motor de base de datos
engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_size": 20,
        "max_overflow": 10
    })

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Generador de sesiones de base de datos para inyección de dependencias en FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
