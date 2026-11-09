import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np
from scipy import stats

# Agregar el directorio raíz al path para permitir importaciones entre carpetas
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from analisis.queueing_theory import QueueingModelMMC, FRANJAS_PROYECTO
from simulacion.simpy_engine import run_markovian_replica


class ContrastAnalyzer:
    """
    Ejecuta el contraste estadístico entre el modelo analítico M/M/c (Fórmula C de Erlang)
    y la réplica canónica en SimPy utilizando N=30 réplicas independientes con intervalos
    de confianza del 95% (distribución t-Student, gl = N - 1).
    """

    def __init__(
        self,
        lambda_rate: float = 2.70,
        mu_rate: float = 0.05,
        c_servers: int = 70,
        num_replicas: int = 30,
        base_seed: int = 1000,
    ):
        self.lambda_rate = lambda_rate
        self.mu_rate = mu_rate
        self.c_servers = c_servers
        self.num_replicas = num_replicas
        self.base_seed = base_seed
        self.modelo_teorico = QueueingModelMMC(lambda_rate, mu_rate, c_servers)

    @staticmethod
    def calcular_estadisticos_ic95(muestras: List[float], valor_teorico: float) -> Dict[str, Any]:
        """Calcula media, desviación estándar, IC 95% (t-Student) y error relativo porcentual."""
        arr = np.asarray(muestras, dtype=float)
        n = len(arr)
        media = float(np.mean(arr))
        std = float(np.std(arr, ddof=1)) if n > 1 else 0.0
        t_crit = float(stats.t.ppf(0.975, df=n - 1)) if n > 1 else 1.96
        sem = std / np.sqrt(n) if n > 0 else 0.0
        half_width = t_crit * sem
        ci_low = media - half_width
        ci_high = media + half_width

        if abs(valor_teorico) < 1e-15:
            error_pct = 0.0
        else:
            error_pct = abs((media - valor_teorico) / valor_teorico) * 100.0

        en_ic = bool(ci_low - 1e-12 <= valor_teorico <= ci_high + 1e-12)

        return {
            "teorico": float(valor_teorico),
            "media_sim": media,
            "std_sim": std,
            "half_width_95": float(half_width),
            "ic95_low": float(ci_low),
            "ic95_high": float(ci_high),
            "error_rel_pct": float(error_pct),
            "en_ic95": en_ic,
        }

    def ejecutar_contraste(self, verbose: bool = True) -> Dict[str, Dict[str, Any]]:
        """
        Ejecuta N réplicas independientes para el escenario configurado y muestra la tabla
        comparativa con intervalos de confianza del 95%.
        """
        metricas_teoricas = self.modelo_teorico.calculate_metrics()
        llaves = ["rho", "Pw", "Lq", "Wq", "W", "L"]
        resultados_simulacion: Dict[str, List[float]] = {k: [] for k in llaves}

        if verbose:
            print(
                f"Ejecutando {self.num_replicas} réplicas M/M/c en SimPy "
                f"(lambda={self.lambda_rate}, mu={self.mu_rate}, c={self.c_servers})..."
            )

        for r in range(self.num_replicas):
            seed_r = self.base_seed + r * 97
            metricas_simpy = run_markovian_replica(
                lambda_rate=self.lambda_rate,
                mu_rate=self.mu_rate,
                c_servers=self.c_servers,
                seed=seed_r,
            )
            for k in llaves:
                resultados_simulacion[k].append(metricas_simpy[k])

        resumen: Dict[str, Dict[str, Any]] = {}
        for k in llaves:
            resumen[k] = self.calcular_estadisticos_ic95(
                resultados_simulacion[k], metricas_teoricas[k]
            )

        if verbose:
            print("\n" + "=" * 100)
            print(
                f"CONTRASTE ANALÍTICO M/M/c vs SIMPY ({self.num_replicas} RÉPLICAS, IC 95% t-STUDENT)"
            )
            print("=" * 100)
            header = (
                f"{'Métrica':<8} | {'Teórico M/M/c':<14} | {'Media SimPy':<14} | "
                f"{'IC 95% (± margen)':<27} | {'Error (%)':<10} | {'Estado':<10}"
            )
            print(header)
            print("-" * 100)
            for k in llaves:
                st = resumen[k]
                ic_str = f"[{st['ic95_low']:.4f}, {st['ic95_high']:.4f}] (±{st['half_width_95']:.4f})"
                if st["error_rel_pct"] < 5.0 and st["en_ic95"]:
                    estado = "OK (<5%, en IC)"
                elif st["en_ic95"]:
                    estado = "OK (en IC 95%)"
                elif st["error_rel_pct"] < 5.0:
                    estado = "OK (<5%)"
                else:
                    estado = "REVISAR"
                print(
                    f"{k:<8} | {st['teorico']:<14.4f} | {st['media_sim']:<14.4f} | "
                    f"{ic_str:<27} | {st['error_rel_pct']:<8.2f}% | {estado:<15}"
                )
            print("=" * 100)

        return resumen


