from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


# ---------------------------------------------------------
# Esquemas para Pedidos (Orders)
# ---------------------------------------------------------
class OrderCreateSchema(BaseModel):
    customer_id: str = Field(..., description="Identificador único del cliente (ej. CUST-101)")
    restaurant_id: int = Field(..., ge=1, le=10, description="Identificador del restaurante (1 a 10)")
    delivery_coord_x: float = Field(..., ge=0.0, le=6.0, description="Coordenada X de entrega en km [0.0, 6.0]")
    delivery_coord_y: float = Field(..., ge=0.0, le=6.0, description="Coordenada Y de entrega en km [0.0, 6.0]")


class OrderResponseSchema(BaseModel):
    id: int
    customer_id: str
    restaurant_id: int
    status: str
    delivery_coord_x: float
    delivery_coord_y: float
    eta_listo: float
    t_creado: datetime
    t_listo: Optional[datetime] = None
    t_recogida: Optional[datetime] = None
    t_entregado: Optional[datetime] = None
    courier_id: Optional[int] = None
    is_urgent: bool = False
    cancellation_reason: Optional[str] = None

    class Config:
        from_attributes = True


class OrderCancelSchema(BaseModel):
    reason: str = Field("CUSTOMER_IMPATIENCE", description="Motivo de cancelación (ej. CUSTOMER_IMPATIENCE, TIMEOUT)")


# ---------------------------------------------------------
# Esquemas para KDS de Cocina (Restaurants)
# ---------------------------------------------------------
class KDSOrderResponseSchema(BaseModel):
    order_id: int
    restaurant_id: int
    status: str
    tiempo_espera_cola_min: float
    eta_listo: float
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------
# Esquemas para Repartidores (Couriers)
# ---------------------------------------------------------
class CourierLoginSchema(BaseModel):
    name: str = Field(..., description="Nombre o identificación del repartidor")
    initial_coord_x: float = Field(3.0, ge=0.0, le=6.0)
    initial_coord_y: float = Field(3.0, ge=0.0, le=6.0)
    battery_level: Optional[float] = Field(95.0, ge=0.0, le=100.0)


class CourierLocationUpdateSchema(BaseModel):
    coord_x: float = Field(..., ge=0.0, le=6.0)
    coord_y: float = Field(..., ge=0.0, le=6.0)
    battery_level: float = Field(..., ge=0.0, le=100.0)


class CourierOfferItemSchema(BaseModel):
    order_id: int
    restaurant_id: int
    restaurant_coord_x: float
    restaurant_coord_y: float
    delivery_coord_x: float
    delivery_coord_y: float
    distancia_vial_km: float
    tiempo_viaje_est_min: float
    tarifa_propuesta: float
    segundos_restantes_oferta: float
    is_urgent: bool


class OrderAcceptSchema(BaseModel):
    courier_id: int = Field(..., description="Identificador del repartidor que acepta la comanda")


class OrderStatusUpdateSchema(BaseModel):
    courier_id: int
    new_status: str = Field(..., description="Nuevo estado: LlegadaARestaurante, EN_TRANSITO_CLIENTE, ENTREGADO, CANCELADO_INCIDENCIA_TRANSITO")
    current_coord_x: Optional[float] = Field(None, ge=0.0, le=6.0)
    current_coord_y: Optional[float] = Field(None, ge=0.0, le=6.0)
    notes: Optional[str] = None


# ---------------------------------------------------------
# Esquemas para Rastreo (Tracking)
# ---------------------------------------------------------
class TrackingResponseSchema(BaseModel):
    order_id: int
    status: str
    courier_id: Optional[int] = None
    courier_coord_x: Optional[float] = None
    courier_coord_y: Optional[float] = None
    delivery_coord_x: float
    delivery_coord_y: float
    distancia_vial_restante_km: Optional[float] = None
    tiempo_llegada_est_min: Optional[float] = None
    last_update: Optional[datetime] = None


# ---------------------------------------------------------
# Esquemas de Configuración y Salud (DevOps)
# ---------------------------------------------------------
class SystemConfigSchema(BaseModel):
    active_dispatch_policy: str = Field("synchronized", description="Política activa: 'synchronized' o 'greedy'")
    buffer_delta_t_min: float = Field(2.0, ge=0.0, le=5.0, description="Margen de holgura en minutos")
    max_shift_duration_min: float = Field(360.0, ge=1.0, description="Límite máximo de turno (6h = 360 min)")
    anti_limbo_max_counter_min: float = Field(20.0, ge=0.1, description="Límite máximo en mostrador antes de merma")
    urgency_bonus_multiplier: float = Field(1.20, ge=1.0, description="Multiplicador de bono urgente (+20%)")
    min_battery_threshold_pct: float = Field(15.0, ge=5.0, le=30.0, description="Reserva mínima de batería de smartphone")


class HealthResponseSchema(BaseModel):
    status: str
    database: str
    cpu_percent: float
    memory_mb: float
    latency_avg_ms: float
    uptime_seconds: float
