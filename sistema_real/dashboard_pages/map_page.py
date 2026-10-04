"""
Página 1 del Dashboard: Plano Cartesiano 2D, Operaciones y Control de Pedidos.
Muestra el mapa a la izquierda con leyendas laterales y los paneles de control apilados a la derecha.
"""
import random
from nicegui import ui, events
from sistema_real.map_renderer import render_cartesian_svg_content
from sistema_real.dashboard_pages.common import state, api_client, common_header


@ui.page("/")
async def page_operations():
    ui.query("body").classes("bg-slate-950 text-slate-100 font-sans")
    common_header("/")

    if not state["restaurants"]:
        state["restaurants"] = await api_client.get_restaurants()
    if not state["couriers"]:
        state["couriers"] = await api_client.get_couriers()

    # Configuración de capas para la leyenda interactiva
    LAYERS_DEF = [
        ("restaurants", "Restaurantes (10)", "bg-emerald-500", "rounded"),
        ("customers", "Clientes", "bg-amber-500", "rounded-full"),
        ("couriers_free", "Couriers Libres", "bg-sky-400", "rounded-full"),
        ("couriers_busy", "Couriers en Ruta", "bg-pink-500", "rounded-full"),
        ("preview", "Punto de Clic", "bg-purple-500", "rounded-full"),
    ]

    def update_map_view():
        map_image.content = render_cartesian_svg_content(
            restaurants=state["restaurants"],
            couriers=state["couriers"],
            active_orders=state["orders"],
            selected_order_id=state["selected_order_id"],
            preview_point=state["preview_point"],
            layers=state.get("map_layers")
        )

    # Manejador nativo de clics sobre el mapa interactivo (Pixel -> Km)
    def handle_map_mouse(e: events.MouseEventArguments):
        if e.type == "click":
            # Coordenadas exactas en píxeles del canvas 680x680
            # Eje X: 0 km en px 55, 6 km en px 635 (ancho 580 px)
            # Eje Y: 0 km en px 625, 6 km en px 45 (alto 580 px)
            x_km = round(max(0.0, min(6.0, (e.image_x - 55.0) * (6.0 / 580.0))), 2)
            y_km = round(max(0.0, min(6.0, (625.0 - e.image_y) * (6.0 / 580.0))), 2)

            state["preview_point"] = (x_km, y_km)
            coord_x_input.set_value(x_km)
            coord_y_input.set_value(y_km)
            update_map_view()

    with ui.row().classes("w-full p-2.5 gap-3 items-start max-w-[1700px] mx-auto flex-col lg:flex-row flex-nowrap"):

        # ======================================================================
        # COLUMNA IZQUIERDA: PLANO CARTESIANO 2D + LEYENDAS AL LADO
        # ======================================================================
        with ui.column().classes("w-full lg:w-1/2 xl:w-7/12 gap-2 flex-shrink-0"):
            with ui.card().classes("w-full p-3 bg-slate-900 border border-slate-800 shadow-xl rounded-xl flex flex-col"):
                with ui.row().classes("w-full justify-between items-center mb-1"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("map", size="sm").classes("text-indigo-400")
                        ui.label("Plano Cartesiano 2D (0.00 a 6.00 km)").classes("text-sm font-bold text-white")
                    ui.button("Ver Todos", on_click=lambda: clear_selection()).props("flat dense").classes("text-xs text-indigo-400")

                ui.label("Haz clic en el plano para fijar coordenadas de entrega del cliente.").classes("text-[11px] text-slate-400 mb-1")

                # Fila horizontal: Mapa interactivo + Leyendas a su lado
                with ui.row().classes("w-full items-stretch gap-2.5 flex-nowrap"):
                    # Mapa interactivo con NiceGUI InteractiveImage (sin recargas, crosshair activo)
                    map_image = ui.interactive_image(
                        size=(680, 680),
                        content=render_cartesian_svg_content(
                            restaurants=state["restaurants"],
                            couriers=state["couriers"],
                            active_orders=state["orders"],
                            selected_order_id=state["selected_order_id"],
                            preview_point=state["preview_point"],
                            layers=state.get("map_layers")
                        ),
                        on_mouse=handle_map_mouse,
                        events=["click"],
                        cross="#38bdf8",
                        sanitize=False
                    ).classes("flex-1 max-h-[460px] aspect-square rounded-lg border border-slate-800 bg-slate-950")

                    # Leyenda lateral vertical interactiva con filtros booleanos
                    with ui.column().classes("w-44 gap-2 p-2.5 bg-slate-950 rounded-lg border border-slate-800 text-[11px] text-slate-300 flex-shrink-0 justify-between"):
                        with ui.column().classes("gap-1.5 w-full"):
                            with ui.row().classes("w-full justify-between items-center mb-0.5"):
                                ui.label("Filtro Leyenda").classes("text-xs font-bold text-white")
                                with ui.row().classes("gap-1"):
                                    ui.button("Todos", on_click=lambda: set_all_layers(True)).props("flat dense").classes("text-[10px] text-indigo-400 p-0")
                                    ui.label("|").classes("text-[10px] text-slate-600")
                                    ui.button("Ninguno", on_click=lambda: set_all_layers(False)).props("flat dense").classes("text-[10px] text-slate-400 p-0")

                            legend_items_container = ui.column().classes("gap-1 w-full")

                            def render_legend_items():
                                legend_items_container.clear()
                                with legend_items_container:
                                    for key, label, color_cls, shape_cls in LAYERS_DEF:
                                        is_active = state["map_layers"].get(key, True)
                                        bg_cls = "bg-slate-900 border-slate-700 text-slate-100" if is_active else "bg-slate-950/60 border-slate-900 text-slate-500 opacity-50"
                                        icon_name = "check_box" if is_active else "check_box_outline_blank"
                                        icon_color = "text-indigo-400" if is_active else "text-slate-600"
                                        marker_color = color_cls if is_active else "bg-slate-600"

                                        def make_toggle(k=key):
                                            def toggle():
                                                state["map_layers"][k] = not state["map_layers"].get(k, True)
                                                render_legend_items()
                                                update_map_view()
                                            return toggle

                                        with ui.row().classes(
                                            f"w-full items-center justify-between px-2 py-1 rounded-md border cursor-pointer select-none transition-all hover:border-slate-600 {bg_cls}"
                                        ).on("click", make_toggle(key)):
                                            with ui.row().classes("items-center gap-1.5"):
                                                ui.element("span").classes(f"w-2.5 h-2.5 {marker_color} {shape_cls}")
                                                ui.label(label).classes("text-[11px] font-medium")
                                            ui.icon(icon_name, size="xs").classes(icon_color)

                            def set_all_layers(active: bool):
                                for k, _, _, _ in LAYERS_DEF:
                                    state["map_layers"][k] = active
                                render_legend_items()
                                update_map_view()

                            render_legend_items()

                        with ui.column().classes("gap-1 w-full border-t border-slate-800 pt-2"):
                            ui.label("Guía de Uso:").classes("text-[10px] font-semibold text-slate-400")
                            ui.label("• Pulsa un ítem para filtrar.").classes("text-[10px] text-slate-400")
                            ui.label("• Clic en plano fija cliente.").classes("text-[10px] text-slate-400")
                            ui.button("Limpiar Resalte", on_click=lambda: clear_selection()).props("outline dense").classes("w-full mt-1 text-[10px] text-indigo-300")

        # ======================================================================
        # COLUMNA DERECHA: CUADROS DE MANIPULACIÓN UNO ENCIMA DEL OTRO
        # ======================================================================
        with ui.column().classes("w-full lg:w-1/2 xl:w-5/12 gap-2.5 flex flex-col justify-start"):

            # CUADRO 1 (ARRIBA): CREAR PEDIDO (COMO CLIENTE)
            with ui.card().classes("w-full p-3 bg-slate-900 border border-slate-800 shadow-xl rounded-xl"):
                with ui.row().classes("w-full justify-between items-center mb-1"):
                    with ui.row().classes("items-center gap-1.5"):
                        ui.icon("add_shopping_cart", size="xs").classes("text-amber-400")
                        ui.label("1. Crear Pedido (Cliente)").classes("text-sm font-bold text-white")
                    ui.button("Enviar a FastAPI", on_click=lambda: submit_order(), icon="send").props("unelevated dense").classes("bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs px-3 py-1 rounded")

                with ui.row().classes("w-full gap-2 mt-1"):
                    cust_id_input = ui.input(label="ID de Cliente", value=f"CUST-{random.randint(100, 999)}").classes("flex-1 text-xs").props("dense outlined dark")
                    rest_options = {r["id"]: f"R{r['id']} - {r['name']}" for r in state["restaurants"]} or {1: "R1 - Burger Chapinero"}
                    rest_select = ui.select(rest_options, value=1, label="Restaurante").classes("flex-1 text-xs").props("dense outlined dark")

                with ui.row().classes("w-full gap-2 mt-1"):
                    coord_x_input = ui.number(label="Coord X (km)", value=3.50, min=0.0, max=6.0, step=0.1).classes("flex-1 text-xs").props("dense outlined dark")
                    coord_y_input = ui.number(label="Coord Y (km)", value=3.20, min=0.0, max=6.0, step=0.1).classes("flex-1 text-xs").props("dense outlined dark")

                async def submit_order():
                    cid = cust_id_input.value or f"CUST-{random.randint(100, 999)}"
                    rid = int(rest_select.value)
                    cx = float(coord_x_input.value or 0)
                    cy = float(coord_y_input.value or 0)
                    try:
                        res = await api_client.create_order(cid, rid, cx, cy)
                        ui.notify(f"Pedido #{res['id']} creado: Estado '{res['status']}' | ETA {res['eta_listo']} min", type="positive")
                        cust_id_input.set_value(f"CUST-{random.randint(100, 999)}")
                        state["selected_order_id"] = res["id"]
                        await refresh_data()
                    except Exception as ex:
                        ui.notify(f"Error al enviar pedido: {ex}", type="negative")

            # CUADRO 2 (ABAJO): ANALIZAR PEDIDOS EN PROGRESO & CONTROL DE FLUJO
            with ui.card().classes("w-full p-3 bg-slate-900 border border-slate-800 shadow-xl rounded-xl"):
                with ui.row().classes("w-full justify-between items-center mb-1"):
                    with ui.row().classes("items-center gap-1.5"):
                        ui.icon("timeline", size="xs").classes("text-sky-400")
                        ui.label("2. Analizar Orden en Progreso & Control").classes("text-sm font-bold text-white")

                async def on_order_select_change(e=None):
                    val = None
                    if e is not None:
                        val = getattr(e, "value", None)
                        if val is None and hasattr(e, "args"):
                            val = e.args
                    if val is None:
                        val = order_dropdown.value

                    try:
                        state["selected_order_id"] = int(val) if val is not None else None
                    except (ValueError, TypeError):
                        state["selected_order_id"] = None

                    update_order_detail_view()
                    update_map_view()

                order_dropdown = ui.select(
                    {},
                    label="Selecciona Orden Activa para Analizar y Resaltar",
                    on_change=on_order_select_change
                ).classes("w-full text-xs").props("dense outlined dark")

                # Contenedor de detalles de la orden seleccionada (compacto)
                order_detail_container = ui.column().classes("w-full mt-1 gap-1 p-2 bg-slate-950 rounded-lg border border-slate-800")

                # Controles del Ciclo de Vida de la App
                ui.label("Avanzar ciclo de vida:").classes("text-[11px] font-semibold text-slate-300 mt-1")
                with ui.row().classes("w-full gap-1.5 flex-wrap"):
                    btn_ready = ui.button("1. Listo", on_click=lambda: action_mark_ready()).props("unelevated dense").classes("bg-emerald-700 text-[11px] text-white px-2.5 py-0.5 rounded")
                    btn_assign = ui.button("2. Asignar", on_click=lambda: action_assign_courier()).props("unelevated dense").classes("bg-sky-700 text-[11px] text-white px-2.5 py-0.5 rounded")
                    btn_transit = ui.button("3. En Ruta", on_click=lambda: action_transit()).props("unelevated dense").classes("bg-purple-700 text-[11px] text-white px-2.5 py-0.5 rounded")
                    btn_deliver = ui.button("4. Entregar", on_click=lambda: action_deliver()).props("unelevated dense").classes("bg-green-600 text-[11px] text-white px-2.5 py-0.5 rounded")
                    btn_cancel = ui.button("Cancelar", on_click=lambda: action_cancel()).props("unelevated dense").classes("bg-rose-700 text-[11px] text-white px-2.5 py-0.5 rounded")

                # Toggle piloto automático para la orden seleccionada
                async def toggle_auto_pilot(e=None):
                    is_active = False
                    if e is not None:
                        val = getattr(e, "value", None)
                        if val is None and hasattr(e, "args"):
                            val = e.args
                        is_active = bool(val)
                    else:
                        is_active = bool(auto_pilot_switch.value)

                    if is_active:
                        if not state["selected_order_id"]:
                            ui.notify("Selecciona una orden primero", type="warning")
                            auto_pilot_switch.set_value(False)
                            return
                        state["auto_pilot_order_id"] = state["selected_order_id"]
                        ui.notify(f"Piloto automático activado para orden #{state['auto_pilot_order_id']}", type="positive")
                    else:
                        state["auto_pilot_order_id"] = None
                        ui.notify("Piloto automático desactivado", type="info")

                auto_pilot_switch = ui.switch(
                    "⚡ Piloto Automático (Avanzar paso a paso en vivo)",
                    on_change=toggle_auto_pilot
                ).classes("text-xs text-amber-300 mt-1")

    def clear_selection():
        state["selected_order_id"] = None
        state["auto_pilot_order_id"] = None
        order_dropdown.set_value(None)
        update_order_detail_view()
        update_map_view()

    def update_order_detail_view():
        order_detail_container.clear()
        sel_id = state["selected_order_id"]
        order = next((o for o in state["orders"] if o["id"] == sel_id), None)
        with order_detail_container:
            if not order:
                ui.label("Ninguna orden seleccionada. Elige una del desplegable para inspeccionar y resaltar.").classes("text-[11px] text-slate-400 italic")
                return

            st = order.get("status", "DESCONOCIDO")
            st_color = "amber" if "COLA" in st or "PREPARACION" in st else ("emerald" if st == "ENTREGADO" else ("rose" if "CANCELADO" in st else "sky"))
            
            with ui.row().classes("w-full justify-between items-center"):
                ui.label(f"Orden #{order['id']} — {order['customer_id']}").classes("text-xs font-bold text-white")
                ui.badge(st, color=st_color).classes("text-[10px] font-semibold")

            with ui.row().classes("w-full text-[11px] text-slate-300 justify-between"):
                ui.label(f"Restaurante: R{order['restaurant_id']}")
                ui.label(f"Entrega: ({order['delivery_coord_x']:.2f}, {order['delivery_coord_y']:.2f}) km")

            courier_info = f"Courier #{order.get('courier_id')}" if order.get('courier_id') else "Sin asignar"
            with ui.row().classes("w-full text-[11px] text-slate-300 justify-between"):
                ui.label(f"Repartidor: {courier_info}")
                ui.label(f"ETA Cocina: {order.get('eta_listo', 0.0)} min")

    # --- Acciones sobre el pedido seleccionado ---
    async def action_mark_ready():
        if not state["selected_order_id"]:
            ui.notify("Selecciona una orden primero", type="warning")
            return
        try:
            res = await api_client.mark_order_ready(state["selected_order_id"])
            ui.notify(f"Orden #{res['id']} marcada LISTO_EN_MOSTRADOR (+20% bono urgente)", type="positive")
            await refresh_data()
        except Exception as e:
            ui.notify(f"Error al marcar listo: {e}", type="negative")

    async def action_assign_courier():
        if not state["selected_order_id"]:
            ui.notify("Selecciona una orden primero", type="warning")
            return
        avail_couriers = [c for c in state["couriers"] if c.get("is_active") and c.get("is_available")]
        if not avail_couriers:
            ui.notify("No hay couriers disponibles en este momento", type="warning")
            return
        c = avail_couriers[0]
        try:
            res = await api_client.accept_order(state["selected_order_id"], c["id"])
            ui.notify(f"Orden #{res['id']} asignada a Courier {c['name']} (ID {c['id']})", type="positive")
            await refresh_data()
        except Exception as e:
            ui.notify(f"Error al asignar courier: {e}", type="negative")

    async def action_transit():
        if not state["selected_order_id"]:
            ui.notify("Selecciona una orden primero", type="warning")
            return
        order = next((o for o in state["orders"] if o["id"] == state["selected_order_id"]), None)
        cid = order.get("courier_id") if order else None
        if not cid:
            ui.notify("La orden aún no tiene repartidor asignado", type="warning")
            return
        try:
            res = await api_client.update_order_status(state["selected_order_id"], cid, "EN_TRANSITO_CLIENTE")
            ui.notify(f"Orden #{res['id']} en tránsito hacia el cliente.", type="positive")
            await refresh_data()
        except Exception as e:
            ui.notify(f"Error al actualizar estado: {e}", type="negative")

    async def action_deliver():
        if not state["selected_order_id"]:
            ui.notify("Selecciona una orden primero", type="warning")
            return
        order = next((o for o in state["orders"] if o["id"] == state["selected_order_id"]), None)
        cid = order.get("courier_id") if order else None
        if not cid:
            ui.notify("La orden no tiene repartidor", type="warning")
            return
        try:
            if order:
                res = await api_client.update_order_status(state["selected_order_id"], cid, "ENTREGADO", order["delivery_coord_x"], order["delivery_coord_y"])
                ui.notify(f"Orden #{res['id']} entregada al cliente con éxito.", type="positive")
                await refresh_data()
        except Exception as e:
            ui.notify(f"Error al entregar: {e}", type="negative")

    async def action_cancel():
        if not state["selected_order_id"]:
            ui.notify("Selecciona una orden primero", type="warning")
            return
        try:
            res = await api_client.cancel_order(state["selected_order_id"], "CUSTOMER_IMPATIENCE")
            ui.notify(f"Orden #{res['id']} cancelada por impaciencia.", type="info")
            await refresh_data()
        except Exception as e:
            ui.notify(f"Error al cancelar: {e}", type="negative")

    # --- Refresco Periódico de Datos ---
    async def refresh_data():
        state["restaurants"] = await api_client.get_restaurants()
        state["couriers"] = await api_client.get_couriers()
        state["orders"] = await api_client.get_orders(limit=50)
        state["telemetry"] = await api_client.get_telemetry_health()

        active_list = [o for o in state["orders"] if o.get("status") not in ("ENTREGADO", "CANCELADO_POR_CLIENTE", "CANCELADO_SIN_REPARTIDOR", "CANCELADO_INCIDENCIA_TRANSITO")]
        opts = {o["id"]: f"#{o['id']} ({o['status']}) - {o['customer_id']} -> R{o['restaurant_id']}" for o in active_list}
        if order_dropdown.options != opts:
            order_dropdown.set_options(opts)
        if state["selected_order_id"] is not None and state["selected_order_id"] in opts:
            if order_dropdown.value != state["selected_order_id"]:
                order_dropdown.set_value(state["selected_order_id"])

        if state["restaurants"]:
            r_opts = {r["id"]: f"R{r['id']} - {r['name']}" for r in state["restaurants"]}
            if rest_select.options != r_opts:
                rest_select.set_options(r_opts)
                if rest_select.value not in r_opts:
                    rest_select.set_value(list(r_opts.keys())[0])

        update_order_detail_view()
        update_map_view()

    # --- Bucle de Piloto Automático y Tick cada 1 segundo ---
    async def tick_second():
        if state.get("auto_pilot_order_id"):
            oid = state["auto_pilot_order_id"]
            order = next((o for o in state["orders"] if o["id"] == oid), None)
            if order:
                st = order.get("status")
                if st in ("EN_COLA_COCINA", "EN_PREPARACION"):
                    await action_mark_ready()
                elif st == "LISTO_EN_MOSTRADOR" and not order.get("courier_id"):
                    await action_assign_courier()
                elif st == "ASIGNADO":
                    c_id = order.get("courier_id")
                    courier = next((c for c in state["couriers"] if c["id"] == c_id), None)
                    rest = next((r for r in state["restaurants"] if r["id"] == order["restaurant_id"]), None)
                    if courier and rest:
                        dx = rest["coord_x"] - courier["current_coord_x"]
                        dy = rest["coord_y"] - courier["current_coord_y"]
                        dist = (dx**2 + dy**2)**0.5
                        if dist < 0.25:
                            await action_transit()
                        else:
                            step = min(0.3, dist)
                            nx = courier["current_coord_x"] + (dx / dist) * step
                            ny = courier["current_coord_y"] + (dy / dist) * step
                            await api_client.update_courier_location(c_id, nx, ny, max(15.0, courier["battery_level"] - 0.2))
                elif st == "EN_TRANSITO_CLIENTE":
                    c_id = order.get("courier_id")
                    courier = next((c for c in state["couriers"] if c["id"] == c_id), None)
                    if courier:
                        dx = order["delivery_coord_x"] - courier["current_coord_x"]
                        dy = order["delivery_coord_y"] - courier["current_coord_y"]
                        dist = (dx**2 + dy**2)**0.5
                        if dist < 0.25:
                            await action_deliver()
                            state["auto_pilot_order_id"] = None
                            auto_pilot_switch.set_value(False)
                        else:
                            step = min(0.3, dist)
                            nx = courier["current_coord_x"] + (dx / dist) * step
                            ny = courier["current_coord_y"] + (dy / dist) * step
                            await api_client.update_courier_location(c_id, nx, ny, max(15.0, courier["battery_level"] - 0.2))

        await refresh_data()

    await refresh_data()
    ui.timer(1.0, tick_second)
