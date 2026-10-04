"""
Página 2 del Dashboard: Métricas de Operación, Telemetría de Host y Configuración.
Contiene los cuadros de distribución y hardware uno al lado del otro, y un switch de estrategia.
"""
from nicegui import ui
from sistema_real.dashboard_pages.common import state, api_client, common_header


@ui.page("/metricas")
async def page_metrics():
    ui.query("body").classes("bg-slate-950 text-slate-100 font-sans")
    common_header("/metricas")

    with ui.column().classes("w-full p-3 gap-3 max-w-[1700px] mx-auto"):

        # ======================================================================
        # SECCIÓN 1: TARJETAS KPI EN TIEMPO REAL
        # ======================================================================
        with ui.row().classes("w-full gap-2.5 flex-wrap"):
            with ui.card().classes("flex-1 min-w-[170px] p-3 bg-slate-900 border border-slate-800 rounded-xl shadow-lg"):
                ui.label("Repartidores Conectados").classes("text-[11px] text-slate-400 font-medium")
                kpi_couriers_active = ui.label("0").classes("text-2xl font-extrabold text-sky-400")
                kpi_couriers_sub = ui.label("0 Libres | 0 En Ruta").classes("text-[10px] text-slate-400")

            with ui.card().classes("flex-1 min-w-[170px] p-3 bg-slate-900 border border-slate-800 rounded-xl shadow-lg"):
                ui.label("Pedidos al Día (Total)").classes("text-[11px] text-slate-400 font-medium")
                kpi_orders_total = ui.label("0").classes("text-2xl font-extrabold text-white")
                ui.label("Acumulado sesión").classes("text-[10px] text-slate-400")

            with ui.card().classes("flex-1 min-w-[170px] p-3 bg-slate-900 border border-slate-800 rounded-xl shadow-lg"):
                ui.label("Pedidos en Curso").classes("text-[11px] text-slate-400 font-medium")
                kpi_orders_progress = ui.label("0").classes("text-2xl font-extrabold text-amber-400")
                ui.label("Cocina + Mostrador + Tránsito").classes("text-[10px] text-slate-400")

            with ui.card().classes("flex-1 min-w-[170px] p-3 bg-slate-900 border border-slate-800 rounded-xl shadow-lg"):
                ui.label("Pedidos Completados").classes("text-[11px] text-slate-400 font-medium")
                kpi_orders_done = ui.label("0").classes("text-2xl font-extrabold text-emerald-400")
                ui.label("Entregas exitosas").classes("text-[10px] text-slate-400")

            with ui.card().classes("flex-1 min-w-[170px] p-3 bg-slate-900 border border-slate-800 rounded-xl shadow-lg"):
                ui.label("Pedidos Cancelados").classes("text-[11px] text-slate-400 font-medium")
                kpi_orders_cancel = ui.label("0").classes("text-2xl font-extrabold text-rose-400")
                ui.label("Impaciencia o anti-limbo").classes("text-[10px] text-slate-400")

        # ======================================================================
        # SECCIÓN 2: CUADROS UNO AL LADO DEL OTRO (DISTRIBUCIÓN Y TELEMETRÍA)
        # ======================================================================
        with ui.row().classes("w-full gap-3 items-stretch flex-col lg:flex-row flex-nowrap"):

            # CUADRO IZQUIERDO: DISTRIBUCIÓN DE PEDIDOS (PIE CHART CON ui.echart)
            with ui.card().classes("w-full lg:w-1/2 flex-1 p-3.5 bg-slate-900 border border-slate-800 rounded-xl shadow-lg flex flex-col justify-between"):
                with ui.row().classes("items-center gap-2 mb-1"):
                    ui.icon("pie_chart", size="xs").classes("text-indigo-400")
                    ui.label("Distribución de Pedidos (Estado Actual)").classes("text-sm font-bold text-white")

                pie_options = {
                    "backgroundColor": "transparent",
                    "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
                    "legend": {"top": "3%", "left": "center", "textStyle": {"color": "#94a3b8"}},
                    "series": [
                        {
                            "name": "Pedidos",
                            "type": "pie",
                            "radius": ["40%", "70%"],
                            "avoidLabelOverlap": False,
                            "itemStyle": {"borderRadius": 8, "borderColor": "#0f172a", "borderWidth": 2},
                            "label": {"show": False, "position": "center"},
                            "emphasis": {
                                "label": {"show": True, "fontSize": 15, "fontWeight": "bold", "color": "#ffffff"}
                            },
                            "labelLine": {"show": False},
                            "data": [
                                {"value": 0, "name": "En Curso", "itemStyle": {"color": "#38bdf8"}},
                                {"value": 0, "name": "Completados", "itemStyle": {"color": "#10b981"}},
                                {"value": 0, "name": "Cancelados", "itemStyle": {"color": "#ef4444"}},
                            ],
                        }
                    ],
                }
                pie_chart = ui.echart(pie_options).classes("w-full h-64")

            # CUADRO DERECHO: TELEMETRÍA DE HARDWARE (CPU, RAM, LATENCIA)
            with ui.card().classes("w-full lg:w-1/2 flex-1 p-3.5 bg-slate-900 border border-slate-800 rounded-xl shadow-lg flex flex-col justify-between"):
                with ui.row().classes("items-center gap-2 mb-1"):
                    ui.icon("memory", size="xs").classes("text-emerald-400")
                    ui.label("Telemetría de Servidor (Host)").classes("text-sm font-bold text-white")

                with ui.column().classes("w-full gap-2.5 my-auto"):
                    with ui.column().classes("w-full gap-1"):
                        with ui.row().classes("w-full justify-between text-xs"):
                            ui.label("Uso de CPU:").classes("text-slate-400")
                            cpu_val_label = ui.label("0.0%").classes("font-bold text-emerald-400")
                        cpu_progress = ui.linear_progress(value=0.0, show_value=False).props("color=emerald rounded").classes("w-full h-2")

                    with ui.column().classes("w-full gap-1"):
                        with ui.row().classes("w-full justify-between text-xs"):
                            ui.label("Memoria RAM Asignada:").classes("text-slate-400")
                            ram_val_label = ui.label("0.0 MB").classes("font-bold text-sky-400")
                        ram_progress = ui.linear_progress(value=0.0, show_value=False).props("color=sky rounded").classes("w-full h-2")

                    with ui.row().classes("w-full justify-between text-xs p-2 bg-slate-950 rounded border border-slate-800"):
                        ui.label("Latencia Media API:")
                        latency_label = ui.label("0.0 ms").classes("font-bold text-amber-400")

                    with ui.row().classes("w-full justify-between text-xs p-2 bg-slate-950 rounded border border-slate-800"):
                        ui.label("Uptime del Servidor:")
                        uptime_label = ui.label("0 s").classes("font-bold text-slate-300")

        # ======================================================================
        # SECCIÓN 3: CONFIGURACIÓN DINÁMICA DE LA API CON SWITCH DE ESTRATEGIA
        # ======================================================================
        with ui.card().classes("w-full p-4 bg-slate-900 border border-slate-800 rounded-xl shadow-lg"):
            with ui.row().classes("items-center justify-between mb-2 w-full"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("tune", size="xs").classes("text-amber-400")
                    ui.label("Configuración Dinámica de la API (/api/v1/config/)").classes("text-sm font-bold text-white")

            ui.label("Modifica los parámetros y políticas en caliente. Los cambios se persisten inmediatamente en la instancia FastAPI.").classes("text-[11px] text-slate-400 mb-2")

            # SWITCH DE ESTRATEGIA (Sincronizado Predictivo vs Voraz Inmediato)
            with ui.row().classes("w-full items-center justify-between p-3 bg-slate-950 rounded-xl border border-slate-800 mb-3"):
                with ui.row().classes("items-center gap-3"):
                    ui.icon("swap_horiz", size="sm").classes("text-indigo-400")
                    with ui.column().classes("gap-0"):
                        ui.label("Estrategia Activa de Despacho").classes("text-[11px] text-slate-400")
                        strategy_title_label = ui.label("Sincronizado Predictivo (Propuesta)").classes("text-xs font-bold text-white")

                def on_strategy_toggle(e=None):
                    is_active = False
                    if e is not None:
                        val = getattr(e, "value", None)
                        if val is None and hasattr(e, "args"):
                            val = e.args
                        is_active = bool(val)
                    else:
                        is_active = bool(strategy_switch.value)

                    if is_active:
                        strategy_title_label.set_text("Sincronizado Predictivo (Propuesta — ETA Cocina + Buffer)")
                        strategy_badge.set_text("SYNCHRONIZED")
                        strategy_badge.props("color=indigo")
                    else:
                        strategy_title_label.set_text("Voraz Inmediato (Línea Base — Asignación Inmediata)")
                        strategy_badge.set_text("GREEDY")
                        strategy_badge.props("color=amber")

                with ui.row().classes("items-center gap-3"):
                    ui.label("Voraz Inmediato").classes("text-xs text-slate-400")
                    strategy_switch = ui.switch(value=True, on_change=on_strategy_toggle).props("color=indigo dark")
                    ui.label("Sincronizado Predictivo").classes("text-xs text-indigo-300 font-semibold")
                    strategy_badge = ui.badge("SYNCHRONIZED", color="indigo").classes("text-xs font-bold ml-1")

            with ui.row().classes("w-full gap-3 flex-wrap mt-1"):
                buffer_input = ui.number(label="Holgura Buffer Delta t (min)", value=2.0, min=0.0, max=5.0, step=0.5).classes("w-52 text-xs").props("dense outlined dark")
                shift_input = ui.number(label="Turno Máximo (min, 6h=360)", value=360.0, min=60.0, max=480.0, step=30.0).classes("w-52 text-xs").props("dense outlined dark")
                antilimbo_input = ui.number(label="Timeout Anti-Limbo (min)", value=20.0, min=5.0, max=60.0, step=1.0).classes("w-52 text-xs").props("dense outlined dark")
                urgency_input = ui.number(label="Multiplicador Bono Urgente", value=1.20, min=1.0, max=2.0, step=0.05).classes("w-52 text-xs").props("dense outlined dark")
                battery_input = ui.number(label="Batería Crítica Mínima (%)", value=15.0, min=5.0, max=30.0, step=1.0).classes("w-52 text-xs").props("dense outlined dark")

            async def save_configuration():
                payload = {
                    "active_dispatch_policy": "synchronized" if strategy_switch.value else "greedy",
                    "buffer_delta_t_min": float(buffer_input.value or 0),
                    "max_shift_duration_min": float(shift_input.value or 0),
                    "anti_limbo_max_counter_min": float(antilimbo_input.value or 0),
                    "urgency_bonus_multiplier": float(urgency_input.value or 0),
                    "min_battery_threshold_pct": float(battery_input.value or 0),
                }
                try:
                    res = await api_client.update_system_config(payload)
                    ui.notify("Configuración de API actualizada exitosamente.", type="positive")
                except Exception as ex:
                    ui.notify(f"Error al guardar configuración: {ex}", type="negative")

            async def reload_configuration():
                cfg = await api_client.get_system_config()
                is_sync = (cfg.get("active_dispatch_policy", "synchronized") == "synchronized")
                strategy_switch.set_value(is_sync)
                on_strategy_toggle(type("obj", (object,), {"value": is_sync}))

                buffer_input.set_value(cfg.get("buffer_delta_t_min", 2.0))
                shift_input.set_value(cfg.get("max_shift_duration_min", 360.0))
                antilimbo_input.set_value(cfg.get("anti_limbo_max_counter_min", 20.0))
                urgency_input.set_value(cfg.get("urgency_bonus_multiplier", 1.20))
                battery_input.set_value(cfg.get("min_battery_threshold_pct", 15.0))
                ui.notify("Configuración recargada desde la API.", type="info")

            with ui.row().classes("w-full mt-3 gap-2 justify-end"):
                ui.button("Recargar Valores Actuales", on_click=reload_configuration).props("flat dense").classes("text-slate-300 text-xs")
                ui.button("Guardar en API", on_click=save_configuration, icon="save").props("unelevated dense").classes("bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs px-3 py-1.5 rounded")

    # --- Función de Actualización de Métricas cada segundo ---
    async def update_metrics_loop():
        summary = await api_client.get_order_stats_summary()
        telemetry = await api_client.get_telemetry_health()
        couriers = await api_client.get_couriers()

        connected = summary.get("connected_couriers", len(couriers))
        libres = sum(1 for c in couriers if c.get("is_active") and c.get("is_available"))
        ocupados = max(0, connected - libres)

        kpi_couriers_active.set_text(str(connected))
        kpi_couriers_sub.set_text(f"{libres} Libres | {ocupados} En Ruta")

        total = summary.get("total_orders", 0)
        progress = summary.get("orders_in_progress", 0)
        done = summary.get("orders_completed", 0)
        cancel = summary.get("orders_cancelled", 0)

        kpi_orders_total.set_text(str(total))
        kpi_orders_progress.set_text(str(progress))
        kpi_orders_done.set_text(str(done))
        kpi_orders_cancel.set_text(str(cancel))

        pie_chart.options["series"][0]["data"] = [
            {"value": progress, "name": "En Curso", "itemStyle": {"color": "#38bdf8"}},
            {"value": done, "name": "Completados", "itemStyle": {"color": "#10b981"}},
            {"value": cancel, "name": "Cancelados", "itemStyle": {"color": "#ef4444"}},
        ]
        pie_chart.update()

        cpu_pct = telemetry.get("cpu_percent", 0.0)
        mem_mb = telemetry.get("memory_mb", 0.0)
        lat_ms = telemetry.get("latency_avg_ms", 0.0)
        uptime_sec = telemetry.get("uptime_seconds", 0.0)

        cpu_val_label.set_text(f"{cpu_pct:.1f}%")
        cpu_progress.set_value(min(1.0, cpu_pct / 100.0))

        ram_val_label.set_text(f"{mem_mb:.1f} MB")
        ram_progress.set_value(min(1.0, mem_mb / 4096.0))

        latency_label.set_text(f"{lat_ms:.2f} ms")
        uptime_label.set_text(f"{int(uptime_sec // 60)}m {int(uptime_sec % 60)}s")

    await reload_configuration()
    await update_metrics_loop()
    ui.timer(1.0, update_metrics_loop)
