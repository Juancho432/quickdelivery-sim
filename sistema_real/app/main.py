import time
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

from sistema_real.app.database import engine, Base, get_db
from sistema_real.app.models import OrderModel, CourierModel, RestaurantModel, TrackingRecordModel, seed_database, utcnow
from sistema_real.app.schemas import (
    OrderCreateSchema, OrderResponseSchema, OrderCancelSchema,
    KDSOrderResponseSchema, OrderReadyResponseSchema,
    CourierLoginSchema, CourierLocationUpdateSchema, CourierOfferItemSchema,
    OrderAcceptSchema, OrderStatusUpdateSchema,
    TrackingResponseSchema, SystemConfigSchema, HealthResponseSchema
)
from sistema_real.app.telemetry import TelemetryMiddleware, get_telemetry_stats
from sistema_real.app.dispatch import (
    calculate_vial_distance, calculate_travel_time_min,
    promote_next_kitchen_order, check_anti_limbo_timeout,
    get_qualified_offers_for_courier, accept_order_atomic,
    transition_order_status
)
from sistema_real.app.config import system_config

app_start_time = time.time()

app = FastAPI(
    title="QuickDelivery Sim — API del Sistema Real",
    description="API REST modular para el sistema de pedidos a domicilio, despacho sincronizado y telemetria (Entrega Parcial 1).",
    version="1.0.0"
)

# Middleware de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware de Telemetría (captura de latencias HTTP y CPU/RAM con psutil)
app.add_middleware(TelemetryMiddleware)


@app.on_event("startup")
def startup_event():
    """Crea las tablas en PostgreSQL 15 e inserta los datos semilla (seed) de 10 restaurantes y repartidores."""
    try:
        Base.metadata.create_all(bind=engine)
        db = next(get_db())
        seed_database(db)
    except Exception as e:
        print(f"[Startup Warning] Base de datos no disponible de inmediato o ya inicializada: {e}")


# ==============================================================================
# 1. ENDPOINTS DE CLIENTES (Creación, Rastreo y Cancelación)
# ==============================================================================

