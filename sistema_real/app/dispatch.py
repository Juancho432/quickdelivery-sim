from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from sistema_real.app.models import OrderModel, CourierModel, RestaurantModel, TrackingRecordModel, utcnow
from sistema_real.app.config import system_config


def calculate_vial_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Calcula la distancia vial urbana aplicando el factor de sinuosidad tau = 1.25 (D-11 Excl-4)."""
    manhattan = abs(x2 - x1) + abs(y2 - y1)
    return round(1.25 * manhattan, 3)


def calculate_travel_time_min(distance_km: float, speed_kmh: float = 18.0) -> float:
    """Estima el tiempo de viaje en minutos a una velocidad media urbana de 18 km/h."""
    if distance_km <= 0.0:
        return 0.0
    return round((distance_km / speed_kmh) * 60.0, 2)


def promote_next_kitchen_order(restaurant_id: int, db: Session):
    """Promueve automáticamente la comanda FIFO más antigua de EN_COLA_COCINA a EN_PREPARACION."""
    restaurant = db.query(RestaurantModel).filter(RestaurantModel.id == restaurant_id).first()
    if not restaurant:
        return

    active_cooking = db.query(OrderModel).filter(
        OrderModel.restaurant_id == restaurant_id,
        OrderModel.status == "EN_PREPARACION"
    ).count()

    free_burners = restaurant.kitchen_capacity - active_cooking
    if free_burners > 0:
        next_order = db.query(OrderModel).filter(
            OrderModel.restaurant_id == restaurant_id,
            OrderModel.status == "EN_COLA_COCINA"
        ).order_by(OrderModel.t_creado.asc()).first()

        if next_order:
            next_order.status = "EN_PREPARACION"
            next_order.t_inicio_cocina = utcnow()
            db.commit()


def check_anti_limbo_timeout(order: OrderModel, db: Session) -> bool:
    """Verifica el protocolo anti-limbo (D-07): cancela si lleva >= 20 min en mostrador sin repartidor."""
    if order.status == "LISTO_EN_MOSTRADOR" and order.courier_id is None and order.t_listo is not None:
        dwell_min = (utcnow() - order.t_listo).total_seconds() / 60.0
        if dwell_min >= system_config.anti_limbo_max_counter_min:
            order.status = "CANCELADO_SIN_REPARTIDOR"
            order.cancellation_reason = "COUNTER_TIMEOUT_20MIN"
            db.commit()
            return True
    return False


def get_qualified_offers_for_courier(courier_id: int, db: Session) -> List[dict]:
    """Evalúa Just-In-Time las órdenes disponibles para las cuales el repartidor está calificado."""
    courier = db.query(CourierModel).filter(CourierModel.id == courier_id).first()
    if not courier or not courier.is_active or not courier.is_available:
        return []

    # Verificación dura de límite de turno (6 horas = 360 min)
    shift_min = (utcnow() - courier.shift_start_time).total_seconds() / 60.0
    if shift_min >= system_config.max_shift_duration_min:
        courier.is_active = False
        courier.is_available = False
        db.commit()
        return []

    # Consulta de órdenes activas sin asignar
    candidate_orders = db.query(OrderModel).filter(
        OrderModel.status.in_(["EN_PREPARACION", "LISTO_EN_MOSTRADOR", "OFERTADO"]),
        OrderModel.courier_id.is_(None)
    ).all()

    qualified_offers = []

    for order in candidate_orders:
        # Verificar protocolo anti-limbo primero
        if check_anti_limbo_timeout(order, db):
            continue

        restaurant = order.restaurant
        if not restaurant:
            continue

        # Cinemática vial hacia el restaurante
        d_local = calculate_vial_distance(courier.current_coord_x, courier.current_coord_y, restaurant.coord_x, restaurant.coord_y)
        t_viaje_local = calculate_travel_time_min(d_local)

        # Cinemática vial hacia el cliente
        d_cliente = calculate_vial_distance(restaurant.coord_x, restaurant.coord_y, order.delivery_coord_x, order.delivery_coord_y)
        t_viaje_cliente = calculate_travel_time_min(d_cliente)

        t_espera_est = 0.0 if order.status == "LISTO_EN_MOSTRADOR" else max(0.0, order.eta_listo - t_viaje_local)

        # Filtro preventivo de batería (D-08): drenaje de 0.15%/min con margen de seguridad >= 15%
        delta_bat_est = (t_viaje_local + t_espera_est + t_viaje_cliente) * 0.15
        if (courier.battery_level - delta_bat_est) < system_config.min_battery_threshold_pct:
            continue

        # Evaluación según política activa
        is_ready = order.status == "LISTO_EN_MOSTRADOR"
        
        # Cálculo de tarifa propuesta (base $2.50 + $0.80/km vial)
        tarifa = 2.50 + (0.80 * (d_local + d_cliente))
        if order.is_urgent or is_ready:
            tarifa *= system_config.urgency_bonus_multiplier

        qualified_offers.append({
            "order_id": order.id,
            "restaurant_id": restaurant.id,
            "restaurant_coord_x": restaurant.coord_x,
            "restaurant_coord_y": restaurant.coord_y,
            "delivery_coord_x": order.delivery_coord_x,
            "delivery_coord_y": order.delivery_coord_y,
            "distancia_vial_km": round(d_local + d_cliente, 2),
            "tiempo_viaje_est_min": round(t_viaje_local + t_viaje_cliente, 1),
            "tarifa_propuesta": round(tarifa, 2),
            "segundos_restantes_oferta": 45.0,
            "is_urgent": order.is_urgent or is_ready
        })

    return qualified_offers


def accept_order_atomic(order_id: int, courier_id: int, db: Session) -> OrderModel:
    """Asignación atómica mediante SELECT FOR UPDATE para resolver carreras concurrentes en 45 s."""
    # Bloqueo a nivel de fila
    order = db.query(OrderModel).filter(OrderModel.id == order_id).with_for_update().first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Orden #{order_id} no encontrada")

    if order.courier_id is not None or order.status in ["ASIGNADO", "EN_TRANSITO_CLIENTE", "ENTREGADO", "CANCELADO_POR_CLIENTE", "CANCELADO_SIN_REPARTIDOR"]:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La orden ya fue asignada o no está disponible")

    courier = db.query(CourierModel).filter(CourierModel.id == courier_id).with_for_update().first()
    if not courier or not courier.is_active or not courier.is_available:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El repartidor no está disponible o está inactivo")

    # Asignación exitosa
    order.courier_id = courier_id
    order.status = "ASIGNADO"
    courier.is_available = False

    db.commit()
    db.refresh(order)
    return order


def transition_order_status(order_id: int, courier_id: int, new_status: str, coord_x: Optional[float], coord_y: Optional[float], db: Session) -> OrderModel:
    """Gestiona los hitos físicos del viaje y el logout forzado por límites D-08 al completar entrega."""
    order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada")

    if order.courier_id != courier_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="El repartidor no tiene asignada esta orden")

    courier = db.query(CourierModel).filter(CourierModel.id == courier_id).first()

    # Actualizar coordenadas del repartidor si se proporcionan
    if coord_x is not None and coord_y is not None and courier:
        courier.current_coord_x = coord_x
        courier.current_coord_y = coord_y

    now = utcnow()

    if new_status == "LlegadaARestaurante":
        pass  # Notificación de arribo físico al local
    elif new_status == "EN_TRANSITO_CLIENTE":
        order.status = "EN_TRANSITO_CLIENTE"
        order.t_recogida = now
    elif new_status == "ENTREGADO":
        order.status = "ENTREGADO"
        order.t_entregado = now
        if courier:
            courier.is_available = True
            # Regla D-08: Verificar si cumplió 6h o batería < 15% al finalizar entrega
            shift_min = (now - courier.shift_start_time).total_seconds() / 60.0
            if shift_min >= system_config.max_shift_duration_min or courier.battery_level < system_config.min_battery_threshold_pct:
                courier.is_active = False
                courier.is_available = False
    elif new_status == "CANCELADO_INCIDENCIA_TRANSITO":
        order.status = "CANCELADO_INCIDENCIA_TRANSITO"
        order.cancellation_reason = "INCIDENT_IN_TRANSIT"
        if courier:
            courier.is_available = True
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Estado {new_status} no válido")

    db.commit()
    db.refresh(order)
    return order