def ejecutar_contraste_tabla5(
    num_replicas: int = 30,
    base_seed: int = 1000,
    export_path: Optional[str] = "datos/mmc_contrast_results.json",
) -> Dict[str, Any]:
    """
    Ejecuta 30 réplicas independientes de la simulación M/M/c en SimPy para cada una
    de las 7 franjas horarias de la Tabla 5 (FRANJAS_PROYECTO), calculando intervalos de
    confianza del 95% y errores relativos porcentuales frente a Erlang-C.
    """
    print("\n" + "=" * 130)
    print(
        f"VALIDACIÓN INTEGRAL CONTRA TABLA 5: {num_replicas} RÉPLICAS M/M/c POR FRANJA CON INTERVALOS DE CONFIANZA DEL 95%"
    )
    print("=" * 130)
    header = (
        f"{'Franja Horaria':<27} | {'c':<2} | {'rho Teo / Sim (±IC95)':<25} | "
        f"{'Wq Teo / Sim (±IC95) [min]':<28} | {'W Teo / Sim (±IC95) [min]':<27} | "
        f"{'L Teo / Sim (±IC95)':<25} | {'Err W (%)':<9}"
    )
    print(header)
    print("-" * 130)

    resultados_franjas: Dict[str, Any] = {}

    for idx, f in enumerate(FRANJAS_PROYECTO):
        analizador = ContrastAnalyzer(
            lambda_rate=f["lambda"],
            mu_rate=f["mu"],
            c_servers=f["c"],
            num_replicas=num_replicas,
            base_seed=base_seed + idx * 1000,
        )
        res = analizador.ejecutar_contraste(verbose=False)
        resultados_franjas[f["nombre"]] = {
            "parametros": f,
            "num_replicas": num_replicas,
            "metricas": res,
        }

        rho_s = f"{res['rho']['teorico']:.4f} / {res['rho']['media_sim']:.4f} (±{res['rho']['half_width_95']:.4f})"
        wq_s = f"{res['Wq']['teorico']:.4f} / {res['Wq']['media_sim']:.4f} (±{res['Wq']['half_width_95']:.4f})"
        w_s = f"{res['W']['teorico']:.4f} / {res['W']['media_sim']:.4f} (±{res['W']['half_width_95']:.4f})"
        l_s = f"{res['L']['teorico']:.4f} / {res['L']['media_sim']:.4f} (±{res['L']['half_width_95']:.4f})"
        err_w = res["W"]["error_rel_pct"]

        print(
            f"{f['nombre']:<27} | {f['c']:<2} | {rho_s:<25} | "
            f"{wq_s:<28} | {w_s:<27} | {l_s:<25} | {err_w:<8.2f}%"
        )

    print("=" * 130)

    if export_path:
        out_file = ROOT_DIR / export_path
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as fp:
            json.dump(resultados_franjas, fp, indent=4, ensure_ascii=False)
        print(f"Resultados de las {num_replicas} réplicas guardados en: {out_file}")

    return resultados_franjas


if __name__ == "__main__":
    # 1. Contraste detallado del Pico Almuerzo (demostración paso a paso de la Sección 3.7.3)
    analizador_almuerzo = ContrastAnalyzer(
        lambda_rate=2.70, mu_rate=0.05, c_servers=70, num_replicas=30, base_seed=4000
    )
    analizador_almuerzo.ejecutar_contraste(verbose=True)

    # 2. Contraste completo de las 7 franjas horarias de la Tabla 5 con 30 réplicas e IC 95%
    ejecutar_contraste_tabla5(num_replicas=30, base_seed=1000)
