import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

import socket

# Obtención de la URL de conexión desde variables de entorno
# En Docker Compose apunta al servicio 'db' (PostgreSQL 15 Alpine)
# Fuera de Docker ('db' no resoluble en host) conmuta automáticamente a 'localhost'
DEFAULT_POSTGRES = "postgresql+psycopg2://delivery_user:delivery_pass@db:5432/delivery_db"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_POSTGRES)

# Asegurar que se use el dialecto psycopg2 si la URL viene genérica
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

if "@db:5432" in DATABASE_URL:
    try:
        socket.gethostbyname("db")
    except (socket.gaierror, socket.herror, OSError):
        DATABASE_URL = DATABASE_URL.replace("@db:5432", "@localhost:5432")



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