@app.post("/api/v1/orders/", response_model=OrderResponseSchema, status_code=status.HTTP_201_CREATED, tags=["Clientes"])
def create_order(payload: OrderCreateSchema, db: Session = Depends(get_db)):
    """E1: Ingesta de pedidos. Evalúa capacidad de cocina (C1) y programa en cola o preparación."""
    restaurant = db.query(RestaurantModel).filter(RestaurantModel.id == payload.restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurante no encontrado")

    # Contención de fogones (Criterio C1):
    active_cooking = db.query(OrderModel).filter(
        OrderModel.restaurant_id == payload.restaurant_id,
        OrderModel.status == "EN_PREPARACION"
    ).count()

    waiting_in_queue = db.query(OrderModel).filter(
        OrderModel.restaurant_id == payload.restaurant_id,
        OrderModel.status == "EN_COLA_COCINA"
    ).count()

    # Si hay fogones libres, pasa directamente a cocción; si no, a cola FIFO
    if active_cooking < restaurant.kitchen_capacity:
        order_status = "EN_PREPARACION"
        t_inicio = utcnow()
    else:
        order_status = "EN_COLA_COCINA"
        t_inicio = None

    # Estimación de disponibilidad física (ETA de cocina)
    eta_min = 18.5 + (waiting_in_queue * 18.5 / restaurant.kitchen_capacity)

    new_order = OrderModel(
        customer_id=payload.customer_id,
        restaurant_id=payload.restaurant_id,
        delivery_coord_x=payload.delivery_coord_x,
        delivery_coord_y=payload.delivery_coord_y,
        status=order_status,
        eta_listo=round(eta_min, 1),
        t_inicio_cocina=t_inicio
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    return new_order


@app.get("/api/v1/orders/{order_id}/tracking", response_model=TrackingResponseSchema, tags=["Clientes"])
def get_order_tracking(order_id: int, db: Session = Depends(get_db)):
    """E2: Rastreo GPS en tiempo real del repartidor y avance del pedido."""
    order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    check_anti_limbo_timeout(order, db)

    courier_x = None
    courier_y = None
    dist_restante = None
    tiempo_est = None

    if order.courier:
        courier_x = order.courier.current_coord_x
        courier_y = order.courier.current_coord_y
        dist_restante = calculate_vial_distance(courier_x, courier_y, order.delivery_coord_x, order.delivery_coord_y)
        tiempo_est = calculate_travel_time_min(dist_restante)

    return TrackingResponseSchema(
        order_id=order.id,
        status=order.status,
        courier_id=order.courier_id,
        courier_coord_x=courier_x,
        courier_coord_y=courier_y,
        delivery_coord_x=order.delivery_coord_x,
        delivery_coord_y=order.delivery_coord_y,
        distancia_vial_restante_km=dist_restante,
        tiempo_llegada_est_min=tiempo_est,
        last_update=utcnow()
    )


@app.post("/api/v1/orders/{order_id}/cancel", response_model=OrderResponseSchema, tags=["Clientes"])
def cancel_order_by_customer(order_id: int, payload: OrderCancelSchema, db: Session = Depends(get_db)):
    """E3: Cancelación voluntaria del cliente por impaciencia (Weibull). Libera fogón o courier."""
    order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    if order.status in ["ENTREGADO", "CANCELADO_POR_CLIENTE", "CANCELADO_SIN_REPARTIDOR", "CANCELADO_INCIDENCIA_TRANSITO"]:
        raise HTTPException(status_code=400, detail="La orden no puede cancelarse en su estado actual")

    was_cooking = (order.status == "EN_PREPARACION")
    order.status = "CANCELADO_POR_CLIENTE"
    order.cancellation_reason = payload.reason

    # Si tenía repartidor asignado, lo libera
    if order.courier:
        order.courier.is_available = True

    db.commit()

    # Si estaba en fogón, promueve automáticamente la siguiente orden en cola FIFO
    if was_cooking:
        promote_next_kitchen_order(order.restaurant_id, db)

    db.refresh(order)
    return order


# ==============================================================================
# 2. ENDPOINTS DE RESTAURANTES (KDS y Fin de Cocción)
# ==============================================================================

@app.get("/api/v1/restaurants/{restaurant_id}/orders", response_model=List[KDSOrderResponseSchema], tags=["Restaurantes (KDS)"])
def get_restaurant_orders(
    restaurant_id: int,
    status_filter: Optional[str] = Query(None, description="Filtro opcional de estado, ej. EN_PREPARACION"),
    db: Session = Depends(get_db)
):
    """E4: Pantalla KDS del restaurante. Exclusión 2 (D-11): NO incluye recetas ni ingredientes."""
    query = db.query(OrderModel).filter(OrderModel.restaurant_id == restaurant_id)
    if status_filter:
        query = query.filter(OrderModel.status == status_filter)
    else:
        query = query.filter(OrderModel.status.in_(["EN_COLA_COCINA", "EN_PREPARACION", "LISTO_EN_MOSTRADOR"]))

    orders = query.order_by(OrderModel.t_creado.asc()).all()
    results = []
    now = utcnow()

    for o in orders:
        check_anti_limbo_timeout(o, db)
        tiempo_espera = (now - o.t_creado).total_seconds() / 60.0
        results.append(KDSOrderResponseSchema(
            order_id=o.id,
            restaurant_id=o.restaurant_id,
            status=o.status,
            tiempo_espera_cola_min=round(tiempo_espera, 1),
            eta_listo=o.eta_listo,
            created_at=o.t_creado
        ))

    return results


@app.post("/api/v1/orders/{order_id}/ready", response_model=OrderResponseSchema, tags=["Restaurantes (KDS)"])
def mark_order_ready(order_id: int, db: Session = Depends(get_db)):
    """E5: Fin de Cocción (D-09). Libera fogón, sella t_listo y promueve la comanda FIFO más antigua."""
    order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    order.status = "LISTO_EN_MOSTRADOR"
    order.t_listo = utcnow()
    order.is_urgent = True  # Conmuta a prioridad urgente con bono +20%
    db.commit()

    # Promoción automática del siguiente pedido en cola de cocina
    promote_next_kitchen_order(order.restaurant_id, db)

    db.refresh(order)
    return order


# ==============================================================================
# 3. ENDPOINTS DE REPARTIDORES (Login, Pings GPS, Ofertas, Aceptación, Hitos y Logout)
# ==============================================================================

@app.post("/api/v1/couriers/login", tags=["Repartidores"], status_code=status.HTTP_201_CREATED)
def courier_login(payload: CourierLoginSchema, db: Session = Depends(get_db)):
    """E6: Conexión de repartidor (NHPP). Registra inicio de turno de 6h y batería inicial."""
    new_courier = CourierModel(
        name=payload.name,
        current_coord_x=payload.initial_coord_x,
        current_coord_y=payload.initial_coord_y,
        battery_level=payload.battery_level or 95.0,
        shift_start_time=utcnow(),
        is_available=True,
        is_active=True
    )
    db.add(new_courier)
    db.commit()
    db.refresh(new_courier)
    return {
        "courier_id": new_courier.id,
        "name": new_courier.name,
        "battery_level": new_courier.battery_level,
        "shift_start_time": new_courier.shift_start_time,
        "message": "Turno iniciado correctamente (Límite máximo 6 horas)"
    }


@app.post("/api/v1/couriers/{courier_id}/location", tags=["Repartidores"])
def update_courier_location(courier_id: int, payload: CourierLocationUpdateSchema, db: Session = Depends(get_db)):
    """E7: Pings periódicos de telemetría GPS y batería (Pregunta de Decisión 3: 5s vs 15s)."""
    courier = db.query(CourierModel).filter(CourierModel.id == courier_id).first()
    if not courier or not courier.is_active:
        raise HTTPException(status_code=404, detail="Repartidor no encontrado o inactivo")

    courier.current_coord_x = payload.coord_x
    courier.current_coord_y = payload.coord_y
    courier.battery_level = payload.battery_level

    # Registro en historial de rastreo
    tracking_record = TrackingRecordModel(
        courier_id=courier_id,
        coord_x=payload.coord_x,
        coord_y=payload.coord_y,
        battery_level=payload.battery_level
    )
    db.add(tracking_record)
    db.commit()
    return {"status": "updated", "courier_id": courier_id, "battery_level": payload.battery_level}


@app.get("/api/v1/couriers/{courier_id}/offers", response_model=List[CourierOfferItemSchema], tags=["Repartidores"])
def get_courier_offers(courier_id: int, db: Session = Depends(get_db)):
    """E8: Sondeo Just-In-Time de ofertas calificadas (batería >= 15%, turno < 6h, ventana de 45 s)."""
    offers = get_qualified_offers_for_courier(courier_id, db)
    return offers


@app.post("/api/v1/orders/{order_id}/accept", response_model=OrderResponseSchema, tags=["Repartidores"])
def accept_order(order_id: int, payload: OrderAcceptSchema, db: Session = Depends(get_db)):
    """E9: Aceptación atómica concurrente en ventana de 45 s con SELECT FOR UPDATE."""
    assigned_order = accept_order_atomic(order_id, payload.courier_id, db)
    return assigned_order


@app.patch("/api/v1/orders/{order_id}/status", response_model=OrderResponseSchema, tags=["Repartidores"])
def update_order_status(order_id: int, payload: OrderStatusUpdateSchema, db: Session = Depends(get_db)):
    """E10: Notificación de hitos del viaje (llegada, recogida y entrega con logout automático D-08)."""
    updated_order = transition_order_status(
        order_id=order_id,
        courier_id=payload.courier_id,
        new_status=payload.new_status,
        coord_x=payload.current_coord_x,
        coord_y=payload.current_coord_y,
        db=db
    )
    return updated_order


@app.post("/api/v1/couriers/{courier_id}/logout", tags=["Repartidores"])
def courier_logout(courier_id: int, db: Session = Depends(get_db)):
    """E11: Cierre formal de turno (voluntario o forzado tras 6 horas o batería < 15%)."""
    courier = db.query(CourierModel).filter(CourierModel.id == courier_id).first()
    if not courier:
        raise HTTPException(status_code=404, detail="Repartidor no encontrado")

    courier.is_active = False
    courier.is_available = False
    db.commit()
    return {"message": f"Repartidor {courier.name} desconectado exitosamente", "courier_id": courier_id}


# ==============================================================================
# 4. ENDPOINTS DE CONFIGURACIÓN Y SALUD (DevOps)
# ==============================================================================

@app.get("/api/v1/config/", response_model=SystemConfigSchema, tags=["Configuración"])
def get_system_config():
    """E12a: Consulta los parámetros operativos en tiempo real."""
    return system_config.to_dict()


@app.put("/api/v1/config/", response_model=SystemConfigSchema, tags=["Configuración"])
def update_system_config(payload: SystemConfigSchema):
    """E12b: Modifica en caliente la política de asignación y umbrales temporales para pruebas."""
    updated = system_config.update(**payload.model_dump())
    return updated


@app.get("/api/v1/telemetry/health", response_model=HealthResponseSchema, tags=["DevOps"])
def healthcheck(db: Session = Depends(get_db)):
    """E13: Diagnóstico continuo de hardware (CPU, RAM vía psutil), latencia y estado de PostgreSQL."""
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"disconnected: {e}"

    stats = get_telemetry_stats()
    uptime = time.time() - app_start_time

    return HealthResponseSchema(
        status="healthy" if db_status == "connected" else "degraded",
        database=db_status,
        cpu_percent=stats["cpu_percent"],
        memory_mb=stats["memory_mb"],
        latency_avg_ms=stats["latency_avg_ms"],
        uptime_seconds=round(uptime, 1)
    )
