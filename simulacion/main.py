import argparse
import json
import math
import sys
from pathlib import Path
from typing import Dict, Any, List

# Garantizar resolución de módulos tanto desde la raíz como desde simulacion/
current_dir = Path(__file__).resolve().parent
repo_root = current_dir.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

try:
    from simulacion.simpy_engine import SimpyEngine
except ImportError:
    from simpy_engine import SimpyEngine


def calcular_estadisticas_replicas(metricas_lista: List[Dict[str, float]]) -> Dict[str, Any]:
    """
    Calcula media muestral, desviación estándar e intervalo de confianza del 95%
    utilizando la distribución t-Student con n - 1 grados de libertad (t = 2.0452 para n=30).
    """
    n = len(metricas_lista)
    if n == 0:
        return {}

    t_critico = 2.0452 if n == 30 else 1.96  # t_0.975,29 para 30 réplicas

    keys_kpis = [
        "W_total_p95_min",
        "T_espera_rest_avg_min",
        "T_mostrador_p95_min",
        "P_canc_porcentaje",
        "Rho_rep_avg_porcentaje",
    ]

    resumen = {}
    for k in keys_kpis:
        valores = [m[k] for m in metricas_lista if k in m]
        if not valores:
            continue
        media = sum(valores) / n
        if n > 1:
            varianza = sum((x - media) ** 2 for x in valores) / (n - 1)
            desv_std = math.sqrt(varianza)
            error_est = desv_std / math.sqrt(n)
            ic_semiamplitud = t_critico * error_est
        else:
            desv_std = 0.0
            ic_semiamplitud = 0.0

        resumen[k] = {
            "media": round(media, 2),
            "desv_std": round(desv_std, 2),
            "ic_95": [round(media - ic_semiamplitud, 2), round(media + ic_semiamplitud, 2)],
            "ic_semiamplitud": round(ic_semiamplitud, 2),
        }

    return resumen


