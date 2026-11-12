"""
analisis/sensibilidad_buffer.py
--------------------------------
Script ejecutable y reproducible para evaluar la sensibilidad del margen de holgura
temporal (delta_t_buffer in [0.0, 5.0] min) en la regla de Despacho Sincronizado Predictivo.

Responde formalmente a la Pregunta de Decisión 4 del Proyecto de Aula:
¿Cuál es el valor del margen de holgura temporal que minimiza conjuntamente el tiempo de
espera del repartidor en el restaurante (T_espera_rest) y el percentil 95 del tiempo de
permanencia de la comida en mostrador (T_mostrador_p95 <= 6.0 min)?
"""

import os
import sys
import json
import math
from pathlib import Path
from typing import Dict, Any, List

# Garantizar resolución de rutas
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from simulacion.simpy_engine import SimpyEngine

BUFFER_VALUES = [0.0, 1.0, 2.0, 2.5, 3.0, 4.0, 5.0]
REPLICAS_POR_BUFFER = 10
SEED_BASE = 42
OUTPUT_JSON = ROOT_DIR / "datos" / "sensibilidad_buffer_results.json"
OUTPUT_FIG = ROOT_DIR / "docs" / "figuras" / "fig_04_sensibilidad_buffer.png"


def ejecutar_analisis_sensibilidad(
    buffers: List[float] = BUFFER_VALUES,
    n_replicas: int = REPLICAS_POR_BUFFER,
    seed_base: int = SEED_BASE
) -> Dict[str, Any]:
    print("=" * 80)
    print(f"ANÁLISIS DE SENSIBILIDAD DEL BUFFER (Δt_buffer) — PREGUNTA DE DECISIÓN 4")
    print(f"Valores a evaluar: {buffers} min | Réplicas por valor: {n_replicas} (Semillas {seed_base}..{seed_base + n_replicas - 1})")
    print("=" * 80)

    resultados_por_buffer = {}

    for b in buffers:
        print(f"\n>>> Evaluando Δt_buffer = {b:.1f} min ({n_replicas} réplicas de 24h)...")
        metricas_replicas = []

        for i in range(n_replicas):
            seed_actual = seed_base + i
            motor = SimpyEngine(policy_name="synchronized", t_buffer=b, seed=seed_actual)
            kpis = motor.run_24h(export_path=None)
            metricas_replicas.append(kpis)

        # Calcular medias y desviaciones estándar
        n = len(metricas_replicas)
        t_critico = 2.262 if n == 10 else 2.0452  # t-Student para n=10 (9 gl) o n=30 (29 gl)

        def resumir_kpi(clave: str):
            vals = [m[clave] for m in metricas_replicas if clave in m]
            media = sum(vals) / n
            var = sum((x - media) ** 2 for x in vals) / (n - 1) if n > 1 else 0.0
            desv = math.sqrt(var)
            semi = t_critico * (desv / math.sqrt(n)) if n > 1 else 0.0
            return {
                "media": round(media, 2),
                "desv_std": round(desv, 2),
                "ic_95": [round(media - semi, 2), round(media + semi, 2)],
                "ic_semiamplitud": round(semi, 2),
            }

        resumen_b = {
            "buffer_min": b,
            "T_espera_rest_avg_min": resumir_kpi("T_espera_rest_avg_min"),
            "T_mostrador_p95_min": resumir_kpi("T_mostrador_p95_min"),
            "W_total_p95_min": resumir_kpi("W_total_p95_min"),
            "P_canc_porcentaje": resumir_kpi("P_canc_porcentaje"),
            "Rho_rep_avg_porcentaje": resumir_kpi("Rho_rep_avg_porcentaje"),
            "entregas_promedio": round(sum(m["ordenes_entregadas"] for m in metricas_replicas) / n, 1)
        }

        print(f"    Espera en restaurante : {resumen_b['T_espera_rest_avg_min']['media']} ± {resumen_b['T_espera_rest_avg_min']['ic_semiamplitud']} min (SLA <= 3.5 min)")
        print(f"    Permanencia mostrador : {resumen_b['T_mostrador_p95_min']['media']} ± {resumen_b['T_mostrador_p95_min']['ic_semiamplitud']} min")
        print(f"    Ciclo total W (p95)   : {resumen_b['W_total_p95_min']['media']} ± {resumen_b['W_total_p95_min']['ic_semiamplitud']} min")
        print(f"    Tasa cancelación      : {resumen_b['P_canc_porcentaje']['media']}% | Entregas día: {resumen_b['entregas_promedio']}")

        resultados_por_buffer[f"{b:.1f}"] = resumen_b

    # Consolidar salida JSON
    output_data = {
        "metadata": {
            "descripcion": "Barrido paramétrico de sensibilidad de delta_t_buffer para Despacho Sincronizado",
            "pregunta_decision": "Pregunta 4: Margen de Holgura Cocina-Despacho",
            "replicas_por_buffer": n_replicas,
            "seed_base": seed_base,
            "valores_buffer_evaluados": buffers
        },
        "resultados": resultados_por_buffer
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=4)
    print(f"\n[OK] Datos de sensibilidad exportados exitosamente a: {OUTPUT_JSON}")

    # Mostrar tabla resumen formateada
    print("\n" + "=" * 105)
    print(f"{'TABLA DE SENSIBILIDAD DEL MARGEN DE HOLGURA (Δt_buffer)':^105}")
    print("=" * 105)
    print(f"{'Buffer (min)':<12} | {'Espera Rest (min)':<22} | {'Mostrador p95 (min)':<22} | {'Ciclo W_p95 (min)':<20} | {'Cancelación (%)':<16}")
    print("-" * 105)
    for b_str, data in resultados_por_buffer.items():
        esp = f"{data['T_espera_rest_avg_min']['media']} ± {data['T_espera_rest_avg_min']['ic_semiamplitud']}"
        most = f"{data['T_mostrador_p95_min']['media']} ± {data['T_mostrador_p95_min']['ic_semiamplitud']}"
        w95 = f"{data['W_total_p95_min']['media']} ± {data['W_total_p95_min']['ic_semiamplitud']}"
        canc = f"{data['P_canc_porcentaje']['media']}%"
        print(f"{b_str + ' min':<12} | {esp:<22} | {most:<22} | {w95:<20} | {canc:<16}")
    print("=" * 105)

    # Generar gráfica de compromiso (Trade-Off) si matplotlib y seaborn están disponibles
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns

        sns.set_theme(style="whitegrid", context="paper", font_scale=1.1)
        fig, ax1 = plt.subplots(figsize=(8, 5))

        x = buffers
        y_esp = [resultados_por_buffer[f"{b:.1f}"]["T_espera_rest_avg_min"]["media"] for b in buffers]
        y_most = [resultados_por_buffer[f"{b:.1f}"]["T_mostrador_p95_min"]["media"] for b in buffers]

        color1 = "#2980b9"
        ax1.set_xlabel("Margen de Holgura Temporal $\\Delta t_{\\mathrm{buffer}}$ (minutos)", fontweight="bold")
        ax1.set_ylabel("Espera Ociosa del Repartidor (min)", color=color1, fontweight="bold")
        l1 = ax1.plot(x, y_esp, marker="o", color=color1, linewidth=2.5, label="Espera Ociosa Repartidor")
        ax1.tick_params(axis="y", labelcolor=color1)
        ax1.axhline(y=3.5, color=color1, linestyle=":", alpha=0.7, label="SLA Espera (3.5 min)")

        ax2 = ax1.twinx()
        color2 = "#c0392b"
        ax2.set_ylabel("Permanencia en Mostrador $p95$ (min)", color=color2, fontweight="bold")
        l2 = ax2.plot(x, y_most, marker="s", color=color2, linewidth=2.5, linestyle="--", label="Permanencia Mostrador p95")
        ax2.tick_params(axis="y", labelcolor=color2)
        ax2.axhline(y=6.0, color=color2, linestyle="--", alpha=0.7, label="SLA Térmico (6.0 min)")

        # Marcar buffer óptimo 2.5 min
        ax1.axvline(x=2.5, color="#27ae60", linestyle="-.", linewidth=2, label="Punto Óptimo (2.5 min)")

        plt.title("Compromiso Operativo: Ociosidad de Flota vs. Permanencia en Mostrador", fontweight="bold", pad=12)
        fig.tight_layout()

        OUTPUT_FIG.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(OUTPUT_FIG, dpi=300)
        plt.close()
        print(f"[OK] Gráfica de trade-off guardada en: {OUTPUT_FIG}")
    except Exception as e:
        print(f"[Warning] No se pudo generar la gráfica de sensibilidad: {e}")

    return output_data


if __name__ == "__main__":
    ejecutar_analisis_sensibilidad()
