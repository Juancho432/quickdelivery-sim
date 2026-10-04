"""
Renderizador SVG para el Plano Cartesiano 2D [0.00 km, 6.00 km].
Genera el contenido vectorial para el mapa interactivo con restaurantes, clientes,
repartidores y ajuste dinámico de transparencias.
"""
from typing import List, Dict, Any, Optional, Tuple


def km_to_px(x_km: float, y_km: float) -> Tuple[float, float]:
    """Convierte coordenadas en km [0.0, 6.0] a píxeles SVG [55..635, 625..45]."""
    scale = 580.0 / 6.0
    px = 55.0 + max(0.0, min(6.0, float(x_km))) * scale
    py = 625.0 - max(0.0, min(6.0, float(y_km))) * scale
    return px, py


def render_cartesian_svg_content(
    restaurants: List[Dict[str, Any]],
    couriers: List[Dict[str, Any]],
    active_orders: List[Dict[str, Any]],
    selected_order_id: Optional[int] = None,
    preview_point: Optional[Tuple[float, float]] = None,
    layers: Optional[Dict[str, bool]] = None
) -> str:
    """
    Genera el contenido vectorial SVG (defs, cuadrícula, entidades y trayectorias).
    Diseñado para integrarse directamente en ui.interactive_image o dentro de un <svg>.
    Soporta filtrado dinámico de capas por estado booleano.
    """
    if layers is None:
        layers = {
            "restaurants": True,
            "customers": True,
            "couriers_free": True,
            "couriers_busy": True,
            "preview": True,
        }

    selected_order = None
    if selected_order_id is not None:
        for ord_item in active_orders:
            try:
                if int(ord_item.get("id")) == int(selected_order_id):
                    selected_order = ord_item
                    break
            except (ValueError, TypeError):
                if str(ord_item.get("id")) == str(selected_order_id):
                    selected_order = ord_item
                    break

    sel_rest_id = selected_order.get("restaurant_id") if selected_order else None
    sel_courier_id = selected_order.get("courier_id") if selected_order else None

    svg_parts = []

    # --- Filtros, Patrones y Estilos ---
    svg_parts.append("""
    <defs>
      <pattern id="grid-sub" width="19.333" height="19.333" patternUnits="userSpaceOnUse">
        <path d="M 19.333 0 L 0 0 0 19.333" fill="none" stroke="#172554" stroke-width="0.7" stroke-opacity="0.5"/>
      </pattern>
      <pattern id="grid-main" width="96.667" height="96.667" patternUnits="userSpaceOnUse">
        <rect width="96.667" height="96.667" fill="url(#grid-sub)" />
        <path d="M 96.667 0 L 0 0 0 96.667" fill="none" stroke="#1e293b" stroke-width="1.6"/>
      </pattern>
      <filter id="glow-gold" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="5" result="coloredBlur"/>
        <feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
      <filter id="glow-cyan" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
        <feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
      <filter id="glow-pink" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="5" result="coloredBlur"/>
        <feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
    </defs>
    """)

    # --- Área de Fondo y Cuadrícula ---
    svg_parts.append('<rect x="0" y="0" width="680" height="680" fill="#0b1120" rx="10"/>')
    svg_parts.append('<rect x="55" y="45" width="580" height="580" fill="#0f172a" />')
    svg_parts.append('<rect x="55" y="45" width="580" height="580" fill="url(#grid-main)" />')
    svg_parts.append('<rect x="55" y="45" width="580" height="580" fill="none" stroke="#334155" stroke-width="2" />')

    # --- Marcas y Etiquetas de Ejes (0.0 a 6.0 km) ---
    scale = 580.0 / 6.0
    for i in range(7):
        km = float(i)
        x_p = 55.0 + km * scale
        y_p = 625.0 - km * scale

        # Eje X
        svg_parts.append(f'<line x1="{x_p}" y1="625" x2="{x_p}" y2="633" stroke="#64748b" stroke-width="1.5"/>')
        svg_parts.append(f'<text x="{x_p}" y="650" fill="#94a3b8" font-size="11" font-family="sans-serif" text-anchor="middle">{km:.1f}k</text>')

        # Eje Y
        svg_parts.append(f'<line x1="47" y1="{y_p}" x2="55" y2="{y_p}" stroke="#64748b" stroke-width="1.5"/>')
        svg_parts.append(f'<text x="42" y="{y_p + 4}" fill="#94a3b8" font-size="11" font-family="sans-serif" text-anchor="end">{km:.1f}k</text>')

    # Títulos de Ejes
    svg_parts.append('<text x="345" y="672" fill="#cbd5e1" font-size="12" font-weight="bold" font-family="sans-serif" text-anchor="middle">Eje X (km) — Longitud urbana</text>')
    svg_parts.append('<text x="18" y="335" fill="#cbd5e1" font-size="12" font-weight="bold" font-family="sans-serif" text-anchor="middle" transform="rotate(-90 18 335)">Eje Y (km) — Latitud urbana</text>')

    # =========================================================================
    # TRAYECTORIAS Y RUTAS DEL PEDIDO SELECCIONADO
    # =========================================================================
    if selected_order:
        r_info = next((r for r in restaurants if r.get("id") == sel_rest_id), None)
        c_info = next((c for c in couriers if c.get("id") == sel_courier_id), None)

        cust_x, cust_y = selected_order.get("delivery_coord_x", 0.0), selected_order.get("delivery_coord_y", 0.0)
        px_cust, py_cust = km_to_px(cust_x, cust_y)

        if r_info and (layers.get("customers", True) or layers.get("restaurants", True)):
            px_rest, py_rest = km_to_px(r_info.get("coord_x", 0.0), r_info.get("coord_y", 0.0))

            if c_info:
                px_cour, py_cour = km_to_px(c_info.get("current_coord_x", 0.0), c_info.get("current_coord_y", 0.0))
                st = selected_order.get("status", "")

                if st in ["ASIGNADO", "OFERTADO"]:
                    # Repartidor yendo al Restaurante
                    if layers.get("couriers_busy", True) or layers.get("restaurants", True):
                        svg_parts.append(f'<line x1="{px_cour}" y1="{py_cour}" x2="{px_rest}" y2="{py_rest}" stroke="#38bdf8" stroke-width="3" stroke-dasharray="7,4" filter="url(#glow-cyan)"/>')
                    if layers.get("restaurants", True) and layers.get("customers", True):
                        svg_parts.append(f'<line x1="{px_rest}" y1="{py_rest}" x2="{px_cust}" y2="{py_cust}" stroke="#f59e0b" stroke-width="2" stroke-dasharray="4,4" stroke-opacity="0.6"/>')
                elif st == "EN_TRANSITO_CLIENTE":
                    # Repartidor en tránsito hacia el Cliente
                    if (layers.get("couriers_busy", True) or layers.get("couriers_free", True)) and layers.get("customers", True):
                        svg_parts.append(f'<line x1="{px_cour}" y1="{py_cour}" x2="{px_cust}" y2="{py_cust}" stroke="#ec4899" stroke-width="4" stroke-dasharray="9,5" filter="url(#glow-pink)"/>')
                else:
                    if layers.get("restaurants", True) and layers.get("customers", True):
                        svg_parts.append(f'<line x1="{px_rest}" y1="{py_rest}" x2="{px_cust}" y2="{py_cust}" stroke="#f59e0b" stroke-width="2.5" stroke-dasharray="6,4"/>')
            else:
                if layers.get("restaurants", True) and layers.get("customers", True):
                    svg_parts.append(f'<line x1="{px_rest}" y1="{py_rest}" x2="{px_cust}" y2="{py_cust}" stroke="#f59e0b" stroke-width="2.5" stroke-dasharray="6,4"/>')

    # =========================================================================
    # 1. RESTAURANTES (10 locales)
    # =========================================================================
    if layers.get("restaurants", True):
        for r in restaurants:
            rid = r.get("id")
            rx, ry = r.get("coord_x", 0.0), r.get("coord_y", 0.0)
            px, py = km_to_px(rx, ry)
            r_name = r.get("name", f"R{rid}")
            cap = r.get("kitchen_capacity", 4)

            is_highlighted = (selected_order is not None and sel_rest_id is not None and str(rid) == str(sel_rest_id))
            if selected_order is not None:
                op = "1.0" if is_highlighted else "0.15"
            else:
                op = "0.95"

            if is_highlighted:
                svg_parts.append(f'<circle cx="{px}" cy="{py}" r="26" fill="#10b981" fill-opacity="0.25" stroke="#34d399" stroke-width="2.5" filter="url(#glow-gold)"/>')

            svg_parts.append(f'<g opacity="{op}">'
                             f'<rect x="{px-13}" y="{py-13}" width="26" height="26" fill="#059669" stroke="#34d399" stroke-width="2" rx="5"/>'
                             f'<text x="{px}" y="{py+5}" fill="#ffffff" font-size="12" font-weight="bold" font-family="sans-serif" text-anchor="middle">R{rid}</text>'
                             f'<rect x="{px-40}" y="{py-28}" width="80" height="15" fill="#064e3b" fill-opacity="0.85" rx="3"/>'
                             f'<text x="{px}" y="{py-17}" fill="#a7f3d0" font-size="9.5" font-weight="bold" font-family="sans-serif" text-anchor="middle">{r_name[:12]} ({cap}k)</text>'
                             f'</g>')

    # =========================================================================
    # 2. CLIENTES / PEDIDOS ACTIVOS
    # =========================================================================
    if layers.get("customers", True):
        for o in active_orders:
            oid = o.get("id")
            cx, cy = o.get("delivery_coord_x", 0.0), o.get("delivery_coord_y", 0.0)
            px, py = km_to_px(cx, cy)
            cid = o.get("customer_id", f"C-{oid}")
            st = o.get("status", "")

            is_highlighted = (selected_order is not None and str(oid) == str(selected_order.get("id")))
            if selected_order is not None:
                op = "1.0" if is_highlighted else "0.15"
            else:
                op = "0.9"

            fill_color = "#f59e0b"
            if "CANCELADO" in st:
                fill_color = "#ef4444"
            elif st == "ENTREGADO":
                fill_color = "#10b981"

            if is_highlighted:
                svg_parts.append(f'<circle cx="{px}" cy="{py}" r="22" fill="{fill_color}" fill-opacity="0.25" stroke="{fill_color}" stroke-width="2.5" filter="url(#glow-gold)"/>')

            svg_parts.append(f'<g opacity="{op}">'
                             f'<circle cx="{px}" cy="{py}" r="9" fill="{fill_color}" stroke="#ffffff" stroke-width="2"/>'
                             f'<rect x="{px-35}" y="{py+14}" width="70" height="14" fill="#78350f" fill-opacity="0.85" rx="3"/>'
                             f'<text x="{px}" y="{py+25}" fill="#fde68a" font-size="9" font-weight="bold" font-family="sans-serif" text-anchor="middle">{cid}</text>'
                             f'</g>')

    # =========================================================================
    # 3. REPARTIDORES (Couriers)
    # =========================================================================
    for c in couriers:
        cid = c.get("id")
        cx, cy = c.get("current_coord_x", 0.0), c.get("current_coord_y", 0.0)
        px, py = km_to_px(cx, cy)
        cname = c.get("name", f"C-{cid}")
        is_avail = c.get("is_available", True)
        is_act = c.get("is_active", True)
        bat = c.get("battery_level", 100.0)

        # Filtrar por capa según disponibilidad (libre vs ocupado/en ruta)
        if is_avail and not layers.get("couriers_free", True):
            continue
        if not is_avail and not layers.get("couriers_busy", True):
            continue

        is_highlighted = (selected_order is not None and sel_courier_id is not None and str(cid) == str(sel_courier_id))
        if selected_order is not None:
            op = "1.0" if is_highlighted else "0.15"
        else:
            op = "0.95"

        c_color = "#38bdf8" if is_avail else "#ec4899"
        if not is_act:
            c_color = "#64748b"

        if is_highlighted:
            svg_parts.append(f'<circle cx="{px}" cy="{py}" r="24" fill="{c_color}" fill-opacity="0.3" stroke="{c_color}" stroke-width="2.5" filter="url(#glow-cyan)"/>')

        svg_parts.append(f'<g opacity="{op}">'
                         f'<circle cx="{px}" cy="{py}" r="10" fill="{c_color}" stroke="#ffffff" stroke-width="2"/>'
                         f'<text x="{px}" y="{py+3.5}" fill="#0f172a" font-size="9" font-weight="bold" font-family="sans-serif" text-anchor="middle">M</text>'
                         f'<rect x="{px-35}" y="{py-25}" width="70" height="14" fill="#0f172a" fill-opacity="0.85" rx="3" stroke="{c_color}" stroke-width="1"/>'
                         f'<text x="{px}" y="{py-14}" fill="#ffffff" font-size="8.5" font-weight="bold" font-family="sans-serif" text-anchor="middle">{cname[:9]} ({bat:.0f}%)</text>'
                         f'</g>')

    # =========================================================================
    # 4. PUNTO PREVIEW / CLIC DE NUEVO PEDIDO
    # =========================================================================
    if preview_point and layers.get("preview", True):
        px_prev, py_prev = km_to_px(preview_point[0], preview_point[1])
        svg_parts.append(f'<g>'
                         f'<circle cx="{px_prev}" cy="{py_prev}" r="15" fill="#a855f7" fill-opacity="0.35" stroke="#c084fc" stroke-width="2" stroke-dasharray="3,3"/>'
                         f'<circle cx="{px_prev}" cy="{py_prev}" r="5" fill="#c084fc" stroke="#ffffff" stroke-width="1.5"/>'
                         f'<text x="{px_prev}" y="{py_prev-18}" fill="#e9d5ff" font-size="10" font-weight="bold" font-family="sans-serif" text-anchor="middle">Nuevo ({preview_point[0]:.2f}, {preview_point[1]:.2f})</text>'
                         f'</g>')

    return "".join(svg_parts)


def render_cartesian_map(
    restaurants: List[Dict[str, Any]],
    couriers: List[Dict[str, Any]],
    active_orders: List[Dict[str, Any]],
    selected_order_id: Optional[int] = None,
    preview_point: Optional[Tuple[float, float]] = None,
    layers: Optional[Dict[str, bool]] = None
) -> str:
    """
    Genera el marcado SVG completo con etiqueta <svg> contenedora.
    Mantiene compatibilidad total con pruebas unitarias y renderizados directos.
    """
    content = render_cartesian_svg_content(
        restaurants=restaurants,
        couriers=couriers,
        active_orders=active_orders,
        selected_order_id=selected_order_id,
        preview_point=preview_point,
        layers=layers
    )
    return (
        '<svg viewBox="0 0 680 680" width="100%" height="100%" '
        'xmlns="http://www.w3.org/2000/svg" '
        'style="background-color: #0b1120; border-radius: 12px; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5); user-select: none;">'
        + content +
        '</svg>'
    )