def ejecutar_banco_replicas(
    politica: str,
    n_replicas: int = 30,
    seed_inicio: int = 42,
    t_buffer: float = 2.5,
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Ejecuta N réplicas con semillas secuenciales para una política determinada."""
    print(f"\n>>> Ejecutando {n_replicas} réplicas para política: [{politica.upper()}] (Semillas {seed_inicio}..{seed_inicio + n_replicas - 1})...")
    resultados_crudos = []

    for i in range(n_replicas):
        seed_actual = seed_inicio + i
        motor = SimpyEngine(policy_name=politica, t_buffer=t_buffer, seed=seed_actual)
        kpis = motor.run_24h(export_path=None)
        resultados_crudos.append(kpis)
        print(f"  [Réplica {i+1:02d}/{n_replicas:02d} | Semilla {seed_actual}] -> T_espera_rest: {kpis['T_espera_rest_avg_min']:.2f} min | W_p95: {kpis['W_total_p95_min']:.2f} min | P_canc: {kpis['P_canc_porcentaje']:.2f}%")

    stats = calcular_estadisticas_replicas(resultados_crudos)
    return resultados_crudos, stats


def imprimir_tabla_comparativa(stats_greedy: Dict[str, Any], stats_sync: Dict[str, Any], n_replicas: int):
    """Muestra en terminal una tabla de contraste formal entre ambas políticas."""
    print("\n" + "=" * 90)
    print(f"{'COMPARATIVA DE POLÍTICAS — ' + str(n_replicas) + ' RÉPLICAS ESTOCÁSTICAS (IC 95%)':^90}")
    print("=" * 90)
    print(f"{'Métrica (KPI)':<30} | {'Voraz (Greedy)':<25} | {'Sincronizada (Sync)':<25}")
    print("-" * 90)

    labels = {
        "T_espera_rest_avg_min": "Espera en restaurante (min)",
        "W_total_p95_min": "Tiempo de ciclo W_p95 (min)",
        "T_mostrador_p95_min": "Permanencia mostrador p95",
        "P_canc_porcentaje": "Tasa de cancelación (%)",
        "Rho_rep_avg_porcentaje": "Utilización de flota (%)",
    }

    for k, nombre in labels.items():
        g_val = f"{stats_greedy[k]['media']} ± {stats_greedy[k]['ic_semiamplitud']}"
        s_val = f"{stats_sync[k]['media']} ± {stats_sync[k]['ic_semiamplitud']}"
        print(f"{nombre:<30} | {g_val:<25} | {s_val:<25}")
    print("=" * 90 + "\n")


def main():
    parser = argparse.ArgumentParser(description="QuickDelivery Sim — Motor CLI de Simulación DES")
    parser.add_argument(
        "--policy",
        choices=["greedy", "synchronized", "both"],
        default="both",
        help="Política de despacho a simular (default: both)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=30,
        help="Número de réplicas estocásticas independientes (default: 30)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Semilla base inicial (default: 42)",
    )
    parser.add_argument(
        "--buffer",
        type=float,
        default=2.5,
        help="Margen de holgura delta_t para política sincronizada en minutos (default: 2.5)",
    )
    parser.add_argument(
        "--export",
        type=str,
        default="datos/simulation_results.json",
        help="Ruta del archivo JSON de salida (default: datos/simulation_results.json)",
    )

    args = parser.parse_args()
    data_output: Dict[str, Any] = {
        "metadata": {
            "n_replicas": args.runs,
            "seed_inicio": args.seed,
            "buffer_delta_t_min": args.buffer,
        }
    }

    stats_greedy = {}
    stats_sync = {}

    if args.policy in ("greedy", "both"):
        raw_g, stats_greedy = ejecutar_banco_replicas(
            politica="greedy", n_replicas=args.runs, seed_inicio=args.seed, t_buffer=args.buffer
        )
        data_output["politica_voraz"] = {
            "estadisticas_ic95": stats_greedy,
            "replicas": raw_g,
        }

    if args.policy in ("synchronized", "both"):
        raw_s, stats_sync = ejecutar_banco_replicas(
            politica="synchronized", n_replicas=args.runs, seed_inicio=args.seed, t_buffer=args.buffer
        )
        data_output["politica_sincronizada"] = {
            "estadisticas_ic95": stats_sync,
            "replicas": raw_s,
        }

    # Conservar claves de primer nivel para retrocompatibilidad directa con scripts existentes
    if stats_sync:
        data_output["W_total_p95_min"] = stats_sync["W_total_p95_min"]["media"]
        data_output["T_espera_rest_avg_min"] = stats_sync["T_espera_rest_avg_min"]["media"]
        data_output["T_mostrador_p95_min"] = stats_sync["T_mostrador_p95_min"]["media"]
        data_output["P_canc_porcentaje"] = stats_sync["P_canc_porcentaje"]["media"]
        data_output["Rho_rep_avg_porcentaje"] = stats_sync["Rho_rep_avg_porcentaje"]["media"]
    elif stats_greedy:
        data_output["W_total_p95_min"] = stats_greedy["W_total_p95_min"]["media"]
        data_output["T_espera_rest_avg_min"] = stats_greedy["T_espera_rest_avg_min"]["media"]
        data_output["T_mostrador_p95_min"] = stats_greedy["T_mostrador_p95_min"]["media"]
        data_output["P_canc_porcentaje"] = stats_greedy["P_canc_porcentaje"]["media"]
        data_output["Rho_rep_avg_porcentaje"] = stats_greedy["Rho_rep_avg_porcentaje"]["media"]

    if args.policy == "both":
        imprimir_tabla_comparativa(stats_greedy, stats_sync, args.runs)

    # Exportación persistente
    ruta_export = Path(args.export)
    ruta_export.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta_export, "w", encoding="utf-8") as f:
        json.dump(data_output, f, indent=4)
    print(f"\n[OK] Resultados consolidados exportados con éxito a: {ruta_export.resolve()}")


if __name__ == "__main__":
    main()