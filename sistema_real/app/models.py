from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sistema_real.app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class RestaurantModel(Base):
    __tablename__ = "restaurants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    coord_x = Column(Float, nullable=False)  # Coordenada X en km [0.0, 6.0]
    coord_y = Column(Float, nullable=False)  # Coordenada Y en km [0.0, 6.0]
    kitchen_capacity = Column(Integer, nullable=False)  # Fogones kr in [3, 6], total red: 47
    created_at = Column(DateTime(timezone=True), default=utcnow)

    orders = relationship("OrderModel", back_populates="restaurant")


class CourierModel(Base):
    __tablename__ = "couriers"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    name = Column(String(100), nullable=False)
    current_coord_x = Column(Float, nullable=False, default=3.0)
    current_coord_y = Column(Float, nullable=False, default=3.0)
    battery_level = Column(Float, nullable=False, default=95.0)  # % de carga [0.0, 100.0]
    shift_start_time = Column(DateTime(timezone=True), default=utcnow)
    shift_duration_limit_min = Column(Float, default=360.0)  # Cota dura de 6 horas
    is_available = Column(Boolean, default=True)  # True si está libre para ofertas
    is_active = Column(Boolean, default=True)  # False tras logout obligatorio o voluntario

    orders = relationship("OrderModel", back_populates="courier")
    tracking_records = relationship("TrackingRecordModel", back_populates="courier")


class OrderModel(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    customer_id = Column(String(50), nullable=False, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False, index=True)
    
    # 11 Estados del Modelo DES:
    # CREADO, EN_COLA_COCINA, EN_PREPARACION, LISTO_EN_MOSTRADOR, OFERTADO,
    # ASIGNADO, EN_TRANSITO_CLIENTE, ENTREGADO, CANCELADO_POR_CLIENTE,
    # CANCELADO_SIN_REPARTIDOR, CANCELADO_INCIDENCIA_TRANSITO
    status = Column(String(40), nullable=False, default="CREADO", index=True)

    delivery_coord_x = Column(Float, nullable=False)
    delivery_coord_y = Column(Float, nullable=False)
    eta_listo = Column(Float, nullable=False, default=18.5)  # En minutos de jornada

    t_creado = Column(DateTime(timezone=True), default=utcnow)
    t_inicio_cocina = Column(DateTime(timezone=True), nullable=True)
    t_listo = Column(DateTime(timezone=True), nullable=True)  # Fin de cocción / pase a mostrador
    t_recogida = Column(DateTime(timezone=True), nullable=True)  # Retiro por repartidor
    t_entregado = Column(DateTime(timezone=True), nullable=True)  # Entrega final al cliente

    courier_id = Column(Integer, ForeignKey("couriers.id"), nullable=True, index=True)
    is_urgent = Column(Boolean, default=False)  # True con bono +20% tras pase a mostrador
    cancellation_reason = Column(String(100), nullable=True)

    restaurant = relationship("RestaurantModel", back_populates="orders")
    courier = relationship("CourierModel", back_populates="orders")
    tracking_records = relationship("TrackingRecordModel", back_populates="order")


class TrackingRecordModel(Base):
    __tablename__ = "tracking_records"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True, index=True)
    courier_id = Column(Integer, ForeignKey("couriers.id"), nullable=False, index=True)
    coord_x = Column(Float, nullable=False)
    coord_y = Column(Float, nullable=False)
    battery_level = Column(Float, nullable=False)
    recorded_at = Column(DateTime(timezone=True), default=utcnow)

    order = relationship("OrderModel", back_populates="tracking_records")
    courier = relationship("CourierModel", back_populates="tracking_records")


def seed_database(db):
    """Pobla los 10 restaurantes con 47 fogones totales y couriers iniciales si la BD está vacía."""
    if db.query(RestaurantModel).count() == 0:
        restaurants_data = [
            {"id": 1, "name": "Burger Station Chapinero", "coord_x": 1.5, "coord_y": 2.0, "kitchen_capacity": 5},
            {"id": 2, "name": "Pizzeria Napolitana Zona T", "coord_x": 2.8, "coord_y": 1.2, "kitchen_capacity": 4},
            {"id": 3, "name": "Wok Express Salitre", "coord_x": 2.0, "coord_y": 2.0, "kitchen_capacity": 4},
            {"id": 4, "name": "Tacos El Guero Galerias", "coord_x": 4.5, "coord_y": 3.2, "kitchen_capacity": 6},
            {"id": 5, "name": "Sushi Master Usaquen", "coord_x": 3.2, "coord_y": 4.8, "kitchen_capacity": 5},
            {"id": 6, "name": "Pollo Criollo Centro", "coord_x": 1.0, "coord_y": 4.0, "kitchen_capacity": 6},
            {"id": 7, "name": "Arepas & Empanadas Teusaquillo", "coord_x": 4.0, "coord_y": 1.5, "kitchen_capacity": 4},
            {"id": 8, "name": "Green Salad & Bowls Chicó", "coord_x": 5.2, "coord_y": 5.0, "kitchen_capacity": 3},
            {"id": 9, "name": "Pastas & Risottos Parkway", "coord_x": 2.5, "coord_y": 3.5, "kitchen_capacity": 5},
            {"id": 10, "name": "Parrilla Urbana Cedritos", "coord_x": 3.8, "coord_y": 2.7, "kitchen_capacity": 5},
        ]
        for r_data in restaurants_data:
            db.add(RestaurantModel(**r_data))
        db.commit()

    if db.query(CourierModel).count() == 0:
        couriers_data = [
            {"name": f"Courier-{i:02d}", "current_coord_x": 1.0 + (i * 0.4) % 5.0, "current_coord_y": 1.0 + (i * 0.5) % 5.0, "battery_level": 92.0 + (i % 8)}
            for i in range(1, 16)
        ]
        for c_data in couriers_data:
            db.add(CourierModel(**c_data))
        db.commit()
